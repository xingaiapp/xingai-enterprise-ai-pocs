"""Stage 2 — Document Verification Agent."""
from __future__ import annotations

from ..ledger import DecisionLedger
from ..models import Claim, Escalation

REQUIRED_DOCS = {
    "auto": ["police_report", "photos"],
    "property": ["photos", "receipts"],
    "default": ["photos"],
}


def run_doc_verification(claim: Claim, ledger: DecisionLedger) -> str:
    required = REQUIRED_DOCS.get(claim.loss_type, REQUIRED_DOCS["default"])
    missing = [d for d in required if d not in claim.documents]

    if missing:
        claim.status = "escalated"
        claim.escalation = Escalation(
            reason="missing_docs", stage="doc_verification", notes=f"missing: {missing}"
        )
        ledger.record(
            domain="doc_verification",
            question=f"Does claim {claim.claim_id} have the documents required for loss_type={claim.loss_type}?",
            recommendation="escalate:missing_docs",
            reasoning=[f"missing required documents: {missing}", f"required={required}"],
            confidence=0.9,
            claim_id=claim.claim_id,
            source_ref=f"claim:{claim.claim_id}",
        )
        return "escalate"

    claim.status = "docs_verified"
    ledger.record(
        domain="doc_verification",
        question=f"Does claim {claim.claim_id} have the documents required for loss_type={claim.loss_type}?",
        recommendation="verified",
        reasoning=[f"all required documents present: {required}"],
        confidence=0.93,
        claim_id=claim.claim_id,
    )
    return "continue"
