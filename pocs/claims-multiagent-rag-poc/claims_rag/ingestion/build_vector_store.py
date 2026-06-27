"""
Build Chroma vector collections from synthetic markdown/JSON sources.

Three collections — never mixed:
  - policy_documents
  - claim_history
  - regulations

Run once (or after data changes):
  python -m claims_rag.ingestion.build_vector_store
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import chromadb
from chromadb.api.types import EmbeddingFunction

from claims_rag.config import POC_ROOT, get_env_settings, get_policy_config
from claims_rag.ingestion.embeddings import HashEmbeddingFunction

logger = logging.getLogger(__name__)

DATA_DIR = POC_ROOT / "data"


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Simple character-based chunker with overlap."""
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = end - overlap
    return [c for c in chunks if c]


def _load_policy_docs() -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for path in sorted((DATA_DIR / "synthetic_policies").glob("*.md")):
        docs.append(
            {
                "document_id": path.stem,
                "source_path": str(path.relative_to(POC_ROOT)),
                "text": path.read_text(encoding="utf-8"),
            }
        )
    return docs


def _load_regulation_docs() -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for path in sorted((DATA_DIR / "synthetic_regulations").glob("*.md")):
        docs.append(
            {
                "document_id": path.stem,
                "source_path": str(path.relative_to(POC_ROOT)),
                "text": path.read_text(encoding="utf-8"),
            }
        )
    return docs


def _load_claim_history_docs() -> list[dict[str, Any]]:
    path = DATA_DIR / "synthetic_claim_history" / "claim_history.json"
    records = json.loads(path.read_text(encoding="utf-8"))
    docs: list[dict[str, Any]] = []
    for rec in records:
        text = (
            f"Policy {rec['policy_number']} claim {rec['claim_id']}: "
            f"{rec['description']} Amount ${rec['amount_usd']:.2f} "
            f"on {rec['incident_date']} status {rec['status']} type {rec['claim_type']}."
        )
        docs.append(
            {
                "document_id": rec["claim_id"],
                "source_path": str(path.relative_to(POC_ROOT)),
                "text": text,
                "policy_number": rec["policy_number"],
            }
        )
    return docs


def _get_embedding_function(env: Any, policy: Any) -> EmbeddingFunction:
    """OpenAI embeddings when key present; else offline hash embeddings."""
    if env.openai_api_key and policy.embeddings.provider == "openai":
        from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

        return OpenAIEmbeddingFunction(
            api_key=env.openai_api_key,
            model_name=policy.embeddings.model,
        )
    return HashEmbeddingFunction()


def _upsert_collection(
    client: chromadb.PersistentClient,
    collection_name: str,
    documents: list[dict[str, Any]],
    chunk_size: int,
    overlap: int,
    embedding_fn: EmbeddingFunction,
) -> int:
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass

    kwargs: dict[str, Any] = {
        "name": collection_name,
        "metadata": {"hnsw:space": "cosine"},
        "embedding_function": embedding_fn,
    }
    collection = client.get_or_create_collection(**kwargs)

    ids: list[str] = []
    texts: list[str] = []
    metadatas: list[dict[str, Any]] = []

    for doc in documents:
        for i, chunk in enumerate(chunk_text(doc["text"], chunk_size, overlap)):
            chunk_id = f"{doc['document_id']}::chunk-{i}"
            ids.append(chunk_id)
            texts.append(chunk)
            meta = {
                "document_id": doc["document_id"],
                "chunk_id": chunk_id,
                "source_path": doc.get("source_path", ""),
                "collection": collection_name,
            }
            if "policy_number" in doc:
                meta["policy_number"] = doc["policy_number"]
            metadatas.append(meta)

    if ids:
        collection.add(ids=ids, documents=texts, metadatas=metadatas)
    return len(ids)


def build_vector_store(persist_dir: Path | None = None) -> dict[str, int]:
    """Ingest all synthetic sources; return chunk counts per collection."""
    env = get_env_settings()
    policy = get_policy_config()
    persist = persist_dir or env.chroma_persist_dir
    persist.mkdir(parents=True, exist_ok=True)

    embedding_fn = _get_embedding_function(env, policy)
    client = chromadb.PersistentClient(path=str(persist))

    vs = policy.vector_store
    counts = {
        vs.collections["policy_documents"]: _upsert_collection(
            client,
            vs.collections["policy_documents"],
            _load_policy_docs(),
            vs.chunk_size,
            vs.chunk_overlap,
            embedding_fn,
        ),
        vs.collections["claim_history"]: _upsert_collection(
            client,
            vs.collections["claim_history"],
            _load_claim_history_docs(),
            vs.chunk_size,
            vs.chunk_overlap,
            embedding_fn,
        ),
        vs.collections["regulations"]: _upsert_collection(
            client,
            vs.collections["regulations"],
            _load_regulation_docs(),
            vs.chunk_size,
            vs.chunk_overlap,
            embedding_fn,
        ),
    }
    logger.info("Vector store built at %s: %s", persist, counts)
    return counts


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    counts = build_vector_store()
    for name, n in counts.items():
        print(f"{name}: {n} chunks indexed")


if __name__ == "__main__":
    main()
