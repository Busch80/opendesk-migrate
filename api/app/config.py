"""Configuration management.

All values are loaded from environment variables (.env in development).
Pydantic Settings handles validation and casting.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        validate_default=True,
    )

    # Application ------------------------------------------------------------------
    app_env: Annotated[str, Field(description="Application environment")] = "development"
    app_debug: Annotated[bool, Field(description="Debug mode")] = True
    app_log_level: Annotated[str, Field(description="Log level")] = "INFO"
    app_url: Annotated[str, Field(description="Public base URL")] = "http://localhost:8080"
    app_name: Annotated[str, Field(description="Application name")] = "opendesk-migrate"

    # Database --------------------------------------------------------------------
    database_url: Annotated[str, Field(description="PostgreSQL DSN (async)")]
    database_pool_size: Annotated[int, Field(ge=1, le=100)] = 10
    database_max_overflow: Annotated[int, Field(ge=0, le=100)] = 20
    database_pool_timeout: Annotated[int, Field(ge=5, le=300)] = 30

    # Redis -----------------------------------------------------------------------
    redis_url: Annotated[str, Field(description="Redis URL")] = "redis://localhost:6379/0"
    redis_result_backend: Annotated[str, Field(description="Celery result backend")] = "redis://localhost:6379/1"

    # Encryption ------------------------------------------------------------------
    fernet_key: Annotated[str, Field(min_length=44, max_length=44, description="Fernet key for token encryption")]
    secret_key: Annotated[str, Field(min_length=32, description="App secret key for signing")]

    # Storage ---------------------------------------------------------------------
    storage_backend: Annotated[str, Field(description="Storage backend")] = "local"
    staging_path: Annotated[str, Field(description="Local staging path")] = "/staging"
    staging_max_gb: Annotated[int, Field(ge=1, le=10000)] = 500
    staging_retention_days: Annotated[int, Field(ge=1, le=90)] = 14

    # M365 ------------------------------------------------------------------------
    m365_default_tenant_id: Annotated[str, Field(default="", description="M365 tenant ID (only as template)")]
    m365_authority: Annotated[str, Field(description="Microsoft authority URL")] = "https://login.microsoftonline.com"

    # Celery ----------------------------------------------------------------------
    celery_worker_concurrency_mail: Annotated[int, Field(ge=1, le=32)] = 4
    celery_worker_concurrency_cal_contacts: Annotated[int, Field(ge=1, le=32)] = 2
    celery_worker_concurrency_onedrive: Annotated[int, Field(ge=1, le=32)] = 4
    celery_task_time_limit: Annotated[int, Field(ge=60, le=86400)] = 7200

    # Graph Rate limits -----------------------------------------------------------
    graph_requests_per_minute: Annotated[int, Field(ge=100, le=100000)] = 5000
    graph_burst_size: Annotated[int, Field(ge=1, le=1000)] = 50
    graph_retry_max_attempts: Annotated[int, Field(ge=1, le=20)] = 5

    # Observability ---------------------------------------------------------------
    prometheus_enabled: Annotated[bool, Field(description="Enable Prometheus /metrics")] = True
    loki_url: Annotated[str, Field(default="", description="Loki push URL (optional)")]
    sentry_dsn: Annotated[str, Field(default="", description="Sentry DSN (optional)")]

    # i18n ------------------------------------------------------------------------
    default_locale: Annotated[str, Field(min_length=2, max_length=5)] = "de"
    supported_locales: Annotated[str, Field(description="Comma-separated supported locales")] = "de,fr,it,en"

    # OpenDesk defaults -----------------------------------------------------------
    ox_default_url: Annotated[str, Field(default="", description="OX default URL")]
    nc_default_url: Annotated[str, Field(default="", description="Nextcloud default URL")]

    @field_validator("storage_backend")
    @classmethod
    def _validate_storage_backend(cls, v: str) -> str:
        allowed = {"local", "s3"}
        if v not in allowed:
            raise ValueError(f"storage_backend must be one of {allowed}, got {v!r}")
        return v

    @field_validator("app_env")
    @classmethod
    def _validate_env(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"app_env must be one of {allowed}, got {v!r}")
        return v

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def supported_locales_list(self) -> list[str]:
        return [s.strip() for s in self.supported_locales.split(",") if s.strip()]

    @property
    def fernet_key_bytes(self) -> bytes:
        return self.fernet_key.encode("ascii")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings singleton.

    Returns a fresh instance per process (each Celery worker has its own).
    lru_cache is per-process anyway.
    """
    return Settings()  # type: ignore[call-arg]


def get_storage_path() -> Path:
    """Absolute path to the staging directory."""
    settings = get_settings()
    path = Path(settings.staging_path).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


__all__ = ["Settings", "get_settings", "get_storage_path"]
