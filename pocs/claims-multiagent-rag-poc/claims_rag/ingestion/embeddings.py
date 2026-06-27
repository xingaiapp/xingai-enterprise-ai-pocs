"""
Local embedding fallback when OpenAI key or onnxruntime is unavailable.

Uses deterministic bag-of-words hashing — good enough for the small synthetic corpus.
Production path: OpenAI text-embedding-3-small or hosted bge-small.
"""

from __future__ import annotations

import hashlib
from typing import cast

import numpy as np
from chromadb.api.types import EmbeddingFunction, Embeddings


class HashEmbeddingFunction(EmbeddingFunction):
    """Offline embedding function — no API keys, no onnxruntime."""

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim

    def name(self) -> str:
        return "hash_embedding"

    def __call__(self, input: list[str]) -> Embeddings:
        vectors: list[list[float]] = []
        for text in input:
            vec = np.zeros(self.dim, dtype=np.float32)
            for token in text.lower().split():
                digest = hashlib.md5(token.encode("utf-8")).digest()
                for i, byte in enumerate(digest):
                    vec[(i + byte) % self.dim] += (byte - 128) / 128.0
            norm = float(np.linalg.norm(vec))
            if norm > 0:
                vec = vec / norm
            vectors.append(cast(list[float], vec.tolist()))
        return vectors
