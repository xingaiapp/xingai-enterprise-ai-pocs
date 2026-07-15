"""Stage 5 — Fraud Scoring Agent (Fix 1, half B).

Runs AFTER Damage Assessment specifically so it can use cost-anomaly and
photo-forensics signals that don't exist before that stage. Per ADR-009
Phase 2, the LLM path additionally reasons over the free-text
loss_description alongside the numeric damage_cost/reported_amount
comparison — a narrative inconsistency (e.g. loss_description describing
a fender-bender while damage_cost implies major structural damage) is
something no threshold rule can catch. Heuristic path is unchanged from
ADR-008 and is what runs whenever ANTHROPIC_API_KEY is unset.
"""
from __future__ import annotations

from .. import llm_client
from ..ledger import DecisionLedger
from ..models import Claim, Escalation

COST_ANOMALY_RATIO = 1.3  # reported > assessed * this ratio reads as inflated
ESCALATE_SCORE = 0.5

_SYSTEM_PROMPT = """You are the Fraud Scoring agent in an insurance claims pipeline. \
You run AFTER damage assessment, so you have an independently-assessed damage cost, \
a photo-forensics flag, and the claimant's free-text loss description. Decide whether \
this claim should be escalated to a human for fraud investigation, weighing cost \
anomalies, photo forensics, and any inconsistency between the loss description and the \
assessed facts.

Respond with ONLY a JSON object, no other text:
{"escalate": <bool>, "signals": [<string>, ...], "confidence": <number 0-1>}"""


def run_fraud_scoring(claim: Claim, ledger: DecisionLedger) -> str:
    if llm_client.is_available():
        try:
            return _run_llm(claim, ledger)
        except llm_client.LLMError:
            return _run_heuristic(claim, ledger, model_suffix="-fallback-after-llm-error")
    return _run_heuristic(claim, ledger)


def _heuristic_signals(claim: Claim) -> tuple[list[str], float]:
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
    return reasoning, score


def _run_heuristic(claim: Claim, ledger: DecisionLedger, model_suffix: str = "") -> str:
    reasoning, score = _heuristic_signals(claim)
    model_version = f"fraud-scoring-heuristic-v1{model_suffix}"

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
            model_version=model_version,
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
        model_version=model_version,
    )
    return "continue"


def _run_llm(claim: Claim, ledger: DecisionLedger) -> str:
    user_prompt = (
        f"claim_id: {claim.claim_id}\n"
        f"loss_type: {claim.loss_type}\n"
        f"reported_amount: {claim.reported_amount}\n"
        f"assessed_damage_cost: {claim.damage_cost}\n"
        f"photo_forensics_flag: {claim.photo_forensics_flag}\n"
        f"photo_count: {len(claim.photos)}\n"
        f"loss_description: {claim.loss_description or '(none provided)'}"
    )
    result = llm_client.complete_json(_SYSTEM_PROMPT, user_prompt)

    escalate = bool(result.get("escalate", False))
    signals = list(result.get("signals", []))
    confidence = float(result.get("confidence", 0.6))
    model_version = f"fraud-scoring-llm-{llm_client.DEFAULT_MODEL}"

    if escalate:
        claim.status = "escalated"
        claim.escalation = Escalation(reason="fraud_investigation", stage="fraud_scoring", notes="; ".join(signals) or "LLM escalation, no signals listed")
        ledger.record(
            domain="fraud_scoring",
            question=f"Does claim {claim.claim_id} show post-assessment fraud signals (cost anomaly / photo forensics)?",
            recommendation="escalate:fraud_investigation",
            reasoning=signals or ["LLM flagged for escalation without listing specific signals"],
            confidence=round(confidence, 2),
            claim_id=claim.claim_id,
            model_version=model_version,
            source_ref=f"claim:{claim.claim_id}",
        )
        return "escalate"

    claim.status = "fraud_cleared"
    ledger.record(
        domain="fraud_scoring",
        question=f"Does claim {claim.claim_id} show post-assessment fraud signals (cost anomaly / photo forensics)?",
        recommendation="pass",
        reasoning=signals or ["no post-assessment fraud signals identified"],
        confidence=round(confidence, 2),
        claim_id=claim.claim_id,
        model_version=model_version,
    )
    return "continue"
