"""Tests for vector store ingestion."""

from pathlib import Path

import chromadb

from claims_rag.ingestion.build_vector_store import build_vector_store, chunk_text
from claims_rag.ingestion.embeddings import HashEmbeddingFunction


def test_chunk_text_overlap() -> None:
    text = "a" * 1000
    chunks = chunk_text(text, chunk_size=300, overlap=50)
    assert len(chunks) >= 3
    assert all(len(c) <= 300 for c in chunks)


def test_build_vector_store(tmp_path: Path) -> None:
    counts = build_vector_store(persist_dir=tmp_path / "chroma")
    assert counts["policy_documents"] > 0
    assert counts["claim_history"] > 0
    assert counts["regulations"] > 0

    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    policies = client.get_collection(
        "policy_documents",
        embedding_function=HashEmbeddingFunction(),
    )
    result = policies.query(query_texts=["windshield glass coverage"], n_results=2)
    assert len(result["ids"][0]) >= 1
    assert "document_id" in result["metadatas"][0][0]
