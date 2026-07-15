"""Stage 4 — Damage Assessment Agent.

Produces the two inputs Fraud Scoring needs that Fraud Triage never had:
an independent cost estimate and a photo-forensics flag. In this POC the
cost estimate is a deterministic mock (real deployment: computer-vision /
adjuster tooling) so tests can construct exact cost-anomaly scenarios via
Claim.assessed_cost_hint.
"""
from __future__ import annotations

from ..ledger import DecisionLedger
from ..models import Claim

_DEFAULT_ASSESSMENT_RATIO = 0.95  # no hint => assessed cost close to reported, no anomaly


def run_damage_assessment(claim: Claim, ledger: DecisionLedger) -> str:
    if claim.assessed_cost_hint is not None:
        assessed = claim.assessed_cost_hint
    else:
        assessed = round(claim.reported_amount * _DEFAULT_ASSESSMENT_RATIO, 2)

    claim.damage_cost = round(assessed, 2)
    claim.photo_forensics_flag = any(p.reused for p in claim.photos)
    claim.status = "damage_assessed"

    ledger.record(
        domain="damage_assessment",
        question=f"What is the independently-assessed damage cost for claim {claim.claim_id}?",
        recommendation=f"assessed_cost=${claim.damage_cost}",
        reasoning=[
            f"{len(claim.photos)} photo(s) reviewed",
            f"photo_forensics_flag={claim.photo_forensics_flag}",
            f"reported_amount=${claim.reported_amount}",
        ],
        confidence=0.8,
        claim_id=claim.claim_id,
    )
    return "continue"
