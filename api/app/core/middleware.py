import time
import logging
from urllib.parse import urlparse
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from app.core.settings import Settings

logger = logging.getLogger(__name__)


def setup_middleware(app: FastAPI, settings: Settings) -> None:
    origins = settings.cors_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # TrustedHostMiddleware only makes sense with explicit origins (not wildcard)
    if settings.environment == "production" and origins != ["*"]:
        hosts = [urlparse(o).hostname or o for o in origins]
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=hosts,
        )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        logger.info(
            "%s %s → %d  (%.3fs)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed,
        )
        response.headers["X-Process-Time"] = f"{elapsed:.4f}"
        return response
