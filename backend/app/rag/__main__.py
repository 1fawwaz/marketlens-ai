"""CLI entry for RAG ingestion."""

from backend.app.rag.search import ingest_documents

if __name__ == "__main__":
    result = ingest_documents()
    print(result)
