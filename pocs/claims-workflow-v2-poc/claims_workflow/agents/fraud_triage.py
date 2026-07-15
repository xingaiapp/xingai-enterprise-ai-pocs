"""Stage 3 — Fraud Triage Agent (Fix 1, half A).

Runs BEFORE Damage Assessment, on purpose. It only has access to signals
that don't need a damage estimate or photos: claim velocity, policy
tenure, and (Phase 2) the claimant's free-text loss description. It
deliberately cannot see cost-inflation or photo-forensics fraud — that's
Fraud Scoring's job, downstream, once that data exists. See
test_fraud_sequencing.py for the assertion that damage assessment has NOT
run by the time this agent makes its call.

Per ADR-009 Phase 2: the LLM path (_run_llm) reasons over the free-text
loss_description in addition to the numeric signals — something the
heuristic path (_run_heuristic) structurally cannot do. The heuristic
path is unchanged from ADR-008 and is what runs whenever
ANTHROPIC_API_KEY is unset, which is why the full pytest suite stays
green with zero API keys — see tests/eval/ for the LLM-path tests.
"""
from __future__ import annotations

from .. import llm_client
from ..ledger import DecisionLedger
from ..models import Claim, Escalation

VELOCITY_THRESHOLD = 3  # prior claims count that reads as suspicious
TENURE_DAYS_THRESHOLD = 14  # loss reported this soon after policy start reads as suspicious
ESCALATE_SCORE = 0.5

_SYSTEM_PROMPT = """You are the Fraud Triage agent in an insurance claims pipeline. \
You run BEFORE damage assessment — you do not have a damage cost estimate or photos, \
and must not assume anything about them. You only see: claim velocity, policy tenure, \
and the claimant's free-text loss description. Decide whether this claim should be \
escalated to a human for fraud investigation.

Respond with ONLY a JSON object, no other text:
{"escalate": <bool>, "signals": [<string>, ...], "confidence": <number 0-1>}"""


def run_fraud_triage(claim: Claim, ledger: DecisionLedger) -> str:
    if llm_client.is_available():
        try:
            return _run_llm(claim, ledger)
        except llm_client.LLMError:
            return _run_heuristic(claim, ledger, model_suffix="-fallback-after-llm-error")
    return _run_heuristic(claim, ledger)


def _heuristic_signals(claim: Claim) -> tuple[list[str], float]:
    signals = []
    score = 0.0
    if claim.prior_claims_count >= VELOCITY_THRESHOLD:
        signals.append(f"velocity: {claim.prior_claims_count} prior claims (threshold {VELOCITY_THRESHOLD})")
        score += 0.5
    tenure_days = (claim.loss_date - claim.policy_start_date).days
    if tenure_days < TENURE_DAYS_THRESHOLD:
        signals.append(f"tenure anomaly: loss reported {tenure_days}d after policy start (threshold {TENURE_DAYS_THRESHOLD}d)")
        score += 0.5
    return signals, score


def _run_heuristic(claim: Claim, ledger: DecisionLedger, model_suffix: str = "") -> str:
    signals, score = _heuristic_signals(claim)
    model_version = f"fraud-triage-heuristic-v1{model_suffix}"

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
            model_version=model_version,
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
        model_version=model_version,
    )
    return "continue"


def _run_llm(claim: Claim, ledger: DecisionLedger) -> str:
    tenure_days = (claim.loss_date - claim.policy_start_date).days
    user_prompt = (
        f"claim_id: {claim.claim_id}\n"
        f"loss_type: {claim.loss_type}\n"
        f"reported_amount: {claim.reported_amount}\n"
        f"prior_claims_count: {claim.prior_claims_count}\n"
        f"policy_tenure_days: {tenure_days}\n"
        f"loss_description: {claim.loss_description or '(none provided)'}"
    )
    result = llm_client.complete_json(_SYSTEM_PROMPT, user_prompt)

    escalate = bool(result.get("escalate", False))
    signals = list(result.get("signals", []))
    confidence = float(result.get("confidence", 0.6))
    model_version = f"fraud-triage-llm-{llm_client.DEFAULT_MODEL}"

    if escalate:
        claim.status = "escalated"
        claim.escalation = Escalation(reason="fraud_investigation", stage="fraud_triage", notes="; ".join(signals) or "LLM escalation, no signals listed")
        ledger.record(
            domain="fraud_triage",
            question=f"Does claim {claim.claim_id} show early (pre-damage-assessment) fraud signals?",
            recommendation="escalate:fraud_investigation",
            reasoning=signals or ["LLM flagged for escalation without listing specific signals"],
            confidence=round(confidence, 2),
            claim_id=claim.claim_id,
            model_version=model_version,
            source_ref=f"claim:{claim.claim_id}",
        )
        return "escalate"

    claim.status = "triage_passed"
    ledger.record(
        domain="fraud_triage",
        question=f"Does claim {claim.claim_id} show early (pre-damage-assessment) fraud signals?",
        recommendation="pass",
        reasoning=signals or ["no early fraud signals identified"],
        confidence=round(confidence, 2),
        claim_id=claim.claim_id,
        model_version=model_version,
    )
    return "continue"
