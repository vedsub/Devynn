"""
Auth routes: register & login.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import AuthRegister, TokenResponse
from app.core import security
from app.core.database import get_db
from app.core.db_models import User
from app.core.logging_config import get_logger

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: AuthRegister, db: AsyncSession = Depends(get_db)):
    """Create a new user and return an access token."""
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=body.email,
        hashed_password=security.hash_password(body.password),
    )
    db.add(user)
    await db.flush()  # populate user.id

    token = security.create_access_token(data={"sub": str(user.id)})
    return TokenResponse(access_token=token, token_type="bearer")


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with email + password, return access token."""
    logger.info("login_attempt", event="login_attempt", email=form_data.username)
    
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not security.verify_password(form_data.password, user.hashed_password):
        logger.info("login_failed", event="login_failed", email=form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info("login_success", event="login_success", email=form_data.username)
    token = security.create_access_token(data={"sub": str(user.id)})
    return TokenResponse(access_token=token, token_type="bearer")
