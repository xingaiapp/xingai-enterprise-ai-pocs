"""Stage 5 — Fraud Scoring Agent (Fix 1, half B).

Runs AFTER Damage Assessment specifically so it can use cost-anomaly and
photo-forensics signals that don't exist before that stage. This is the
gate the original single "Fraud Score High?" diamond actually belongs at —
it's the first point in the pipeline with the data that name implies.
"""
from __future__ import annotations

from ..ledger import DecisionLedger
from ..models import Claim, Escalation

COST_ANOMALY_RATIO = 1.3  # reported > assessed * this ratio reads as inflated
ESCALATE_SCORE = 0.5


def run_fraud_scoring(claim: Claim, ledger: DecisionLedger) -> str:
    reasoning = []
    score = 0.0

    if claim.damage_cost and claim.reported_amount > claim.damage_cost * COST_ANOMALY_RATIO:
        pct_over = round((claim.reported_amount / claim.damage_cost - 1) * 100)
        reasoning.append(
            f"cost anomaly: reported ${claim.reported_amount} vs assessed ${claim.damage_cost} ({pct_over}% over)"
        )
        score += 0.5

    if claim.photo_forensics_flag:
        reasoning.append("photo forensics: reused/mismatched image metadata detected")
        score += 0.5

    if score >= ESCALATE_SCORE:
        claim.status = "escalated"
        claim.escalation = Escalation(reason="fraud_investigation", stage="fraud_scoring", notes="; ".join(reasoning))
        ledger.record(
            domain="fraud_scoring",
            question=f"Does claim {claim.claim_id} show post-assessment fraud signals (cost anomaly / photo forensics)?",
            recommendation="escalate:fraud_investigation",
            reasoning=reasoning,
            confidence=round(min(0.6 + score * 0.3, 0.95), 2),
            claim_id=claim.claim_id,
            model_version="fraud-scoring-heuristic-v1",
            source_ref=f"claim:{claim.claim_id}",
        )
        return "escalate"

    claim.status = "fraud_cleared"
    ledger.record(
        domain="fraud_scoring",
        question=f"Does claim {claim.claim_id} show post-assessment fraud signals (cost anomaly / photo forensics)?",
        recommendation="pass",
        reasoning=reasoning or ["no cost-anomaly or photo-forensics signals"],
        confidence=0.6,
        claim_id=claim.claim_id,
        model_version="fraud-scoring-heuristic-v1",
    )
    return "continue"
