"""Phase 6 hardening tests."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import text

from backend.app.auth.jwt_auth import authenticate_user, create_access_token, ensure_default_user
from backend.app.database import get_engine
from backend.app.ml.drift import run_drift_check


def _db_available() -> bool:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="PostgreSQL unavailable")


def test_jwt_auth_flow():
    ensure_default_user()
    assert authenticate_user(os.environ["ADMIN_USERNAME"], os.environ["ADMIN_PASSWORD"])
    token = create_access_token(os.environ["ADMIN_USERNAME"])
    assert isinstance(token, str)


def test_drift_monitoring():
    logs = run_drift_check()
    assert len(logs) >= 3
    with get_engine().connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM forecast_drift_log")).scalar()
    assert count >= 3
