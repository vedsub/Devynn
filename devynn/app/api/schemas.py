from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UploadResponse(BaseModel):
    transcript: str
    pace_label: str
    wps: float
    ai_response: str
    grammar_notes: list[str]
    model_version: str
    latency_ms: int
    audio_s3_key: Optional[str] = None
    session_id: Optional[UUID] = None


class SessionCreate(BaseModel):
    domain: Literal["SDE", "DS", "PM"]


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: UUID
    domain: str
    created_at: datetime


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_version: str
