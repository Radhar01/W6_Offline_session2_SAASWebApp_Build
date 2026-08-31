"""Application configuration, loaded from environment variables / .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # App metadata
    APP_NAME: str = "ClipCreator"
    APP_VERSION: str = "0.1.0"
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/clipcreator"

    # Media / file storage
    MEDIA_STORAGE_PATH: str = "./media"
    MAX_UPLOAD_SIZE_MB: int = 2048

    # Video processing
    FFMPEG_PATH: str = "ffmpeg"

    # B-roll sourcing (optional). Without a key, clips fall back to a
    # blurred copy of their own footage as the vertical background.
    PEXELS_API_KEY: str | None = None

    # yt-dlp PO-token provider (optional). Without it, YouTube downloads
    # from datacenter/VPS IPs are frequently blocked ("Sign in to confirm
    # you're not a bot"). See services/url_ingest_service.py.
    BGUTIL_PROVIDER_URL: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (single source of truth app-wide)."""
    return Settings()


# Module-level singleton for convenience (`from app.config import settings`).
settings = get_settings()
