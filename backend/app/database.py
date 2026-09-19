"""Database engine helper."""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from backend.app.config import get_settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True)


def pgvector_available(engine: Engine | None = None) -> bool:
    engine = engine or get_engine()
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            ).fetchone()
            if row is None:
                return False
            col = conn.execute(
                text(
                    """
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'rag_documents'
                      AND column_name = 'embedding_vector'
                    """
                )
            ).fetchone()
            return col is not None
    except Exception:
        return False


def ensure_pgvector_schema(engine: Engine | None = None) -> str:
    """Create pgvector extension/column/index when supported. Returns backend name."""
    engine = engine or get_engine()
    with engine.begin() as conn:
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.execute(
                text(
                    "ALTER TABLE rag_documents ADD COLUMN IF NOT EXISTS embedding_vector vector(384)"
                )
            )
            try:
                conn.execute(
                    text(
                        """
                        CREATE INDEX IF NOT EXISTS idx_rag_embedding_vector
                        ON rag_documents USING ivfflat (embedding_vector vector_cosine_ops)
                        WITH (lists = 1)
                        """
                    )
                )
            except Exception:
                pass
        except Exception:
            return "json_fallback"
    return "pgvector" if pgvector_available(engine) else "json_fallback"
