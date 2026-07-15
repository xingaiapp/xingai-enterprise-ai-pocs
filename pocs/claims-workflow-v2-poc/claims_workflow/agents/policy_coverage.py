"""Stage 6 — Policy Coverage Agent."""
from __future__ import annotations

from ..ledger import DecisionLedger
from ..models import Claim, Escalation

# In-memory fixture, same precedent as claims-mcp-oauth-poc's MOCK_CLAIMS.
MOCK_POLICIES = {
    "POL-1001": {"covered_loss_types": ["auto"], "limit": 15000.0, "clause": "Section 4.2(b) — Collision Coverage"},
    "POL-1002": {"covered_loss_types": ["property"], "limit": 8000.0, "clause": "Section 3.1(a) — Dwelling Coverage"},
    "POL-1003": {"covered_loss_types": ["auto", "property"], "limit": 25000.0, "clause": "Section 4.2(b) / 3.1(a) — Combined"},
}
NO_POLICY_CLAUSE = "Section 1.1 — No Active Policy on File"
WRONG_LOSS_TYPE_CLAUSE_TEMPLATE = "Section 2.3 — Loss Type Not Covered Under This Policy"


def run_policy_coverage(claim: Claim, ledger: DecisionLedger) -> str:
    policy = MOCK_POLICIES.get(claim.policy_id)

    if not policy or claim.loss_type not in policy["covered_loss_types"]:
        clause = WRONG_LOSS_TYPE_CLAUSE_TEMPLATE if policy else NO_POLICY_CLAUSE
        claim.status = "denied"
        claim.denial_clause = clause
        ledger.record(
            domain="policy_coverage",
            question=f"Is claim {claim.claim_id}'s loss_type={claim.loss_type} covered under policy {claim.policy_id}?",
            recommendation="deny:not_covered",
            reasoning=[
                f"policy {claim.policy_id} {'not found' if not policy else 'does not cover loss_type=' + claim.loss_type}"
            ],
            confidence=0.97,
            claim_id=claim.claim_id,
            adverse_action=True,
            policy_clause=clause,
        )
        return "deny"

    if claim.damage_cost is not None and claim.damage_cost > policy["limit"]:
        claim.status = "escalated"
        claim.escalation = Escalation(
            reason="estimate_dispute",
            stage="policy_coverage",
            notes=f"assessed ${claim.damage_cost} exceeds policy limit ${policy['limit']}",
        )
        ledger.record(
            domain="policy_coverage",
            question=f"Is claim {claim.claim_id}'s assessed cost within policy {claim.policy_id}'s limit?",
            recommendation="escalate:estimate_dispute",
            reasoning=[f"assessed ${claim.damage_cost} > limit ${policy['limit']}"],
            confidence=0.85,
            claim_id=claim.claim_id,
        )
        return "escalate"

    claim.status = "coverage_confirmed"
    claim.coverage_limit = policy["limit"]
    ledger.record(
        domain="policy_coverage",
        question=f"Is claim {claim.claim_id} covered and within limit under policy {claim.policy_id}?",
        recommendation="covered",
        reasoning=[f"loss_type covered, within limit ${policy['limit']}"],
        confidence=0.9,
        claim_id=claim.claim_id,
    )
    return "continue"
