"""Minimal offline retrieval over policy_documents.py's clause chunks.

Deliberately dependency-light: a hashing-trick bag-of-words embedding
(pure Python, no numpy, no external embedding API) plus cosine similarity.
This is the same "offline hash embeddings when no API key" idea
claims-multiagent-rag-poc uses for its vector store fallback — applied
here as the only embedding path, on purpose, since the corpus per policy
is tiny (a handful of clauses) and doesn't need a real vector DB. What
this buys: retrieval that's deterministic and testable with zero external
dependencies, so Policy Coverage's citation quality can improve (real
clause text, not a 3-entry dict) without adding a new "Not Production Yet"
external-service dependency.
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import List

VECTOR_DIM = 128


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def embed(text: str) -> List[float]:
    vec = [0.0] * VECTOR_DIM
    for tok in _tokenize(text):
        digest = hashlib.md5(tok.encode()).hexdigest()
        h = int(digest, 16)
        idx = h % VECTOR_DIM
        sign = 1.0 if (h // VECTOR_DIM) % 2 == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def search_policy_documents(policy_id: str, query: str, k: int = 3) -> List[dict]:
    from . import policy_documents

    chunks = policy_documents.get_chunks(policy_id)
    if not chunks:
        return []

    query_vec = embed(query)
    scored = [
        {**chunk, "score": round(cosine_similarity(query_vec, embed(f"{chunk['title']}. {chunk['text']}")), 4)}
        for chunk in chunks
    ]
    scored.sort(key=lambda c: c["score"], reverse=True)
    return scored[:k]
