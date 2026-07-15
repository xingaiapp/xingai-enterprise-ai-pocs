"""Stage 7 — Approval Agent."""
from __future__ import annotations

from ..ledger import DecisionLedger
from ..models import Claim, Escalation

AUTO_APPROVE_THRESHOLD = 5000.0


def run_approval(claim: Claim, ledger: DecisionLedger) -> str:
    amount = claim.damage_cost if claim.damage_cost is not None else claim.reported_amount

    if amount <= AUTO_APPROVE_THRESHOLD:
        claim.status = "approved"
        claim.approved_amount = amount
        ledger.record(
            domain="approval",
            question=f"Does claim {claim.claim_id} qualify for auto-approval?",
            recommendation="auto_approve",
            reasoning=[f"${amount} within auto-approval threshold ${AUTO_APPROVE_THRESHOLD}"],
            confidence=0.9,
            claim_id=claim.claim_id,
        )
        return "continue"

    claim.status = "escalated"
    claim.escalation = Escalation(
        reason="high_value_review", stage="approval", notes=f"${amount} exceeds auto-approval threshold ${AUTO_APPROVE_THRESHOLD}"
    )
    ledger.record(
        domain="approval",
        question=f"Does claim {claim.claim_id} qualify for auto-approval?",
        recommendation="escalate:high_value_review",
        reasoning=[f"${amount} exceeds auto-approval threshold ${AUTO_APPROVE_THRESHOLD}"],
        confidence=0.85,
        claim_id=claim.claim_id,
    )
    return "escalate"
