"""Verify pgvector path against Docker PostgreSQL on port 5433."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import psycopg2
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def _docker_postgres_ready() -> bool:
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5433,
            user="marketlens",
            password="marketlens_dev",
            dbname="marketlens",
        )
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def pgvector_docker_stack():
    if not _docker_available():
        pytest.skip("Docker not available")
    subprocess.run(
        ["docker", "compose", "-f", "docker-compose.pgvector-test.yml", "up", "-d", "postgres"],
        cwd=PROJECT_ROOT,
        check=False,
    )
    deadline = time.time() + 90
    while time.time() < deadline:
        if _docker_postgres_ready():
            break
        time.sleep(3)
    if not _docker_postgres_ready():
        pytest.skip("pgvector docker postgres not reachable on :5433")
    yield
    subprocess.run(
        ["docker", "compose", "-f", "docker-compose.pgvector-test.yml", "down", "-v"],
        cwd=PROJECT_ROOT,
        check=False,
    )


@pytest.mark.skipif(not _docker_available(), reason="Docker not available")
def test_pgvector_docker_retrieval(pgvector_docker_stack):
    prev_host = os.environ.get("POSTGRES_HOST")
    prev_port = os.environ.get("POSTGRES_PORT")
    os.environ["POSTGRES_HOST"] = "localhost"
    os.environ["POSTGRES_PORT"] = "5433"

    from backend.app.config import get_settings
    from backend.app.database import ensure_pgvector_schema, get_engine, pgvector_available
    from backend.app.rag.search import hybrid_search, ingest_documents

    get_settings.cache_clear()
    get_engine.cache_clear()
    try:
        assert get_settings().postgres_port == 5433
        backend = ensure_pgvector_schema()
        assert backend == "pgvector", f"expected pgvector, got {backend}"
        assert pgvector_available()
        ingest = ingest_documents()
        assert ingest["backend"] == "pgvector"
        results = hybrid_search("variance explanation shortfall", top_k=2)
        assert results
        assert results[0]["retrieval_backend"] == "pgvector"
    finally:
        if prev_host is None:
            os.environ.pop("POSTGRES_HOST", None)
        else:
            os.environ["POSTGRES_HOST"] = prev_host
        if prev_port is None:
            os.environ.pop("POSTGRES_PORT", None)
        else:
            os.environ["POSTGRES_PORT"] = prev_port
        get_settings.cache_clear()
        get_engine.cache_clear()
