from fastapi import Request
from app.core.config import settings


def get_settings():
    """Return the application settings singleton."""
    return settings


def get_cache(request: Request):
    return request.app.state.cache


def get_llm(request: Request):
    return request.app.state.llm
