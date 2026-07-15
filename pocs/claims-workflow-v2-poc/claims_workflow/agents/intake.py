"""Stage 1 — Claim Intake Agent."""
from __future__ import annotations

from ..ledger import DecisionLedger
from ..models import Claim

REQUIRED_FIELDS = ("policy_id", "claimant_id", "loss_type")


def run_intake(claim: Claim, ledger: DecisionLedger) -> str:
    missing = [f for f in REQUIRED_FIELDS if not getattr(claim, f)]
    if missing:
        claim.status = "rejected_incomplete"
        ledger.record(
            domain="intake",
            question=f"Is claim {claim.claim_id} complete enough to enter the pipeline?",
            recommendation="reject:incomplete",
            reasoning=[f"missing required fields: {missing}"],
            confidence=0.99,
            claim_id=claim.claim_id,
        )
        return "stop"

    claim.status = "intake_complete"
    ledger.record(
        domain="intake",
        question=f"Is claim {claim.claim_id} complete enough to enter the pipeline?",
        recommendation="accept",
        reasoning=["all required fields present", f"loss_type={claim.loss_type}"],
        confidence=0.95,
        claim_id=claim.claim_id,
    )
    return "continue"
