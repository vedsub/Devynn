import json
import asyncio
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from threading import Thread
from transformers import TextIteratorStreamer

from app.core.security import get_current_user_ws
from app.api.deps import get_llm
from model.inference import build_prompt

router = APIRouter()

@router.websocket("/ws/interview")
async def realtime_interview(websocket: WebSocket, token: str, domain: str = "SDE"):
    # Authenticate via query param token (JWT)
    user = await get_current_user_ws(token)
    if not user:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    
    whisper_model = websocket.app.state.whisper
    llm = await get_llm(websocket)
    
    audio_buffer = bytearray()
    full_transcript = ""
    silent_chunks = 0
    CHUNK_SAMPLES = 16000 * 2    # 2 seconds at 16kHz
    SILENCE_RMS = 0.01
    END_SILENCE = 3              # 3 silent chunks = end of speech

    try:
        while True:
            data = await websocket.receive_bytes()
            audio_buffer.extend(data)
            
            if len(audio_buffer) < CHUNK_SAMPLES * 2:
                continue

            chunk = bytes(audio_buffer[:CHUNK_SAMPLES * 2])
            audio_buffer = audio_buffer[CHUNK_SAMPLES * 2:]

            pcm = np.frombuffer(chunk, np.int16).astype(np.float32) / 32768.0
            
            if np.sqrt(np.mean(pcm**2)) < SILENCE_RMS:
                silent_chunks += 1
            else:
                silent_chunks = 0
                segments, _ = whisper_model.transcribe(pcm, language="en", beam_size=1, vad_filter=True)
                chunk_text = " ".join(s.text for s in segments).strip()
                if chunk_text:
                    full_transcript += " " + chunk_text
                    await websocket.send_text(json.dumps({"type": "partial", "text": chunk_text}))

            if silent_chunks >= END_SILENCE and full_transcript.strip():
                await websocket.send_text(json.dumps({"type": "transcript_final", "text": full_transcript.strip()}))

                streamer = TextIteratorStreamer(llm._tokenizer, skip_prompt=True, skip_special_tokens=True)
                inputs = llm._tokenizer(build_prompt(full_transcript.strip(), domain), return_tensors="pt").to("cuda")
                Thread(target=llm._model.generate, kwargs={**inputs, "streamer": streamer, "max_new_tokens": 200}).start()

                full_response = ""
                for llm_token in streamer:
                    full_response += llm_token
                    await websocket.send_text(json.dumps({"type": "token", "text": llm_token}))
                    await asyncio.sleep(0)

                await websocket.send_text(json.dumps({"type": "done", "response": full_response.strip()}))
                
                # Reset for next turn
                full_transcript = ""
                silent_chunks = 0

    except WebSocketDisconnect:
        pass
