"""Claims Settlement Workflow v2 — orchestrator.

Per ADR-009 Phase 3, submit_claim/resume_claim now run a LangGraph
StateGraph (claims_workflow/graph/supervisor_graph.py) instead of the
hand-written _continue_from_triage / _continue_from_coverage /
_continue_from_approval branch-jumping ADR-008 originally shipped — same
agent functions as nodes, same control flow, just expressed as a graph
instead of nested if/return. Two entry points, unchanged from ADR-008:

  submit_claim(claim)                -> runs until settlement, denial, or
                                         the first escalation
  resume_claim(claim, ledger, human) -> Case Resolution Router decides
                                         exactly which stage to resume at
"""
from __future__ import annotations

from typing import Tuple

from .agents.router import resolve_case
from .graph.supervisor_graph import run_from
from .ledger import DecisionLedger
from .models import Claim


def submit_claim(claim: Claim, ledger: DecisionLedger | None = None) -> Tuple[Claim, DecisionLedger]:
    ledger = ledger or DecisionLedger()
    run_from(claim, ledger, "intake")
    return claim, ledger


def resume_claim(claim: Claim, ledger: DecisionLedger, human_decision: dict) -> Tuple[Claim, DecisionLedger]:
    """human_decision example: {"outcome": "cleared"} or
    {"outcome": "adjusted", "adjusted_amount": 4200.0}."""
    if claim.escalation is None:
        raise ValueError(f"claim {claim.claim_id} is not currently escalated")

    target = resolve_case(claim, ledger, human_decision)

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

    run_from(claim, ledger, target)
    return claim, ledger
