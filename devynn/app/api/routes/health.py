from fastapi import APIRouter

from app.api.schemas import HealthResponse
from app.core.config import settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health():
    """Return service health and model status."""
    return HealthResponse(
        status="ok",
        model_loaded=True,
        model_version=settings.MODEL_VERSION,
    )
