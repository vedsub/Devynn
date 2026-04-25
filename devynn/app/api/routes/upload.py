import os
import time
import uuid

from fastapi import APIRouter, UploadFile, File

from app.api.schemas import UploadResponse
from app.core.config import settings

router = APIRouter()

# ---------------------------------------------------------------------------
# Pace helpers (mirrors original Flask logic)
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
    """Run a grammar check via the LLM and return notes list."""
    from model.inference import generate_output  # lazy import

    prompt = f'Correct "{text}" to standard English and place the results in "Correct Text:"'
    raw = generate_output(prompt)
    corrected = raw.split(":")[-1].strip()
    return [corrected] if corrected else []


@router.post("/upload", response_model=UploadResponse)
async def upload_audio(audio: UploadFile = File(...)):
    """Accept an audio file, transcribe, generate a follow-up question, and
    return structured feedback."""
    from asr.asr_func import transcribe_audio, calculate_speaking_pace  # lazy
    from model.inference import generate_output  # lazy

    start = time.perf_counter()

    # Save uploaded file to /tmp
    file_id = uuid.uuid4()
    tmp_path = f"/tmp/{file_id}.wav"
    contents = await audio.read()
    with open(tmp_path, "wb") as f:
        f.write(contents)

    # --- ASR ---
    try:
        from faster_whisper import WhisperModel

        model_size = settings.WHISPER_MODEL_SIZE
        if model_size == "mock":
            transcript = "mock transcript"
            wps = 2.5
        else:
            asr_model = WhisperModel(model_size, device="cpu")
            transcript = transcribe_audio(asr_model, tmp_path)
            wps = calculate_speaking_pace(transcript, DEFAULT_CHUNK_LENGTH)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    pace_label = _pace_label(wps)

    # --- LLM follow-up question ---
    llm_prompt = (
        f"You are now conducting an interview. "
        f"The candidate said: {transcript}. "
        f"Formulate a thoughtful follow-up question."
    )
    ai_response = generate_output(llm_prompt)

    # --- Grammar notes ---
    grammar_notes = _grammar_check(transcript)

    latency_ms = int((time.perf_counter() - start) * 1000)

    return UploadResponse(
        transcript=transcript,
        pace_label=pace_label,
        wps=round(wps, 2),
        ai_response=ai_response,
        grammar_notes=grammar_notes,
        model_version=settings.MODEL_VERSION,
        latency_ms=latency_ms,
    )
