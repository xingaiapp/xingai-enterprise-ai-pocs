from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


_DATABASE_URL = os.environ.get("DATABASE_URL", "")
if _DATABASE_URL:
    _connect_args = {"check_same_thread": False} if _DATABASE_URL.startswith("sqlite") else {}
    engine = create_engine(_DATABASE_URL, connect_args=_connect_args)
else:
    DB_DIR = Path(__file__).resolve().parent / "db"
    DB_DIR.mkdir(exist_ok=True)
    DB_FILE = DB_DIR / "app.db"
    engine = create_engine(
        f"sqlite:///{DB_FILE}",
        connect_args={"check_same_thread": False},
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class DemoRun(Base):
    __tablename__ = "demo_runs"

    request_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_input: Mapped[str] = mapped_column(Text)
    final_answer: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TraceLog(Base):
    __tablename__ = "trace_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(36), index=True)
    step: Mapped[int] = mapped_column(Integer)
    agent_name: Mapped[str] = mapped_column(String(80))
    input_text: Mapped[str] = mapped_column(Text, default="")
    output_text: Mapped[str] = mapped_column(Text, default="")
    tool_used: Mapped[str] = mapped_column(String(120), default="")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CacheEntry(Base):
    __tablename__ = "cache_entries"

    cache_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    cache_value: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _migrate_trace_duration()


def _migrate_trace_duration() -> None:
    """Add duration_ms to existing SQLite DBs from earlier POC runs."""
    with engine.connect() as conn:
        rows = conn.exec_driver_sql("PRAGMA table_info(trace_logs)").fetchall()
        cols = {r[1] for r in rows}
        if "duration_ms" not in cols and rows:
            conn.exec_driver_sql("ALTER TABLE trace_logs ADD COLUMN duration_ms INTEGER DEFAULT 0")
            conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
