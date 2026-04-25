"""
Session routes: create, list, and get turns.
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import SessionCreate, SessionResponse, TurnResponse
from app.core.database import get_db
from app.core.db_models import User
from app.core.security import get_current_user
from app.services.session_service import (
    create_session,
    get_session_turns,
    get_user_sessions,
)

router = APIRouter(tags=["sessions"])


@router.post("/sessions", response_model=SessionResponse, status_code=201)
async def create_session_endpoint(
    body: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new interview session for the authenticated user."""
    session = await create_session(db, user_id=current_user.id, domain=body.domain)
    return SessionResponse(
        session_id=session.id,
        domain=session.domain,
        created_at=session.started_at,
    )


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the authenticated user's interview sessions."""
    sessions = await get_user_sessions(db, user_id=current_user.id)
    return [
        SessionResponse(
            session_id=s.id,
            domain=s.domain,
            created_at=s.started_at,
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}/turns", response_model=list[TurnResponse])
async def list_turns(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all turns for a session owned by the authenticated user."""
    turns = await get_session_turns(db, session_id=session_id, user_id=current_user.id)
    return turns
