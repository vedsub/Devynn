import structlog
import os
import uuid
from starlette.middleware.base import BaseHTTPMiddleware


def configure_logging():
    is_prod = os.environ.get("ENV", "dev") == "production"
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer() if is_prod else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
    )


def get_logger(name="devynn"):
    return structlog.get_logger(name)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        rid = str(uuid.uuid4())[:8]
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=rid, method=request.method, path=request.url.path)
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response
