"""Case Resolution Router — Fix 2.

Replaces a single generic "Human Review & Escalation" loop-back with an
explicit mapping from (escalation reason, escalation stage, human outcome)
to a specific pipeline re-entry point. See the design article's "Fix 2"
section for the full reasoning; the mapping below is that same table, made
concrete and stage-aware now that fraud detection is split into Triage
(pre-assessment) and Scoring (post-assessment) stages.

Every routing decision is logged to the Decision Ledger with the reason it
was chosen — see test_router.py for the assertion that no route is silent.
"""
from __future__ import annotations

from ..ledger import DecisionLedger
from ..models import Claim

# Any (reason, outcome) combination not explicitly handled below falls
# through here — the router never silently restarts a claim from intake
# just because it doesn't recognize a combination.
SAFE_DEFAULT_TARGET = "deny_upheld"


def resolve_case(claim: Claim, ledger: DecisionLedger, human_decision: dict) -> str:
    if claim.escalation is None:
        raise ValueError(f"claim {claim.claim_id} has no active escalation to resolve")

    reason = claim.escalation.reason
    stage = claim.escalation.stage
    outcome = human_decision.get("outcome")

    if reason == "missing_docs" and outcome == "resolved":
        target = "doc_verification"

    elif reason == "fraud_investigation" and outcome == "cleared":
        # Stage-aware re-entry: a Triage clearance still needs Damage
        # Assessment + Fraud Scoring to run (they hadn't yet); a Scoring
        # clearance can skip straight to Policy Coverage since both agents
        # already ran and don't need to run again.
        target = "damage_assessment" if stage == "fraud_triage" else "policy_coverage"

    elif reason == "fraud_investigation" and outcome == "confirmed":
        target = "deny_fraud"

    elif reason == "estimate_dispute" and outcome == "adjusted":
        adjusted = human_decision.get("adjusted_amount")
        if adjusted is not None:
            claim.damage_cost = adjusted
        target = "approval"

    elif reason == "high_value_review" and outcome == "approved":
        target = "payment"

    elif outcome == "upheld_deny":
        target = "deny_upheld"

    else:
        target = SAFE_DEFAULT_TARGET

    ledger.record(
        domain="case_resolution_router",
        question=f"Where should claim {claim.claim_id} resume after escalation '{reason}' at stage '{stage}'?",
        recommendation=f"route:{target}",
        reasoning=[
            f"escalation_reason={reason}",
            f"escalation_stage={stage}",
            f"human_outcome={outcome}",
            f"escalation_notes={claim.escalation.notes}",
        ],
        confidence=1.0,
        alternatives=["restart_from_intake (rejected — discards work already established for this claim)"],
        claim_id=claim.claim_id,
        source_ref=f"escalation:{claim.claim_id}:{stage}",
    )

    claim.escalation = None
    return target
