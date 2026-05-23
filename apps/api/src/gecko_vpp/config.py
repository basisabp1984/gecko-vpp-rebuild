"""Pydantic-settings configuration for GECKO VPP API.

Reads `.env` from project root (two levels up from this file's package).
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# .env lives at <repo root>/.env, two levels up from apps/api/
REPO_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = REPO_ROOT / ".env"


class Settings(BaseSettings):
    """Environment-driven settings.

    All vars come from .env (or actual environment, which wins over .env).
    """

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://gecko:dev_local_pwd_2026@localhost:5433/gecko_vpp",
        description="async SQLAlchemy URL (asyncpg driver) — superuser for migrations/seeding",
    )
    # API runtime uses gecko_api (NOBYPASSRLS) so RLS policies actually apply.
    # Override via API_DATABASE_URL in .env if needed.
    api_database_url: str = Field(
        default="postgresql+asyncpg://gecko_api:gecko_api_pwd@localhost:5433/gecko_vpp",
        description="async DSN used by FastAPI runtime; NOBYPASSRLS role required",
    )
    postgres_db: str = "gecko_vpp"
    postgres_user: str = "gecko"
    postgres_password: str = "dev_local_pwd_2026"
    postgres_host: str = "localhost"
    postgres_port: int = 5433

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"

    # Tenants (fixed UUIDs — seeded in migration 012)
    tenant_producer_uuid: str = "11111111-1111-1111-1111-111111111111"
    tenant_ci_uuid: str = "22222222-2222-2222-2222-222222222222"
    tenant_storage_uuid: str = "33333333-3333-3333-3333-333333333333"

    # Voice / agents
    voice_provider: str = "stub"
    openai_api_key: str = ""

    # Synth window
    synth_date_start: str = "2026-04-23"
    synth_date_end: str = "2026-05-23"
    synth_rng_seed: int = 42

    @property
    def database_url_sync(self) -> str:
        """Sync DSN for alembic (psycopg driver)."""
        return self.database_url.replace("+asyncpg", "+psycopg")


_settings: Settings | None = None


def get_settings() -> Settings:
    """Cached settings accessor."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
