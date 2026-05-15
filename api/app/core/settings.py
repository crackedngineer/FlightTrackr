from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # OAuth — Google
    google_client_id: Optional[str] = None
    google_redirect_uri: Optional[str] = None
    google_mail_redirect_uri: Optional[str] = None
    google_client_secret: Optional[str] = None

    # OAuth — Microsoft (Outlook)
    microsoft_client_id: Optional[str] = None
    microsoft_client_secret: Optional[str] = None
    microsoft_redirect_uri: Optional[str] = None

    # App URLs
    base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    # Database
    supabase_url: str
    supabase_key: str
    supabase_service_role_key: Optional[str] = None
    database_url: str
    sync_database_url: str

    # Celery / Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # Token encryption — generate with: Fernet.generate_key().decode()
    oauth_token_encryption_key: Optional[str] = None

    # Gmail sync
    gmail_search_query: str = "has:attachment filename:pdf boarding pass"
    gmail_max_results: int = 100

    # App
    app_name: str = "FlightTrackr API"
    app_version: str = "1.0.0"
    app_description: str = "API for parsing boarding passes and managing user data."
    environment: str = "development"
    debug: bool = False

    # Security — comma-separated string e.g. "http://localhost:3000,https://app.example.com"
    allowed_origins: str = "*"
    jwt_secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Logging
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
