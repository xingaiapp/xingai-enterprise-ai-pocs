"""
Fraud-Check Agent — deterministic rules first, LLM narrative pass second.

High risk never auto-denies; adjudication escalates instead.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta

from claims_rag.config import get_policy_config
from claims_rag.llm.client import narrative_fraud_flags
from claims_rag.models import ClaimData, FraudAssessment, RetrievalBundle

logger = logging.getLogger(__name__)


def _parse_date(value: str) -> datetime | None:
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _claims_in_last_30_days(claim: ClaimData, bundle: RetrievalBundle) -> int:
    incident = _parse_date(claim.incident_date)
    if incident is None:
        return 0
    window_start = incident - timedelta(days=30)
    count = 0
    for excerpt in bundle.history_excerpts:
        date_match = re.search(r"on (\d{4}-\d{2}-\d{2})", excerpt.text)
        if not date_match:
            continue
        hist_date = _parse_date(date_match.group(1))
        if hist_date and window_start <= hist_date <= incident:
            count += 1
    return count


def _policy_glass_limit(bundle: RetrievalBundle) -> float | None:
    for excerpt in bundle.policy_excerpts:
        match = re.search(r"Glass repair / replacement\s*\|\s*\$([0-9,]+)", excerpt.text)
        if match:
            return float(match.group(1).replace(",", ""))
        match = re.search(r"Comprehensive\s*\|\s*\$([0-9,]+)", excerpt.text)
        if match:
            return float(match.group(1).replace(",", ""))
    return None


def _policy_effective_recent(bundle: RetrievalBundle, claim: ClaimData) -> bool:
    incident = _parse_date(claim.incident_date)
    if incident is None:
        return False
    for excerpt in bundle.policy_excerpts:
        match = re.search(r"Effective:\s*(\d{4}-\d{2}-\d{2})", excerpt.text)
        if not match:
            continue
        effective = _parse_date(match.group(1))
        if effective and (incident - effective).days < get_policy_config().fraud.min_days_since_policy_start:
            return True
    return False


def run_fraud_check(
    claim: ClaimData,
    bundle: RetrievalBundle,
    *,
    trace_id: str = "",
) -> FraudAssessment:
    policy = get_policy_config()
    flags: list[str] = []
    score = 0.0
    reasons: list[str] = []

    recent_claims = _claims_in_last_30_days(claim, bundle)
    if recent_claims >= policy.fraud.max_claims_30_days:
        flags.append("claim_frequency_30_day_exceeded")
        score = max(score, 0.75)
        reasons.append(f"{recent_claims} claims in 30-day window")

    limit = _policy_glass_limit(bundle)
    if limit and claim.claimed_amount > 0:
        ratio = claim.claimed_amount / limit
        if ratio >= policy.fraud.amount_vs_limit_flag_ratio:
            flags.append("amount_near_or_over_policy_limit")
            score = max(score, 0.55)
            reasons.append(f"claimed amount {ratio:.0%} of policy limit")

    if _policy_effective_recent(bundle, claim):
        flags.append("claim_within_new_policy_window")
        score = max(score, 0.6)
        reasons.append("incident within min days since policy start")

    narrative_flags = narrative_fraud_flags(claim.incident_description)
    for nf in narrative_flags:
        flags.append(nf)
        score = max(score, 0.72 if "frequency" in nf else 0.5)
        reasons.append(f"narrative flag: {nf}")

    if "third" in claim.incident_description.lower():
        flags.append("claimant_reports_third_recent_claim")
        score = max(score, 0.78)

    assessment = FraudAssessment(
        risk_score=min(1.0, score),
        flags=sorted(set(flags)),
        reasoning="; ".join(reasons) if reasons else "No fraud indicators from rules or narrative.",
    )
    logger.info(
        "fraud_check_complete",
        extra={"trace_id": trace_id, "risk_score": assessment.risk_score, "flags": assessment.flags},
    )
    return assessment
