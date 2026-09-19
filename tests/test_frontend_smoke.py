"""Frontend/API smoke coverage for dashboard workflows."""

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
def smoke_client():
    run_ml_pipeline()
    ingest_documents()
    ensure_default_user()
    return TestClient(app)


def _auth_headers(client: TestClient) -> dict[str, str]:
    username = os.environ["ADMIN_USERNAME"]
    password = os.environ["ADMIN_PASSWORD"]
    resp = client.post("/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_smoke_auth_login(smoke_client):
    headers = _auth_headers(smoke_client)
    assert "Authorization" in headers


def test_smoke_dashboard_kpis(smoke_client):
    resp = smoke_client.get("/api/kpis", headers=_auth_headers(smoke_client))
    assert resp.status_code == 200
    body = resp.json()
    assert {"revenue", "target_total", "variance_pct", "active_anomalies"} <= body.keys()


def test_smoke_forecast_endpoint(smoke_client):
    resp = smoke_client.get(
        "/api/forecasts/Clothing?horizon=30&model=xgboost",
        headers=_auth_headers(smoke_client),
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_smoke_anomaly_endpoint(smoke_client):
    resp = smoke_client.get("/api/anomalies?dimension=state", headers=_auth_headers(smoke_client))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_smoke_investigation_with_evidence_ids(smoke_client):
    resp = smoke_client.post(
        "/api/investigate",
        headers=_auth_headers(smoke_client),
        json={"question": "We missed the sales target by 12%. What factors contributed to the gap?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["month_resolution"]["mode"] == "percent_match"
    assert body["target_month"] == "2019-02-01"
    assert body["evidence_bundle"]["supporting_query_ids"]
    assert "VARIANCE_2019-02-01" in body["evidence_bundle"]["supporting_query_ids"]
    assert body["report_provider"] in {"deterministic_fallback", "groq"}


def test_smoke_explicit_month_investigation(smoke_client):
    resp = smoke_client.post(
        "/api/investigate",
        headers=_auth_headers(smoke_client),
        json={
            "question": "Investigate target miss for 2018-11-01 — what factors contributed?"
        },
    )
    assert resp.status_code == 200
    assert resp.json()["target_month"] == "2018-11-01"
    assert resp.json()["month_resolution"]["mode"] == "explicit_date"


@pytest.mark.parametrize(
    "question",
    [
        "Why did we miss the February 2019 sales target?",
        "Which category contributed most to the sales shortfall?",
        "Which state performed worst?",
        "Why did we miss the target?",
        "Give me an executive summary of sales performance.",
    ],
)
def test_smoke_investigation_ui_questions(smoke_client, question):
    resp = smoke_client.post(
        "/api/investigate",
        headers=_auth_headers(smoke_client),
        json={"question": question},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["target_month"]
    assert body["month_resolution"]["mode"]
    assert body["evidence_bundle"]["supporting_query_ids"]
    assert body["report"]
