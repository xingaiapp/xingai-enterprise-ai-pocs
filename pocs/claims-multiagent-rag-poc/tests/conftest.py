"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from claims_rag.ingestion.build_vector_store import build_vector_store


@pytest.fixture(scope="session")
def vector_store_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("chroma_session")
    build_vector_store(persist_dir=path)
    return path


@pytest.fixture
def audit_db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db = tmp_path / "audit.sqlite"
    monkeypatch.setenv("AUDIT_DB_PATH", str(db))
    from claims_rag.config import get_env_settings

    get_env_settings.cache_clear()
    return db
