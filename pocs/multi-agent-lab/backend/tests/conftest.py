from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Must be set before importing app modules
os.environ["DATABASE_URL"] = "sqlite://"  # overridden below via StaticPool
os.environ.setdefault("OPENAI_API_KEY", "")
os.environ.setdefault("APP_ENV", "test")

from database import Base, get_db  # noqa: E402
from main import app  # noqa: E402

# Single shared in-memory SQLite connection for all tests in the session.
# StaticPool ensures every create_engine call reuses the same connection,
# so tables created here are visible to the app's sessions.
_TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(bind=_TEST_ENGINE)

_TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=_TEST_ENGINE)


def _override_get_db():
    session = _TestingSession()
    try:
        yield session
    finally:
        session.close()


# Patch the app's engine so init_db() on startup also hits the same DB
import database as _db_module  # noqa: E402
_db_module.engine = _TEST_ENGINE
_db_module.SessionLocal = _TestingSession


@pytest.fixture
def db():
    """Fresh session per test, rolled back after."""
    session = _TestingSession()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client():
    """Test client with DB overridden to the shared in-memory engine."""
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
