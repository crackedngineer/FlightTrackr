import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.settings import get_settings, Settings
from app.core.exceptions import setup_exception_handlers
from app.core.middleware import setup_middleware
from app.routes.v1 import health, boarding_pass
from app.routes.v1.endpoints import auth, flights, gmail, user, mail_connections
import app.mail.registry as mail_registry
from app.mail.gmail import GmailProvider
from app.mail.outlook import OutlookProvider
from app.mail.protonmail import ProtonMailProvider


def _register_mail_providers(settings: Settings) -> None:
    if settings.google_client_id:
        mail_registry.register(GmailProvider(settings))
    if settings.microsoft_client_id:
        mail_registry.register(OutlookProvider(settings))
    mail_registry.register(ProtonMailProvider())


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    _register_mail_providers(settings)
    logging.info("FlightTrackr API starting up…")
    yield
    logging.info("FlightTrackr API shutting down…")


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=settings.app_description,
        root_path="/api",
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
        openapi_url=("/openapi.json" if settings.environment != "production" else None),
        lifespan=lifespan,
    )

    setup_middleware(app, settings)
    setup_exception_handlers(app)

    ROUTE_PREFIX = ""
    app.include_router(health.router, prefix=f"{ROUTE_PREFIX}/v1", tags=["Health"])
    app.include_router(
        auth.router, prefix=f"{ROUTE_PREFIX}/v1", tags=["Authentication"]
    )
    app.include_router(
        boarding_pass.router, prefix=f"{ROUTE_PREFIX}/v1", tags=["Boarding Pass"]
    )
    app.include_router(flights.router, prefix=f"{ROUTE_PREFIX}/v1", tags=["Trips"])
    app.include_router(gmail.router, prefix=f"{ROUTE_PREFIX}/v1", tags=["Gmail"])
    app.include_router(user.router, prefix=f"{ROUTE_PREFIX}/v1", tags=["User"])
    app.include_router(
        mail_connections.router, prefix=f"{ROUTE_PREFIX}/v1", tags=["Mail Connections"]
    )

    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "message": f"Welcome to {settings.app_name}. Visit /api/docs for API documentation.",
            "version": settings.app_version,
            "environment": settings.environment,
        }

    return app


def get_application() -> FastAPI:
    return create_app()
