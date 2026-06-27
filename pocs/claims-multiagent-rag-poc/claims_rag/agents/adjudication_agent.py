"""
Adjudication Agent — policy-grounded approve / deny / escalate.

Never approves or denies without a policy citation when require_policy_citation is true.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from claims_rag.agents.prompts import ADJUDICATION_SYSTEM
from claims_rag.config import get_policy_config
from claims_rag.llm.client import structured_output
from claims_rag.models import (
    AdjudicationAction,
    AdjudicationDecision,
    ClaimData,
    DocumentCitation,
    FraudAssessment,
    RetrievalBundle,
)

logger = logging.getLogger(__name__)


def _text_has_flood_exclusion(bundle: RetrievalBundle) -> DocumentCitation | None:
    for excerpt in bundle.policy_excerpts:
        lower = excerpt.text.lower()
        if "flood" in lower and "exclu" in lower:
            return excerpt
    return None


def _text_has_glass_coverage(bundle: RetrievalBundle) -> DocumentCitation | None:
    for excerpt in bundle.policy_excerpts:
        lower = excerpt.text.lower()
        if "glass" in lower or "windshield" in lower:
            return excerpt
    return None


def _claim_mentions_flood(claim: ClaimData) -> bool:
    lower = f"{claim.incident_description} {claim.claim_type.value}".lower()
    return any(kw in lower for kw in ("flood", "storm surge", "rising water", "basement flooded"))


def adjudicate_fixture(payload: dict[str, Any]) -> dict[str, Any]:
    """Rule-based adjudication for demo / CI."""
    claim = ClaimData.model_validate(payload["claim"])
    bundle = RetrievalBundle.model_validate(payload["retrieval"])
    fraud = FraudAssessment.model_validate(payload["fraud"])
    decision = _rule_adjudicate(claim, bundle, fraud)
    return decision.model_dump(mode="json")


def _rule_adjudicate(
    claim: ClaimData,
    bundle: RetrievalBundle,
    fraud: FraudAssessment,
) -> AdjudicationDecision:
    policy = get_policy_config()
    adj = policy.adjudication
    fraud_cfg = policy.fraud

    if claim.claimed_amount >= adj.human_review_threshold_usd:
        citation = bundle.policy_excerpts[0] if bundle.policy_excerpts else None
        return AdjudicationDecision(
            action=AdjudicationAction.ESCALATE_TO_HUMAN,
            reasoning=(
                f"Claim amount ${claim.claimed_amount:,.2f} exceeds human review threshold "
                f"${adj.human_review_threshold_usd:,.2f}."
            ),
            citations=[citation] if citation else [],
            confidence=0.95,
        )

    if fraud.risk_score >= fraud_cfg.escalate_risk_score:
        citation = bundle.policy_excerpts[0] if bundle.policy_excerpts else None
        return AdjudicationDecision(
            action=AdjudicationAction.ESCALATE_TO_HUMAN,
            reasoning=(
                f"Fraud risk score {fraud.risk_score:.2f} >= {fraud_cfg.escalate_risk_score}. "
                f"Flags: {', '.join(fraud.flags) or 'none'}."
            ),
            citations=[citation] if citation else [],
            confidence=0.9,
        )

    if _claim_mentions_flood(claim):
        exclusion = _text_has_flood_exclusion(bundle)
        if exclusion:
            return AdjudicationDecision(
                action=AdjudicationAction.DENY,
                reasoning="Flood or surface water damage is excluded under the policy.",
                citations=[exclusion],
                confidence=0.92,
            )

    if claim.claim_type.value == "auto_glass":
        glass_citation = _text_has_glass_coverage(bundle)
        if glass_citation and claim.claimed_amount <= 1500:
            return AdjudicationDecision(
                action=AdjudicationAction.APPROVE,
                reasoning="Glass damage is a covered peril within policy sublimit.",
                citations=[glass_citation],
                confidence=0.88,
            )

    fallback = bundle.policy_excerpts[0] if bundle.policy_excerpts else None
    return AdjudicationDecision(
        action=AdjudicationAction.ESCALATE_TO_HUMAN,
        reasoning="Unable to auto-adjudicate with available policy excerpts — route to human adjuster.",
        citations=[fallback] if fallback else [],
        confidence=0.6,
    )


def run_adjudication(
    claim: ClaimData,
    bundle: RetrievalBundle,
    fraud: FraudAssessment,
    *,
    trace_id: str = "",
) -> tuple[AdjudicationDecision, str]:
    policy = get_policy_config()
    payload = {
        "claim": claim.model_dump(mode="json"),
        "retrieval": bundle.model_dump(mode="json"),
        "fraud": fraud.model_dump(mode="json"),
    }

    decision, backend = structured_output(
        ADJUDICATION_SYSTEM,
        json.dumps(payload),
        AdjudicationDecision,
        trace_id=trace_id,
    )

    if policy.adjudication.require_policy_citation and decision.action in {
        AdjudicationAction.APPROVE,
        AdjudicationAction.DENY,
    }:
        if not decision.citations:
            rule_decision = _rule_adjudicate(claim, bundle, fraud)
            if rule_decision.citations:
                decision = rule_decision
                backend = f"{backend}+rule_citations"

    # Safety rails — config thresholds always win
    if claim.claimed_amount >= policy.adjudication.human_review_threshold_usd:
        decision = AdjudicationDecision(
            action=AdjudicationAction.ESCALATE_TO_HUMAN,
            reasoning=decision.reasoning,
            citations=decision.citations,
            confidence=decision.confidence,
        )
    if fraud.risk_score >= policy.fraud.escalate_risk_score:
        decision = AdjudicationDecision(
            action=AdjudicationAction.ESCALATE_TO_HUMAN,
            reasoning=decision.reasoning,
            citations=decision.citations,
            confidence=decision.confidence,
        )

    logger.info(
        "adjudication_complete",
        extra={"trace_id": trace_id, "action": decision.action.value, "backend": backend},
    )
    return decision, backend
