"""Phase 4 RAG tests."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from backend.app.database import get_engine
from backend.app.rag.search import hybrid_search, ingest_documents, load_synthetic_documents


def _db_available() -> bool:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="PostgreSQL unavailable")


def test_synthetic_documents_labeled():
    docs = load_synthetic_documents()
    assert len(docs) >= 3
    assert all(d["is_synthetic"] for d in docs)


def test_ingest_and_search():
    ingest = ingest_documents()
    assert ingest["chunks"] >= 3
    assert ingest["backend"] in {"pgvector", "json_fallback"}
    results = hybrid_search("variance explanation shortfall", top_k=3)
    assert results
    assert all(r["is_synthetic"] for r in results)
    assert all("citation" in r for r in results)
    assert all("retrieval_backend" in r for r in results)
