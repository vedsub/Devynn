"""
POST /upload — transcribe audio, generate follow-up, return structured response.
Persists turn and uploads audio to S3 as background tasks.
"""

import logging
import os
import time
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import UploadResponse
from app.core.config import settings
from app.core.database import get_db
from app.core.db_models import User
from app.core.security import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pace helpers
# ---------------------------------------------------------------------------
DEFAULT_CHUNK_LENGTH = 10


def _pace_label(wps: float) -> str:
    if 1.0 <= wps <= 3.0:
        return "Good"
    elif wps < 1.0:
        return "Very Slow"
    else:
        return "Too Fast"


def _grammar_check(text: str) -> list[str]:
    from model.inference import generate_output  # lazy

    prompt = f'Correct "{text}" to standard English and place the results in "Correct Text:"'
    raw = generate_output(prompt)
    corrected = raw.split(":")[-1].strip()
    return [corrected] if corrected else []


# ---------------------------------------------------------------------------
# Background tasks
# ---------------------------------------------------------------------------
async def _bg_save_turn(
    session_id: str,
    sequence_num: int,
    transcript: str,
    audio_s3_key: str | None,
    pace_label: str,
    wps: float,
    ai_response: str,
    grammar_notes: list[str],
    model_version: str,
    latency_ms: int,
):
    """Persist a Turn row in the background so the response isn't delayed."""
    from app.core.database import AsyncSessionLocal
    from app.services.session_service import save_turn

    async with AsyncSessionLocal() as db:
        try:
            await save_turn(
                db,
                session_id=uuid.UUID(session_id),
                sequence_num=sequence_num,
                transcript=transcript,
                audio_s3_key=audio_s3_key,
                pace_label=pace_label,
                wps=wps,
                ai_response=ai_response,
                grammar_notes=grammar_notes,
                model_version=model_version,
                latency_ms=latency_ms,
            )
            await db.commit()
        except Exception:
            logger.exception("Background save_turn failed")
            await db.rollback()


async def _bg_upload_s3(file_bytes: bytes, session_id: str, turn_num: int):
    """Upload audio to S3 in the background. Failures are logged, never raised."""
    from app.services.storage_service import upload_audio

    await upload_audio(file_bytes, session_id, turn_num)


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------
@router.post("/upload", response_model=UploadResponse)
async def upload_audio_endpoint(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    audio: UploadFile = File(...),
    session_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Accept audio, transcribe, generate follow-up, return structured feedback.

    If ``session_id`` is provided, the turn is persisted as a BackgroundTask.
    Audio is uploaded to S3 as a BackgroundTask (never blocks response).
    """
    from asr.asr_func import transcribe_audio, calculate_speaking_pace  # lazy
    from model.inference import generate_output  # lazy

    start = time.perf_counter()

    # Read file bytes and save to /tmp
    file_id = uuid.uuid4()
    tmp_path = f"/tmp/{file_id}.wav"
    file_bytes = await audio.read()
    with open(tmp_path, "wb") as f:
        f.write(file_bytes)

    # --- ASR ---
    try:
        model_size = settings.WHISPER_MODEL_SIZE
        if model_size == "mock":
            transcript = "mock transcript"
            wps = 2.5
        else:
            from faster_whisper import WhisperModel

            asr_model = WhisperModel(model_size, device="cpu")
            transcript = transcribe_audio(asr_model, tmp_path)
            wps = calculate_speaking_pace(transcript, DEFAULT_CHUNK_LENGTH)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    pace_label_val = _pace_label(wps)

    # --- LLM follow-up ---
    llm_prompt = (
        f"You are now conducting an interview. "
        f"The candidate said: {transcript}. "
        f"Formulate a thoughtful follow-up question."
    )
    ai_response = generate_output(llm_prompt)

    # --- Grammar ---
    grammar_notes = _grammar_check(transcript)

    latency_ms = int((time.perf_counter() - start) * 1000)

    # --- Background: S3 upload ---
    turn_num = 1  # Will be overridden if session is tracked
    if session_id:
        # Determine next sequence_num from session (simple default for now)
        background_tasks.add_task(
            _bg_save_turn,
            str(session_id),
            turn_num,
            transcript,
            None,  # audio_s3_key filled later if S3 succeeds
            pace_label_val,
            wps,
            ai_response,
            grammar_notes,
            settings.MODEL_VERSION,
            latency_ms,
        )
    background_tasks.add_task(_bg_upload_s3, file_bytes, str(session_id or file_id), turn_num)

    return UploadResponse(
        transcript=transcript,
        pace_label=pace_label_val,
        wps=round(wps, 2),
        ai_response=ai_response,
        grammar_notes=grammar_notes,
        model_version=settings.MODEL_VERSION,
        latency_ms=latency_ms,
        session_id=session_id,
    )
