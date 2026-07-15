"""FastAPI wrapper around the claims_workflow pipeline.

In-memory claim store, same "runnable but not production" precedent as the
rest of this repo's POCs — see README "Not Production Yet" for the real
gaps (persistence, auth, tenant isolation).
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ..ledger import DecisionLedger
from ..models import Claim, Photo
from ..pipeline import resume_claim, submit_claim

app = FastAPI(
    title="Claims Settlement Workflow v2 (XingAI corrected design)",
    version="0.1.0",
    description="Runnable POC for the fraud-sequencing, escalation-routing, and compliance-audit fixes "
    "described in xingai-enterprise-ai-design/articles/2026-07-14-claims-workflow-redesign-fraud-routing-audit.md",
)

_CLAIMS: Dict[str, Tuple[Claim, DecisionLedger]] = {}


class PhotoIn(BaseModel):
    url: str
    reused: bool = False


class SubmitClaimRequest(BaseModel):
    policy_id: str
    claimant_id: str
    loss_type: str
    reported_amount: float
    loss_date: date
    policy_start_date: date
    prior_claims_count: int = 0
    documents: List[str] = Field(default_factory=list)
    photos: List[PhotoIn] = Field(default_factory=list)
    assessed_cost_hint: Optional[float] = None


class ResolveEscalationRequest(BaseModel):
    outcome: str  # resolved | cleared | confirmed | adjusted | approved | upheld_deny
    adjusted_amount: Optional[float] = None
    documents_added: List[str] = Field(default_factory=list)


class ClaimOut(BaseModel):
    claim_id: str
    status: str
    damage_cost: Optional[float]
    approved_amount: Optional[float]
    denial_clause: Optional[str]
    escalation_reason: Optional[str]
    escalation_stage: Optional[str]
    settlement: Optional[dict]


def _to_out(claim: Claim) -> ClaimOut:
    return ClaimOut(
        claim_id=claim.claim_id,
        status=claim.status,
        damage_cost=claim.damage_cost,
        approved_amount=claim.approved_amount,
        denial_clause=claim.denial_clause,
        escalation_reason=claim.escalation.reason if claim.escalation else None,
        escalation_stage=claim.escalation.stage if claim.escalation else None,
        settlement=claim.settlement,
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/claims/submit", response_model=ClaimOut)
def submit(body: SubmitClaimRequest) -> ClaimOut:
    claim = Claim(
        claim_id=f"CLM-{uuid.uuid4().hex[:8]}",
        policy_id=body.policy_id,
        claimant_id=body.claimant_id,
        loss_type=body.loss_type,
        reported_amount=body.reported_amount,
        loss_date=body.loss_date,
        policy_start_date=body.policy_start_date,
        prior_claims_count=body.prior_claims_count,
        documents=body.documents,
        photos=[Photo(url=p.url, reused=p.reused) for p in body.photos],
        assessed_cost_hint=body.assessed_cost_hint,
    )
    claim, ledger = submit_claim(claim)
    _CLAIMS[claim.claim_id] = (claim, ledger)
    return _to_out(claim)


@app.get("/claims/{claim_id}", response_model=ClaimOut)
def get_claim(claim_id: str) -> ClaimOut:
    if claim_id not in _CLAIMS:
        raise HTTPException(status_code=404, detail="claim not found")
    claim, _ = _CLAIMS[claim_id]
    return _to_out(claim)


@app.post("/claims/{claim_id}/resolve", response_model=ClaimOut)
def resolve(claim_id: str, body: ResolveEscalationRequest) -> ClaimOut:
    if claim_id not in _CLAIMS:
        raise HTTPException(status_code=404, detail="claim not found")
    claim, ledger = _CLAIMS[claim_id]
    if claim.escalation is None:
        raise HTTPException(status_code=409, detail="claim is not currently escalated")

    if body.documents_added:
        claim.documents = list(set(claim.documents) | set(body.documents_added))

    human_decision = {"outcome": body.outcome}
    if body.adjusted_amount is not None:
        human_decision["adjusted_amount"] = body.adjusted_amount

    claim, ledger = resume_claim(claim, ledger, human_decision)
    _CLAIMS[claim_id] = (claim, ledger)
    return _to_out(claim)


@app.get("/claims/{claim_id}/audit")
def audit_trail(claim_id: str) -> List[dict]:
    if claim_id not in _CLAIMS:
        raise HTTPException(status_code=404, detail="claim not found")
    _, ledger = _CLAIMS[claim_id]
    return [
        {
            "id": r.id,
            "domain": r.domain,
            "question": r.question,
            "recommendation": r.recommendation,
            "reasoning": r.reasoning,
            "confidence": r.confidence,
            "model_version": r.model_version,
            "adverse_action": r.adverse_action,
            "policy_clause": r.policy_clause,
            "created_at": r.created_at,
        }
        for r in ledger.for_claim(claim_id)
    ]


@app.get("/claims/{claim_id}/adverse-action-letter")
def adverse_action_letter(claim_id: str) -> dict:
    if claim_id not in _CLAIMS:
        raise HTTPException(status_code=404, detail="claim not found")
    _, ledger = _CLAIMS[claim_id]
    letter = ledger.adverse_action_letter(claim_id)
    if letter is None:
        raise HTTPException(status_code=404, detail="no adverse action recorded for this claim")
    return letter
