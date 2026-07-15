"""Unit tests for config validation."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError


@pytest.fixture(autouse=True)
def _set_required_env(monkeypatch: pytest.MonkeyPatch):
    """Settings requires a few env vars to load; provide test values."""
    monkeypatch.setenv("FERNET_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("SECRET_KEY", "x" * 48)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://odmig:odmig@localhost:5432/odmig")
    yield


def test_invalid_storage_backend_rejected(monkeypatch: pytest.MonkeyPatch):
    """Config rejects storage_backend outside allowed set."""
    monkeypatch.setenv("STORAGE_BACKEND", "btrfs")
    from app.config import Settings

    with pytest.raises(ValidationError):
        Settings()


def test_invalid_app_env_rejected(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "qa")
    from app.config import Settings

    with pytest.raises(ValidationError):
        Settings()


def test_settings_supported_locales_list(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SUPPORTED_LOCALES", "de, fr , it")
    from app.config import Settings

    s = Settings()
    assert s.supported_locales_list == ["de", "fr", "it"]


def test_settings_is_production_property(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "production")
    from app.config import Settings

    s = Settings()
    assert s.is_production is True


def test_settings_default_locale(monkeypatch: pytest.MonkeyPatch):
    from app.config import Settings

    s = Settings()
    assert s.default_locale == "de"
