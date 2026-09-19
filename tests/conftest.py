"""Pytest configuration."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Required settings for tests — no hard-coded production credentials
os.environ.setdefault("JWT_SECRET", "pytest-jwt-secret-not-for-production")
os.environ.setdefault("ADMIN_USERNAME", "pytest_admin")
os.environ.setdefault("ADMIN_PASSWORD", "pytest_password_not_for_production")
os.environ.setdefault("POSTGRES_PASSWORD", "marketlens_dev")

from backend.app.config import get_settings

get_settings.cache_clear()


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "groq_live: test requires live Groq API key from .env",
    )


@pytest.fixture(autouse=True)
def deterministic_llm_by_default(request, monkeypatch):
    """Avoid live Groq calls in tests unless explicitly marked groq_live."""
    if not request.node.get_closest_marker("groq_live"):
        monkeypatch.setenv("GROQ_API_KEY", "")
        get_settings.cache_clear()
    yield
    get_settings.cache_clear()
