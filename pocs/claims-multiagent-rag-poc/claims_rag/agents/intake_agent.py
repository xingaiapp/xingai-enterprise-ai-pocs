"""
Intake Agent — structured extraction from raw claim text.

No RAG here: extraction only. Low confidence routes to human review.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from claims_rag.agents.prompts import INTAKE_SYSTEM
from claims_rag.config import get_policy_config
from claims_rag.llm.client import structured_output
from claims_rag.models import ClaimData, ClaimType

logger = logging.getLogger(__name__)

_POLICY_RE = re.compile(r"POL-\d{4}", re.IGNORECASE)
_AMOUNT_RE = re.compile(r"\$\s*([\d,]+(?:\.\d{2})?)", re.IGNORECASE)
_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})|(\d{1,2}/\d{1,2}/\d{4})")


def _infer_claim_type(text: str) -> ClaimType:
    lower = text.lower()
    if "glass" in lower or "windshield" in lower:
        return ClaimType.AUTO_GLASS
    if "home" in lower or "basement" in lower or "kitchen fire" in lower:
        return ClaimType.PROPERTY
    if "collision" in lower:
        return ClaimType.AUTO_COLLISION
    return ClaimType.LIABILITY


def _infer_name(text: str) -> str:
    # "Policy POL-1001. Alex Rivera." pattern in golden set
    match = re.search(r"POL-\d{4}\.\s*([A-Za-z][A-Za-z .'-]+?)\.", text)
    if match:
        return match.group(1).strip()
    match = re.search(r"^([A-Za-z][A-Za-z .'-]+),", text)
    if match:
        return match.group(1).strip()
    return "Unknown Claimant"


def extract_claim_fixture(raw_claim_text: str) -> dict[str, Any]:
    """Deterministic parser for demo / CI when no API key."""
    policy_match = _POLICY_RE.search(raw_claim_text)
    policy_number = policy_match.group(0).upper() if policy_match else ""

    amounts = [float(a.replace(",", "")) for a in _AMOUNT_RE.findall(raw_claim_text) if a]
    claimed_amount = max(amounts) if amounts else 0.0

    date_match = _DATE_RE.search(raw_claim_text)
    incident_date = ""
    if date_match:
        incident_date = date_match.group(1) or date_match.group(2) or ""

    claimant_name = _infer_name(raw_claim_text)
    claim_type = _infer_claim_type(raw_claim_text)

    required = 0
    if policy_number:
        required += 1
    if claimant_name != "Unknown Claimant":
        required += 1
    if incident_date:
        required += 1
    if claimed_amount > 0:
        required += 1
    if len(raw_claim_text.strip()) > 20:
        required += 1

    confidence = min(1.0, required / 5.0)
    if not policy_number:
        confidence = min(confidence, 0.4)

    return {
        "claimant_name": claimant_name,
        "policy_number": policy_number,
        "incident_date": incident_date or "unknown",
        "incident_description": raw_claim_text.strip(),
        "claimed_amount": claimed_amount,
        "claim_type": claim_type.value,
        "extraction_confidence": confidence,
    }


def run_intake(raw_claim_text: str, *, trace_id: str = "") -> tuple[ClaimData, str]:
    """Extract ClaimData from raw submission text."""
    claim, backend = structured_output(
        INTAKE_SYSTEM,
        raw_claim_text,
        ClaimData,
        trace_id=trace_id,
    )
    logger.info(
        "intake_complete",
        extra={
            "trace_id": trace_id,
            "backend": backend,
            "policy_number": claim.policy_number,
            "confidence": claim.extraction_confidence,
        },
    )
    return claim, backend


def intake_needs_human_review(claim: ClaimData) -> bool:
    policy = get_policy_config()
    if claim.extraction_confidence < policy.intake.min_extraction_confidence:
        return True
    for field in policy.intake.required_fields:
        if not getattr(claim, field, None):
            return True
        if field == "policy_number" and not _POLICY_RE.match(str(claim.policy_number)):
            return True
    return False
