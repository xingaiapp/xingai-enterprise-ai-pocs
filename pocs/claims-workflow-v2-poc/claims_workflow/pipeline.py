"""Claims Settlement Workflow v2 — orchestrator.

Two entry points instead of one run_claim() loop, because the design this
implements requires a real pause/resume boundary at escalation:

  submit_claim(claim)                -> runs until settlement, denial, or
                                         the first escalation
  resume_claim(claim, ledger, human) -> Case Resolution Router decides
                                         exactly which stage to resume at

This mirrors how the pipeline would actually be called from an API: submit
returns immediately if a human needs to look at the claim, and a separate
call resumes it once they have.
"""
from __future__ import annotations

from typing import Tuple

from .agents.approval import run_approval
from .agents.damage_assessment import run_damage_assessment
from .agents.doc_verification import run_doc_verification
from .agents.fraud_scoring import run_fraud_scoring
from .agents.fraud_triage import run_fraud_triage
from .agents.intake import run_intake
from .agents.payment import run_payment
from .agents.policy_coverage import run_policy_coverage
from .agents.router import resolve_case
from .ledger import DecisionLedger
from .models import Claim


def submit_claim(claim: Claim, ledger: DecisionLedger | None = None) -> Tuple[Claim, DecisionLedger]:
    ledger = ledger or DecisionLedger()

    if run_intake(claim, ledger) == "stop":
        return claim, ledger

    if run_doc_verification(claim, ledger) == "escalate":
        return claim, ledger

    if run_fraud_triage(claim, ledger) == "escalate":
        return claim, ledger

    return _continue_from_triage(claim, ledger)


def resume_claim(claim: Claim, ledger: DecisionLedger, human_decision: dict) -> Tuple[Claim, DecisionLedger]:
    """human_decision example: {"outcome": "cleared"} or
    {"outcome": "adjusted", "adjusted_amount": 4200.0}."""
    if claim.escalation is None:
        raise ValueError(f"claim {claim.claim_id} is not currently escalated")

    target = resolve_case(claim, ledger, human_decision)

    if target == "doc_verification":
        if run_doc_verification(claim, ledger) == "escalate":
            return claim, ledger
        if run_fraud_triage(claim, ledger) == "escalate":
            return claim, ledger
        return _continue_from_triage(claim, ledger)

    if target == "damage_assessment":
        return _continue_from_triage(claim, ledger)

    if target == "policy_coverage":
        return _continue_from_coverage(claim, ledger)

    if target == "approval":
        return _continue_from_approval(claim, ledger)

    if target == "payment":
        run_payment(claim, ledger)
        return claim, ledger

    if target in ("deny_fraud", "deny_upheld"):
        claim.status = "denied"
        ledger.record(
            domain="case_resolution_router",
            question=f"Final disposition for claim {claim.claim_id} after router decision",
            recommendation=f"final:denied ({target})",
            reasoning=[f"terminal route selected by router: {target}"],
            confidence=1.0,
            claim_id=claim.claim_id,
            adverse_action=True,
            policy_clause="SIU Fraud Finding — Claim Referred to Fraud Bureau"
            if target == "deny_fraud"
            else (claim.denial_clause or "Section — Claim Not Payable (Escalation Upheld)"),
        )
        return claim, ledger

    return claim, ledger


def _continue_from_triage(claim: Claim, ledger: DecisionLedger) -> Tuple[Claim, DecisionLedger]:
    run_damage_assessment(claim, ledger)
    if run_fraud_scoring(claim, ledger) == "escalate":
        return claim, ledger
    return _continue_from_coverage(claim, ledger)


def _continue_from_coverage(claim: Claim, ledger: DecisionLedger) -> Tuple[Claim, DecisionLedger]:
    coverage = run_policy_coverage(claim, ledger)
    if coverage in ("escalate", "deny"):
        return claim, ledger
    return _continue_from_approval(claim, ledger)


def _continue_from_approval(claim: Claim, ledger: DecisionLedger) -> Tuple[Claim, DecisionLedger]:
    if run_approval(claim, ledger) == "escalate":
        return claim, ledger
    run_payment(claim, ledger)
    return claim, ledger
