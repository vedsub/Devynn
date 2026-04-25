"""
POST /upload — transcribe audio, generate follow-up, return structured response.
Persists turn and uploads audio to S3 as background tasks.
"""

import logging
import os
import time
import uuid
import json
import asyncio
from threading import Thread

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, Form, UploadFile, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import UploadResponse
from app.core.config import settings
from app.core.database import get_db
from app.core.db_models import User
from app.core.security import get_current_user
from app.api.deps import get_cache, get_llm

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


async def _bg_log_flywheel(session_id: str, domain: str, transcript: str, ai_response: str, pace_label: str, wps: float, model_version: str):
    """Log the turn to the training data flywheel bucket on S3."""
    from app.services.flywheel_service import log_training_candidate
    import uuid

    class DummyTurn:
        def __init__(self):
            self.transcript = transcript
            self.ai_response = ai_response
            self.pace_label = pace_label
            self.wps = wps
            self.model_version = model_version

    class DummySession:
        def __init__(self):
            self.id = session_id
            self.domain = domain

    await log_training_candidate(DummyTurn(), DummySession())


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.post("/upload", response_model=UploadResponse)
async def upload_audio_endpoint(
    background_tasks: BackgroundTasks,
    response: Response,
    current_user: User = Depends(get_current_user),
    audio: UploadFile = File(...),
    domain: str = Query("SDE"),
    session_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    llm = Depends(get_llm),
    cache = Depends(get_cache),
):
    from asr.asr_func import transcribe_audio, calculate_speaking_pace

    start = time.perf_counter()

    file_id = uuid.uuid4()
    tmp_path = f"/tmp/{file_id}.wav"
    file_bytes = await audio.read()
    with open(tmp_path, "wb") as f:
        f.write(file_bytes)

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
    turn_num = 1
    
    cached = await cache.get(domain, transcript)
    if cached:
        response.headers["X-Cache"] = "HIT"
        ai_response = cached['ai_response']
        grammar_notes = cached.get('grammar_notes', [])
        latency_ms = int((time.perf_counter() - start) * 1000)
    else:
        response.headers["X-Cache"] = "MISS"
        ai_response, grammar_notes, _ = await llm.generate(transcript, domain)
        latency_ms = int((time.perf_counter() - start) * 1000)
        await cache.set(domain, transcript, {"ai_response": ai_response, "grammar_notes": grammar_notes})

    if session_id:
        background_tasks.add_task(
            _bg_save_turn,
            str(session_id),
            turn_num,
            transcript,
            None,
            pace_label_val,
            wps,
            ai_response,
            grammar_notes,
            llm.version,
            latency_ms,
        )
        background_tasks.add_task(
            _bg_log_flywheel,
            str(session_id),
            domain,
            transcript,
            ai_response,
            pace_label_val,
            wps,
            llm.version,
        )
    background_tasks.add_task(_bg_upload_s3, file_bytes, str(session_id or file_id), turn_num)

    return UploadResponse(
        transcript=transcript,
        pace_label=pace_label_val,
        wps=round(wps, 2),
        ai_response=ai_response,
        grammar_notes=grammar_notes,
        model_version=llm.version,
        latency_ms=latency_ms,
        session_id=session_id,
    )


@router.post("/upload/stream")
async def upload_stream(
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...),
    domain: str = Form("SDE"),
    session_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    llm = Depends(get_llm),
    cache = Depends(get_cache),
):
    from asr.asr_func import transcribe_audio, calculate_speaking_pace
    start = time.perf_counter()

    file_id = uuid.uuid4()
    tmp_path = f"/tmp/{file_id}.wav"
    file_bytes = await audio.read()
    with open(tmp_path, "wb") as f:
        f.write(file_bytes)

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
    cached = await cache.get(domain, transcript)
    turn_num = 1

    if cached:
        async def event_stream_cached():
            yield f"data: {json.dumps({'type':'transcript','text':transcript,'pace':pace_label_val})}\n\n"
            yield f"data: {json.dumps({'type':'token','text':cached['ai_response']})}\n\n"
            yield f"data: {json.dumps({'type':'done','model_version':llm.version})}\n\n"
        
        # bg tasks
        if session_id:
            background_tasks.add_task(
                _bg_save_turn, str(session_id), turn_num, transcript, None, pace_label_val, wps, cached['ai_response'], cached.get('grammar_notes', []), llm.version, int((time.perf_counter() - start) * 1000)
            )
            background_tasks.add_task(_bg_log_flywheel, str(session_id), domain, transcript, cached['ai_response'], pace_label_val, wps, llm.version)
        background_tasks.add_task(_bg_upload_s3, file_bytes, str(session_id or file_id), turn_num)
        return StreamingResponse(event_stream_cached(), media_type="text/event-stream", headers={"Cache-Control":"no-cache", "X-Accel-Buffering":"no", "X-Cache":"HIT"})

    # Miss
    async def event_stream_miss():
        yield f"data: {json.dumps({'type':'transcript','text':transcript,'pace':pace_label_val})}\n\n"
        
        full_text = ""
        mock_mode = os.environ.get("MODEL_PATH") == "mock"
        
        if mock_mode:
            mock_tokens = ["Mock ", "follow-up ", f"question for {domain}."]
            for t in mock_tokens:
                full_text += t
                yield f"data: {json.dumps({'type':'token','text':t})}\n\n"
                await asyncio.sleep(0.1)
        else:
            from transformers import TextIteratorStreamer
            import torch
            streamer = TextIteratorStreamer(llm._tokenizer, skip_prompt=True, skip_special_tokens=True)
            prompt = (
                f"You are now conducting an interview for the {domain} role.\n"
                f"The candidate said: {transcript}\n"
                f"Formulate a thoughtful follow-up question."
            )
            model_input = llm._tokenizer(prompt, return_tensors="pt")
            kwargs = dict(**model_input, streamer=streamer, max_new_tokens=200)
            Thread(target=llm._model.generate, kwargs=kwargs).start()

            for token in streamer:
                full_text += token
                yield f"data: {json.dumps({'type':'token','text':token})}\n\n"
                await asyncio.sleep(0)
                
        yield f"data: {json.dumps({'type':'done','model_version':llm.version})}\n\n"
        
        # update cache directly in stream gen finish
        await cache.set(domain, transcript, {"ai_response": full_text, "grammar_notes": []})
        
        if session_id:
            await _bg_save_turn(str(session_id), turn_num, transcript, None, pace_label_val, wps, full_text, [], llm.version, int((time.perf_counter() - start) * 1000))
            background_tasks.add_task(_bg_log_flywheel, str(session_id), domain, transcript, full_text, pace_label_val, wps, llm.version)
            
    background_tasks.add_task(_bg_upload_s3, file_bytes, str(session_id or file_id), turn_num)
    return StreamingResponse(event_stream_miss(), media_type="text/event-stream", headers={"Cache-Control":"no-cache", "X-Accel-Buffering":"no", "X-Cache":"MISS"})
