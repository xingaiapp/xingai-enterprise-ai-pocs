"""
Retrieval Agent — RAG over three isolated Chroma collections.

Every chunk returns citation metadata (document_id, chunk_id, similarity).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import chromadb
from chromadb.api.types import EmbeddingFunction

from claims_rag.config import get_env_settings, get_policy_config
from claims_rag.ingestion.build_vector_store import _get_embedding_function
from claims_rag.ingestion.embeddings import HashEmbeddingFunction
from claims_rag.models import ClaimData, DocumentCitation, RetrievalBundle

logger = logging.getLogger(__name__)


def _client_and_embedding() -> tuple[chromadb.PersistentClient, EmbeddingFunction]:
    env = get_env_settings()
    policy = get_policy_config()
    embedding_fn = _get_embedding_function(env, policy)
    client = chromadb.PersistentClient(path=str(env.chroma_persist_dir))
    return client, embedding_fn


def _distance_to_similarity(distance: float) -> float:
    """Chroma cosine distance → similarity in [0, 1]."""
    return max(0.0, min(1.0, 1.0 - distance))


def _query_collection(
    client: chromadb.PersistentClient,
    collection_name: str,
    query: str,
    *,
    top_k: int,
    min_score: float,
    embedding_fn: EmbeddingFunction,
    policy_filter: str | None = None,
) -> list[DocumentCitation]:
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )
    where: dict[str, Any] | None = None
    if policy_filter and collection_name == "claim_history":
        where = {"policy_number": policy_filter}

    try:
        result = collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as exc:
        logger.warning("retrieval_query_failed", extra={"collection": collection_name, "error": str(exc)})
        return []

    citations: list[DocumentCitation] = []
    if not result["ids"] or not result["ids"][0]:
        return citations

    for i, chunk_id in enumerate(result["ids"][0]):
        meta = (result["metadatas"] or [[{}]])[0][i] or {}
        text = (result["documents"] or [[""]])[0][i] or ""
        dist = (result["distances"] or [[1.0]])[0][i] or 1.0
        score = _distance_to_similarity(float(dist))
        if score < min_score:
            continue
        citations.append(
            DocumentCitation(
                document_id=str(meta.get("document_id", "unknown")),
                chunk_id=str(meta.get("chunk_id", chunk_id)),
                collection=collection_name,
                text=text,
                similarity_score=score,
                source_path=str(meta.get("source_path", "")),
            )
        )
    return citations


def build_retrieval_query(claim: ClaimData) -> str:
    return (
        f"Policy {claim.policy_number} {claim.claim_type.value} "
        f"{claim.incident_description} amount {claim.claimed_amount}"
    )


def run_retrieval(
    claim: ClaimData,
    *,
    trace_id: str = "",
    persist_dir: Path | None = None,
) -> RetrievalBundle:
    """Retrieve top-k chunks from each collection."""
    policy_cfg = get_policy_config()
    env = get_env_settings()
    if persist_dir:
        client = chromadb.PersistentClient(path=str(persist_dir))
        embedding_fn = _get_embedding_function(env, policy_cfg)
    else:
        client, embedding_fn = _client_and_embedding()

    if not isinstance(embedding_fn, HashEmbeddingFunction) and embedding_fn is None:
        embedding_fn = HashEmbeddingFunction()

    query = build_retrieval_query(claim)
    top_k = policy_cfg.retrieval.top_k_per_collection
    min_score = policy_cfg.retrieval.min_similarity_score
    collections = policy_cfg.vector_store.collections

    bundle = RetrievalBundle(
        policy_excerpts=_query_collection(
            client,
            collections["policy_documents"],
            query,
            top_k=top_k,
            min_score=min_score,
            embedding_fn=embedding_fn,
        ),
        history_excerpts=_query_collection(
            client,
            collections["claim_history"],
            query,
            top_k=top_k,
            min_score=min_score,
            embedding_fn=embedding_fn,
            policy_filter=claim.policy_number,
        ),
        regulation_excerpts=_query_collection(
            client,
            collections["regulations"],
            query,
            top_k=top_k,
            min_score=min_score,
            embedding_fn=embedding_fn,
        ),
    )
    logger.info(
        "retrieval_complete",
        extra={
            "trace_id": trace_id,
            "policy_chunks": len(bundle.policy_excerpts),
            "history_chunks": len(bundle.history_excerpts),
            "regulation_chunks": len(bundle.regulation_excerpts),
        },
    )
    return bundle
