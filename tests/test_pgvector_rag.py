"""pgvector RAG path tests."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from backend.app.database import ensure_pgvector_schema, get_engine, pgvector_available
from backend.app.rag.search import get_rag_backend, hybrid_search, ingest_documents


def _db_available() -> bool:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="PostgreSQL unavailable")


def test_pgvector_schema_when_extension_available():
    backend = ensure_pgvector_schema()
    if pgvector_available():
        assert backend == "pgvector"
        ingest = ingest_documents()
        assert ingest["backend"] == "pgvector"
        results = hybrid_search("variance explanation shortfall", top_k=2)
        assert results
        assert results[0]["retrieval_backend"] == "pgvector"
    else:
        pytest.skip("pgvector extension unavailable in current PostgreSQL")


def test_json_fallback_labeled_when_pgvector_missing(monkeypatch):
    monkeypatch.setattr("backend.app.rag.search.pgvector_available", lambda: False)
    monkeypatch.setattr("backend.app.rag.search.ensure_pgvector_schema", lambda engine=None: "json_fallback")
    ingest = ingest_documents()
    assert ingest["backend"] == "json_fallback"
    results = hybrid_search("target miss escalation", top_k=2)
    if results:
        assert results[0]["retrieval_backend"] == "json_fallback"


def test_get_rag_backend_reports_active_mode():
    backend = get_rag_backend()
    assert backend in {"pgvector", "json_fallback"}
