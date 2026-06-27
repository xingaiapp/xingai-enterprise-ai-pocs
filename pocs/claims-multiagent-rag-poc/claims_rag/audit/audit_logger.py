"""
Immutable SQLite audit log + PII redaction utility.

Production path: encryption at rest, field-level ACL, retention policy.
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from claims_rag.config import get_env_settings, get_policy_config


def redact(text: str) -> str:
    """Strip patterns resembling SSN / long account numbers before logging."""
    policy = get_policy_config()
    redacted = text
    for pattern in policy.audit.pii_redact_patterns:
        redacted = re.sub(pattern, "[REDACTED]", redacted)
    return redacted


def _redact_obj(value: Any) -> Any:
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, dict):
        return {k: _redact_obj(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_obj(v) for v in value]
    return value


class AuditLogger:
    """Append-only audit trail — one row per agent step."""

    def __init__(self, db_path: Path | None = None) -> None:
        env = get_env_settings()
        self.db_path = db_path or env.audit_db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_trail (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trace_id TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    input_json TEXT NOT NULL,
                    output_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_trace_id ON audit_trail(trace_id)"
            )

    def log_step(
        self,
        trace_id: str,
        *,
        agent: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        payload_in = json.dumps(_redact_obj(input_data), ensure_ascii=False)
        payload_out = json.dumps(_redact_obj(output_data), ensure_ascii=False)
        meta = json.dumps(metadata or {}, ensure_ascii=False)
        created = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_trail
                (trace_id, agent, input_json, output_json, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (trace_id, agent, payload_in, payload_out, meta, created),
            )

    def get_trace(self, trace_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, trace_id, agent, input_json, output_json, metadata_json, created_at
                FROM audit_trail
                WHERE trace_id = ?
                ORDER BY id ASC
                """,
                (trace_id,),
            ).fetchall()
        results: list[dict[str, Any]] = []
        for row in rows:
            results.append(
                {
                    "id": row[0],
                    "trace_id": row[1],
                    "agent": row[2],
                    "input": json.loads(row[3]),
                    "output": json.loads(row[4]),
                    "metadata": json.loads(row[5]),
                    "created_at": row[6],
                }
            )
        return results
