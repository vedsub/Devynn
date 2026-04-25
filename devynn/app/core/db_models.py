"""
SQLAlchemy 2.0 async ORM models for Devynn.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4, UUID

from sqlalchemy import ForeignKey, func, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    """Shared declarative base for all models."""
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    sessions: Mapped[list["InterviewSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    domain: Mapped[str]
    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    completed_at: Mapped[Optional[datetime]]

    turns: Mapped[list["Turn"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    user: Mapped["User"] = relationship(back_populates="sessions")


class Turn(Base):
    __tablename__ = "turns"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("interview_sessions.id"), index=True
    )
    sequence_num: Mapped[int]
    transcript: Mapped[str] = mapped_column(Text)
    audio_s3_key: Mapped[Optional[str]]
    pace_label: Mapped[str]
    wps: Mapped[float]
    ai_response: Mapped[str] = mapped_column(Text)
    grammar_notes: Mapped[list] = mapped_column(JSONB, default=list)
    model_version: Mapped[str]
    latency_ms: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    session: Mapped["InterviewSession"] = relationship(back_populates="turns")
