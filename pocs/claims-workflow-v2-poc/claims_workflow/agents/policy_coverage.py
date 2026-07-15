"""Stage 6 — Policy Coverage Agent.

Per ADR-009 Phase 1, the policy fixture now lives in mcp_server.store and
is reached via the get_policy_coverage MCP tool instead of a local dict —
this agent no longer knows what MOCK_POLICIES looks like, only what the
tool returns.
"""
from __future__ import annotations

from ..ledger import DecisionLedger
from ..mcp_client import get_client
from ..models import Claim, Escalation


def run_policy_coverage(claim: Claim, ledger: DecisionLedger) -> str:
    result = get_client().call_tool(
        "get_policy_coverage", {"policy_id": claim.policy_id, "loss_type": claim.loss_type}
    )

    if not result["covered"]:
        clause = result["clause"]
        claim.status = "denied"
        claim.denial_clause = clause
        ledger.record(
            domain="policy_coverage",
            question=f"Is claim {claim.claim_id}'s loss_type={claim.loss_type} covered under policy {claim.policy_id}?",
            recommendation="deny:not_covered",
            reasoning=[
                f"policy {claim.policy_id} {'not found' if not result['found'] else 'does not cover loss_type=' + claim.loss_type}"
            ],
            confidence=0.97,
            claim_id=claim.claim_id,
            adverse_action=True,
            policy_clause=clause,
        )
        return "deny"

    limit = result["limit"]
    if claim.damage_cost is not None and claim.damage_cost > limit:
        claim.status = "escalated"
        claim.escalation = Escalation(
            reason="estimate_dispute",
            stage="policy_coverage",
            notes=f"assessed ${claim.damage_cost} exceeds policy limit ${limit}",
        )
        ledger.record(
            domain="policy_coverage",
            question=f"Is claim {claim.claim_id}'s assessed cost within policy {claim.policy_id}'s limit?",
            recommendation="escalate:estimate_dispute",
            reasoning=[f"assessed ${claim.damage_cost} > limit ${limit}"],
            confidence=0.85,
            claim_id=claim.claim_id,
        )
        return "escalate"

    claim.status = "coverage_confirmed"
    claim.coverage_limit = limit
    ledger.record(
        domain="policy_coverage",
        question=f"Is claim {claim.claim_id} covered and within limit under policy {claim.policy_id}?",
        recommendation="covered",
        reasoning=[f"loss_type covered, within limit ${limit}"],
        confidence=0.9,
        claim_id=claim.claim_id,
    )
    return "continue"
