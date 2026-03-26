from typing import Optional

from anyio.functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.
    """

    gooogle_client_id: Optional[str] = None
    google_redirect_uri: Optional[str] = None
    google_client_secret: Optional[str] = None

    supabase_url: str
    supabase_key: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


@lru_cache
def get_settings():
    """
    Creates a cached instance of the settings.
    Using lru_cache ensures the .env isn't re-read on every request.
    """
    return Settings()