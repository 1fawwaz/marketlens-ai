"""One-time setup: create marketlens database, user, and apply schema."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "sql" / "schema.sql"

ADMIN_USER = os.getenv("PG_ADMIN_USER", "postgres")
ADMIN_PASSWORD = os.getenv("PG_ADMIN_PASSWORD", "postgres")
DB_NAME = os.getenv("POSTGRES_DB", "marketlens")
DB_USER = os.getenv("POSTGRES_USER", "marketlens")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "marketlens_dev")


def main() -> None:
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user=ADMIN_USER,
        password=ADMIN_PASSWORD,
        dbname="postgres",
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (DB_USER,))
    if cur.fetchone() is None:
        cur.execute(f"CREATE USER {DB_USER} WITH PASSWORD %s", (DB_PASSWORD,))

    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
    if cur.fetchone() is None:
        cur.execute(f"CREATE DATABASE {DB_NAME} OWNER {DB_USER}")

    cur.execute(f"GRANT ALL PRIVILEGES ON DATABASE {DB_NAME} TO {DB_USER}")
    cur.close()
    conn.close()

    app_conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=DB_NAME,
    )
    app_conn.autocommit = True
    cur = app_conn.cursor()

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    extensions_sql = (PROJECT_ROOT / "sql" / "schema_extensions.sql").read_text(encoding="utf-8")
    # Skip pgvector if not installed (Phase 4 dependency)
    try:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    except psycopg2.Error:
        print("Note: pgvector not installed — using embedding_json fallback")
    cur.execute(schema_sql)
    cur.execute(extensions_sql)
    try:
        cur.execute("ALTER TABLE rag_documents ADD COLUMN IF NOT EXISTS embedding_vector vector(384)")
    except psycopg2.Error:
        print("Note: pgvector column unavailable — JSON embedding fallback only")

    cur.close()
    app_conn.close()
    print(f"Database '{DB_NAME}' ready with schema applied.")


if __name__ == "__main__":
    main()
