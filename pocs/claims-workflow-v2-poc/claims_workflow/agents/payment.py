"""Stage 8 — Payment Processing Agent.

Idempotent by construction, same non-negotiable requirement referenced in
the design article and already enforced in this repo's
claims-partner-api-mcp-poc. Per ADR-009 Phase 1, the settlement store now
lives in mcp_server.store, reached via the create_payment MCP tool.
"""
from __future__ import annotations

from ..ledger import DecisionLedger
from ..mcp_client import get_client
from ..models import Claim


def _idempotency_key(claim: Claim) -> str:
    return f"{claim.claim_id}-settlement"


def run_payment(claim: Claim, ledger: DecisionLedger) -> dict:
    key = _idempotency_key(claim)
    amount = claim.approved_amount if claim.approved_amount is not None else (
        claim.damage_cost if claim.damage_cost is not None else claim.reported_amount
    )

    result = get_client().call_tool(
        "create_payment", {"claim_id": claim.claim_id, "amount": amount, "idempotency_key": key}
    )
    record = result["record"]
    claim.status = "paid"
    claim.settlement = record

    if result["idempotent"]:
        ledger.record(
            domain="payment",
            question=f"Has claim {claim.claim_id} already been settled?",
            recommendation="idempotent_replay",
            reasoning=[f"idempotency key {key} already settled at {record['settled_at']} — returning prior result, not paying twice"],
            confidence=1.0,
            claim_id=claim.claim_id,
        )
    else:
        ledger.record(
            domain="payment",
            question=f"What amount should be settled for claim {claim.claim_id}?",
            recommendation=f"settled:${record['amount']}",
            reasoning=[f"idempotency key {key} written once", f"amount source={'approved_amount' if claim.approved_amount is not None else 'damage_cost/reported_amount'}"],
            confidence=0.95,
            claim_id=claim.claim_id,
        )

    return record


def reset_settlements_for_tests() -> None:
    """Kept for backward compatibility with existing test imports — now
    delegates to mcp_server's store reset instead of clearing a local dict."""
    from mcp_server import store

    store.reset_all_for_tests()
