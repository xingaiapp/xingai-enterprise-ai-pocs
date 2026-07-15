"""Stage 3 — Fraud Triage Agent (Fix 1, half A).

Runs BEFORE Damage Assessment, on purpose. It only has access to signals
that don't need a damage estimate or photos: claim velocity and policy
tenure. It deliberately cannot see cost-inflation or photo-forensics
fraud — that's Fraud Scoring's job, downstream, once that data exists.
See test_fraud_sequencing.py for the assertion that damage assessment has
NOT run by the time this agent makes its call.
"""
from __future__ import annotations

from ..ledger import DecisionLedger
from ..models import Claim, Escalation

VELOCITY_THRESHOLD = 3  # prior claims count that reads as suspicious
TENURE_DAYS_THRESHOLD = 14  # loss reported this soon after policy start reads as suspicious
ESCALATE_SCORE = 0.5


def run_fraud_triage(claim: Claim, ledger: DecisionLedger) -> str:
    signals = []
    score = 0.0

    if claim.prior_claims_count >= VELOCITY_THRESHOLD:
        signals.append(f"velocity: {claim.prior_claims_count} prior claims (threshold {VELOCITY_THRESHOLD})")
        score += 0.5

    tenure_days = (claim.loss_date - claim.policy_start_date).days
    if tenure_days < TENURE_DAYS_THRESHOLD:
        signals.append(f"tenure anomaly: loss reported {tenure_days}d after policy start (threshold {TENURE_DAYS_THRESHOLD}d)")
        score += 0.5

    if score >= ESCALATE_SCORE:
        claim.status = "escalated"
        claim.escalation = Escalation(reason="fraud_investigation", stage="fraud_triage", notes="; ".join(signals))
        ledger.record(
            domain="fraud_triage",
            question=f"Does claim {claim.claim_id} show early (pre-damage-assessment) fraud signals?",
            recommendation="escalate:fraud_investigation",
            reasoning=signals,
            confidence=round(min(0.6 + score * 0.3, 0.95), 2),
            claim_id=claim.claim_id,
            model_version="fraud-triage-heuristic-v1",
            source_ref=f"claim:{claim.claim_id}",
        )
        return "escalate"

    claim.status = "triage_passed"
    ledger.record(
        domain="fraud_triage",
        question=f"Does claim {claim.claim_id} show early (pre-damage-assessment) fraud signals?",
        recommendation="pass",
        reasoning=["no velocity or tenure anomalies", "cost/photo signals deferred to Fraud Scoring post-assessment"],
        confidence=0.55,
        claim_id=claim.claim_id,
        model_version="fraud-triage-heuristic-v1",
    )
    return "continue"
