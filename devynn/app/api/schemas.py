from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


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


# ---------------------------------------------------------------------------
# Auth schemas
# ---------------------------------------------------------------------------
class AuthRegister(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Turn schema
# ---------------------------------------------------------------------------
class TurnResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    sequence_num: int
    transcript: str
    audio_s3_key: Optional[str] = None
    pace_label: str
    wps: float
    ai_response: str
    grammar_notes: list
    model_version: str
    latency_ms: int
    created_at: datetime
