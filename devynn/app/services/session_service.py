"""
Session & Turn CRUD operations.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db_models import InterviewSession, Turn


async def create_session(
    db: AsyncSession,
    user_id: UUID,
    domain: str,
) -> InterviewSession:
    """Create and return a new InterviewSession."""
    session = InterviewSession(user_id=user_id, domain=domain)
    db.add(session)
    await db.flush()
    return session


async def save_turn(
    db: AsyncSession,
    session_id: UUID,
    sequence_num: int,
    transcript: str,
    audio_s3_key: str | None,
    pace_label: str,
    wps: float,
    ai_response: str,
    grammar_notes: list,
    model_version: str,
    latency_ms: int,
) -> Turn:
    """Persist a single interview turn."""
    turn = Turn(
        session_id=session_id,
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
    db.add(turn)
    await db.flush()
    return turn


async def get_user_sessions(
    db: AsyncSession,
    user_id: UUID,
    limit: int = 20,
) -> list[InterviewSession]:
    """Return the user's most recent interview sessions."""
    result = await db.execute(
        select(InterviewSession)
        .where(InterviewSession.user_id == user_id)
        .order_by(InterviewSession.started_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_session_turns(
    db: AsyncSession,
    session_id: UUID,
    user_id: UUID,
) -> list[Turn]:
    """Return all turns for a session owned by the given user."""
    result = await db.execute(
        select(Turn)
        .join(InterviewSession)
        .where(
            Turn.session_id == session_id,
            InterviewSession.user_id == user_id,
        )
        .order_by(Turn.sequence_num)
    )
    return list(result.scalars().all())
