"""
Devynn – AI Interview Assistant
FastAPI application entry-point.
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.routes import auth, health, session, upload
from app.core.config import settings

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path so that `asr` and `model` packages
# are importable when running with `uvicorn app.main:app` from devynn/.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Lifespan – load heavy models once at startup
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(application: FastAPI):
    """Load caching and LLM models once at startup."""
    import os
    from app.services.cache_service import CacheService
    from app.services.llm_service import LLMService
    
    cache = CacheService()
    await cache.connect()
    application.state.cache = cache

    llm = LLMService()
    if os.environ.get("MODEL_PATH") != "mock":
        try:
            await llm.load(settings.MODEL_PATH or "akshatshaw/mistral-interview-finetune", settings.MODEL_VERSION)
        except Exception as e:
            print("Failed to load model:", e)
    else:
        await llm.load("mock", "mock-version")
    application.state.llm = llm

    yield
    application.state.llm = None
    application.state.cache = None

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Devynn – AI Interview Assistant",
    version="0.2.0",
    lifespan=lifespan,
)

# Admin routes for flushing cache
@app.delete("/admin/cache/flush", tags=["admin"])
async def flush_cache(
    request: Request
):
    admin_token = request.headers.get("x-admin-token")
    if admin_token != settings.ADMIN_TOKEN:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Invalid admin token")
    
    cache = request.app.state.cache
    if cache:
        await cache.flush()
    return {"status": "flushed"}

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.ALLOWED_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router, tags=["health"])
app.include_router(auth.router)
app.include_router(upload.router, tags=["upload"])
app.include_router(session.router)

# Jinja2 templates
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "templates"))


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Render the interview chat UI."""
    return templates.TemplateResponse("home.html", {"request": request, "name": "Candidate"})
