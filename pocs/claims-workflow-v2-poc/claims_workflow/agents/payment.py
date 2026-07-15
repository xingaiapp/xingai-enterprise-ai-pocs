"""Stage 8 — Payment Processing Agent.

Idempotent by construction, same non-negotiable requirement referenced in
the design article and already enforced in this repo's
claims-partner-api-mcp-poc: a payment write is keyed by an idempotency key
derived from the claim, and replaying it returns the original settlement
instead of paying twice.
"""
from __future__ import annotations

from ..ledger import DecisionLedger
from ..models import Claim

# In-memory idempotency store, module-level so a resumed/retried claim run
# shares it — mirrors the "what actually happened" concern the design
# article calls out. A real deployment persists this in the payments table.
_SETTLEMENTS: dict = {}


def _idempotency_key(claim: Claim) -> str:
    return f"{claim.claim_id}-settlement"


def run_payment(claim: Claim, ledger: DecisionLedger) -> dict:
    key = _idempotency_key(claim)

    if key in _SETTLEMENTS:
        record = _SETTLEMENTS[key]
        claim.status = "paid"
        claim.settlement = record
        ledger.record(
            domain="payment",
            question=f"Has claim {claim.claim_id} already been settled?",
            recommendation="idempotent_replay",
            reasoning=[f"idempotency key {key} already settled at {record['settled_at']} — returning prior result, not paying twice"],
            confidence=1.0,
            claim_id=claim.claim_id,
        )
        return record

    amount = claim.approved_amount if claim.approved_amount is not None else (
        claim.damage_cost if claim.damage_cost is not None else claim.reported_amount
    )
    from datetime import datetime, timezone

    record = {
        "idempotency_key": key,
        "claim_id": claim.claim_id,
        "amount": amount,
        "settled_at": datetime.now(timezone.utc).isoformat(),
    }
    _SETTLEMENTS[key] = record
    claim.status = "paid"
    claim.settlement = record

    ledger.record(
        domain="payment",
        question=f"What amount should be settled for claim {claim.claim_id}?",
        recommendation=f"settled:${amount}",
        reasoning=[f"idempotency key {key} written once", f"amount source={'approved_amount' if claim.approved_amount is not None else 'damage_cost/reported_amount'}"],
        confidence=0.95,
        claim_id=claim.claim_id,
    )
    return record


def reset_settlements_for_tests() -> None:
    """Test-only helper — the module-level store otherwise persists across
    test cases in the same process, same as it would across requests in a
    real (in-memory) deployment."""
    _SETTLEMENTS.clear()
