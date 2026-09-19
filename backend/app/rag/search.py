"""RAG ingestion and hybrid search with pgvector primary path."""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi
from sqlalchemy import text

from backend.app.database import ensure_pgvector_schema, get_engine, pgvector_available

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAG_DIR = PROJECT_ROOT / "data" / "rag"
EMBED_DIM = 384

_embedder = None
_bm25_index: BM25Okapi | None = None
_corpus_chunks: list[dict] = []
_active_backend: str | None = None


def _tokenize(text_value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text_value.lower())


def _get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer

        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def get_rag_backend(force_refresh: bool = False) -> str:
    global _active_backend
    if force_refresh or _active_backend is None:
        _active_backend = "pgvector" if pgvector_available() else "json_fallback"
    return _active_backend


def load_synthetic_documents() -> list[dict]:
    docs = []
    for path in sorted(RAG_DIR.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        sections = re.split(r"\n## ", content)
        for section in sections[1:]:
            lines = section.splitlines()
            section_title = lines[0].strip()
            body = "\n".join(lines[1:]).strip()
            if body:
                docs.append(
                    {
                        "doc_name": path.name,
                        "section_title": section_title,
                        "chunk_text": body,
                        "is_synthetic": True,
                    }
                )
    return docs


def ingest_documents() -> dict:
    engine = get_engine()
    backend = ensure_pgvector_schema(engine)
    global _active_backend
    _active_backend = backend

    docs = load_synthetic_documents()
    embedder = _get_embedder()
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE rag_documents RESTART IDENTITY"))
        for doc in docs:
            embedding = embedder.encode(doc["chunk_text"]).tolist()
            if backend == "pgvector":
                conn.execute(
                    text(
                        """
                        INSERT INTO rag_documents
                        (doc_name, section_title, chunk_text, is_synthetic, embedding_json, embedding_vector)
                        VALUES (:doc_name, :section_title, :chunk_text, :is_synthetic,
                                CAST(:embedding AS jsonb), CAST(:vector AS vector))
                        """
                    ),
                    {
                        **doc,
                        "embedding": json.dumps(embedding),
                        "vector": f"[{','.join(str(v) for v in embedding)}]",
                    },
                )
            else:
                conn.execute(
                    text(
                        """
                        INSERT INTO rag_documents
                        (doc_name, section_title, chunk_text, is_synthetic, embedding_json)
                        VALUES (:doc_name, :section_title, :chunk_text, :is_synthetic, CAST(:embedding AS jsonb))
                        """
                    ),
                    {**doc, "embedding": json.dumps(embedding)},
                )
    _refresh_memory_index()
    return {"chunks": len(docs), "backend": backend}


def _refresh_memory_index() -> None:
    global _bm25_index, _corpus_chunks
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT doc_id, doc_name, section_title, chunk_text, is_synthetic, embedding_json
                FROM rag_documents
                """
            )
        ).mappings().all()
    _corpus_chunks = [dict(r) for r in rows]
    tokenized = [_tokenize(r["chunk_text"]) for r in _corpus_chunks]
    _bm25_index = BM25Okapi(tokenized) if tokenized else None


def _vector_search_pg(query: str, top_k: int) -> list[dict]:
    embedder = _get_embedder()
    query_vec = embedder.encode(query).tolist()
    vector_literal = f"[{','.join(str(v) for v in query_vec)}]"
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT doc_id, doc_name, section_title, chunk_text, is_synthetic,
                       1 - (embedding_vector <=> CAST(:query_vec AS vector)) AS vector_score
                FROM rag_documents
                WHERE embedding_vector IS NOT NULL
                ORDER BY embedding_vector <=> CAST(:query_vec AS vector)
                LIMIT :top_k
                """
            ),
            {"query_vec": vector_literal, "top_k": top_k},
        ).mappings().all()
    return [dict(r) for r in rows]


def hybrid_search(query: str, top_k: int = 5) -> list[dict]:
    backend = get_rag_backend()
    if backend == "pgvector":
        vector_rows = _vector_search_pg(query, top_k * 2)
        if not _corpus_chunks:
            _refresh_memory_index()
        bm25_scores = (
            _bm25_index.get_scores(_tokenize(query))
            if _bm25_index
            else np.zeros(len(_corpus_chunks))
        )
        bm25_by_id = {
            chunk["doc_id"]: float(bm25_scores[i]) if i < len(bm25_scores) else 0.0
            for i, chunk in enumerate(_corpus_chunks)
        }
        max_bm25 = max(bm25_by_id.values()) if bm25_by_id else 1.0
        results = []
        for row in vector_rows:
            bm25_norm = bm25_by_id.get(row["doc_id"], 0.0) / (max_bm25 or 1.0)
            score = 0.6 * float(row["vector_score"]) + 0.4 * bm25_norm
            results.append(
                {
                    "doc_id": row["doc_id"],
                    "doc_name": row["doc_name"],
                    "section_title": row["section_title"],
                    "chunk_text": row["chunk_text"][:500],
                    "is_synthetic": row["is_synthetic"],
                    "score": round(score, 4),
                    "retrieval_backend": "pgvector",
                    "citation": f"{row['doc_name']} § {row['section_title']}",
                }
            )
        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:top_k]

    # Explicit JSON fallback — not equivalent to pgvector
    if not _corpus_chunks:
        _refresh_memory_index()
    if not _corpus_chunks:
        return []

    embedder = _get_embedder()
    query_vec = np.array(embedder.encode(query))
    bm25_scores = _bm25_index.get_scores(_tokenize(query)) if _bm25_index else np.zeros(len(_corpus_chunks))
    results = []
    for i, chunk in enumerate(_corpus_chunks):
        emb = np.array(chunk["embedding_json"])
        cosine = float(
            np.dot(query_vec, emb) / (np.linalg.norm(query_vec) * np.linalg.norm(emb) + 1e-9)
        )
        bm25_norm = float(bm25_scores[i] / (max(bm25_scores.max(), 1e-9)))
        score = 0.6 * cosine + 0.4 * bm25_norm
        results.append(
            {
                "doc_id": chunk["doc_id"],
                "doc_name": chunk["doc_name"],
                "section_title": chunk["section_title"],
                "chunk_text": chunk["chunk_text"][:500],
                "is_synthetic": chunk["is_synthetic"],
                "score": round(score, 4),
                "retrieval_backend": "json_fallback",
                "citation": f"{chunk['doc_name']} § {chunk['section_title']}",
            }
        )
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_k]
