import uuid
from datetime import datetime, timezone

from fastapi import APIRouter

from app.api.schemas import SessionCreate, SessionResponse

router = APIRouter()


@router.post("/session", response_model=SessionResponse)
async def create_session(body: SessionCreate):
    """Create a new interview session.

    NOTE: This is a stub that returns an in-memory session.
    Swap in a real DB call once the database layer is wired up.
    """
    return SessionResponse(
        session_id=uuid.uuid4(),
        domain=body.domain,
        created_at=datetime.now(timezone.utc),
    )
