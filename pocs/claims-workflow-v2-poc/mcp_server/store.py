"""In-memory stores backing this server's tools.

Moved here from claims_workflow.agents.policy_coverage (MOCK_POLICIES),
claims_workflow.ledger (ledger rows), and claims_workflow.agents.payment
(_SETTLEMENTS) per ADR-009 Phase 1 — this server is now the single owner
of this state; claims_workflow no longer touches any of it directly.

Global, not per-claim: the same claim_id can legitimately appear across
many requests (retries, resumes) and should accumulate ledger rows the
same way a real shared Decision Ledger table would. `reset_all_for_tests()`
exists purely so this POC's pytest suite gets test-to-test isolation
without pretending a real deployment would ever reset its audit trail.
"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Policy fixture — same 3 entries claims_workflow.agents.policy_coverage
# shipped in ADR-008, moved here unchanged.
# ---------------------------------------------------------------------------

MOCK_POLICIES: Dict[str, dict] = {
    "POL-1001": {"covered_loss_types": ["auto"], "limit": 15000.0, "clause": "Section 4.2(b) — Collision Coverage"},
    "POL-1002": {"covered_loss_types": ["property"], "limit": 8000.0, "clause": "Section 3.1(a) — Dwelling Coverage"},
    "POL-1003": {"covered_loss_types": ["auto", "property"], "limit": 25000.0, "clause": "Section 4.2(b) / 3.1(a) — Combined"},
}
NO_POLICY_CLAUSE = "Section 1.1 — No Active Policy on File"
WRONG_LOSS_TYPE_CLAUSE = "Section 2.3 — Loss Type Not Covered Under This Policy"

# ---------------------------------------------------------------------------
# Decision Ledger rows
# ---------------------------------------------------------------------------

_ledger_lock = threading.Lock()
_LEDGER_ROWS: List[dict] = []

# ---------------------------------------------------------------------------
# Payment settlements, keyed by idempotency key
# ---------------------------------------------------------------------------

_payment_lock = threading.Lock()
_SETTLEMENTS: Dict[str, dict] = {}


def record_ledger_row(
    *,
    domain: str,
    question: str,
    recommendation: str,
    reasoning: List[str],
    confidence: float,
    claim_id: Optional[str],
    alternatives: Optional[List[str]] = None,
    risks: Optional[List[str]] = None,
    model_version: str = "heuristic-v1",
    source_ref: Optional[str] = None,
    adverse_action: bool = False,
    policy_clause: Optional[str] = None,
    product: str = "claims-workflow-v2-poc",
) -> dict:
    row = {
        "id": str(uuid.uuid4()),
        "product": product,
        "domain": domain,
        "claim_id": claim_id,
        "question": question,
        "recommendation": recommendation,
        "reasoning": reasoning,
        "confidence": confidence,
        "alternatives": alternatives or [],
        "risks": risks or [],
        "model_version": model_version,
        "source_ref": source_ref,
        "adverse_action": adverse_action,
        "policy_clause": policy_clause,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with _ledger_lock:
        _LEDGER_ROWS.append(row)
    return row


def get_ledger_rows(claim_id: Optional[str] = None) -> List[dict]:
    with _ledger_lock:
        rows = list(_LEDGER_ROWS)
    if claim_id is None:
        return rows
    return [r for r in rows if r["claim_id"] == claim_id]


def get_policy_coverage(policy_id: str, loss_type: str) -> dict:
    policy = MOCK_POLICIES.get(policy_id)
    if not policy:
        return {"found": False, "covered": False, "limit": None, "clause": NO_POLICY_CLAUSE}
    covered = loss_type in policy["covered_loss_types"]
    if not covered:
        return {"found": True, "covered": False, "limit": None, "clause": WRONG_LOSS_TYPE_CLAUSE}
    return {"found": True, "covered": True, "limit": policy["limit"], "clause": policy["clause"]}


def create_payment(claim_id: str, amount: float, idempotency_key: str) -> dict:
    """Returns {"record": {...4 fields...}, "idempotent": bool}. The record
    itself never carries the idempotent flag — a replayed and a first-time
    settlement for the same key are byte-for-byte the same record, which is
    the whole point of idempotency (a caller comparing the two shouldn't be
    able to tell which call created it vs. replayed it)."""
    with _payment_lock:
        cached = _SETTLEMENTS.get(idempotency_key)
        if cached:
            return {"record": cached, "idempotent": True}
        record = {
            "idempotency_key": idempotency_key,
            "claim_id": claim_id,
            "amount": amount,
            "settled_at": datetime.now(timezone.utc).isoformat(),
        }
        _SETTLEMENTS[idempotency_key] = record
        return {"record": record, "idempotent": False}


def reset_all_for_tests() -> None:
    with _ledger_lock:
        _LEDGER_ROWS.clear()
    with _payment_lock:
        _SETTLEMENTS.clear()
