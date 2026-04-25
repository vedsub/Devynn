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
    """Load the Mistral LLM once and store it in app.state."""
    import os

    if os.environ.get("MODEL_PATH") == "mock":
        application.state.llm = None
    else:
        try:
            from model.inference import model as llm_model
            application.state.llm = llm_model
        except Exception:
            application.state.llm = None
    yield
    application.state.llm = None


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Devynn – AI Interview Assistant",
    version="0.2.0",
    lifespan=lifespan,
)

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
