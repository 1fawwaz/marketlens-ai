"""End-to-end integration tests."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.app.auth.jwt_auth import ensure_default_user
from backend.app.database import get_engine
from backend.app.main import app
from backend.app.ml.pipeline import run_ml_pipeline
from backend.app.rag.search import ingest_documents


def _db_available() -> bool:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="PostgreSQL unavailable")


@pytest.fixture(scope="module")
def client():
    run_ml_pipeline()
    ingest_documents()
    ensure_default_user()
    return TestClient(app)


def _token(client: TestClient) -> str:
    resp = client.post(
        "/auth/login",
        json={
            "username": os.environ["ADMIN_USERNAME"],
            "password": os.environ["ADMIN_PASSWORD"],
        },
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_auth_and_kpis(client):
    token = _token(client)
    resp = client.get("/api/kpis", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "revenue" in data
    assert "variance_pct" in data


def test_investigate_endpoint(client):
    token = _token(client)
    resp = client.post(
        "/api/investigate",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "We missed the sales target by 12%. What factors contributed to the gap?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["target_month"] == "2019-02-01"
    assert body["evidence_bundle"]["supporting_query_ids"]
    assert body["evidence_bundle"]["forecast_vs_target"]["grain"] == "category"
    assert body["report_provider"] in {"deterministic_fallback", "groq"}
