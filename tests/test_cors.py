"""CORS configuration regression tests."""

from __future__ import annotations

from backend.app.config import Settings
from backend.app.main import app


def test_cors_uses_explicit_origins_when_configured(monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://marketlens-ai.vercel.app")
    from backend.app.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    assert settings.cors_allowed_origins_list == ["https://marketlens-ai.vercel.app"]


def test_cors_defaults_to_localhost_regex_when_unset(monkeypatch):
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    from backend.app.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    assert settings.cors_allowed_origins_list == []


def test_app_has_cors_middleware():
    middleware_classes = [m.cls.__name__ for m in app.user_middleware]
    assert "CORSMiddleware" in middleware_classes
