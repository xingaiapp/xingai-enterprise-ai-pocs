"""
Shared domain models for the claims workflow.

Every agent reads/writes slices of ClaimWorkflowState.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class AdjudicationAction(str, Enum):
    APPROVE = "APPROVE"
    DENY = "DENY"
    ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"


class ClaimType(str, Enum):
    AUTO_GLASS = "auto_glass"
    AUTO_COLLISION = "auto_collision"
    PROPERTY = "property"
    LIABILITY = "liability"


class ClaimData(BaseModel):
    """Structured output from Intake Agent."""

    claimant_name: str
    policy_number: str
    incident_date: str
    incident_description: str
    claimed_amount: float
    claim_type: ClaimType
    extraction_confidence: float = Field(ge=0.0, le=1.0)


class DocumentCitation(BaseModel):
    """Every retrieved chunk must carry citation metadata."""

    document_id: str
    chunk_id: str
    collection: str
    text: str
    similarity_score: float = Field(ge=0.0, le=1.0)
    source_path: str = ""


class RetrievalBundle(BaseModel):
    """Output from Retrieval Agent — three separate collections."""

    policy_excerpts: list[DocumentCitation] = Field(default_factory=list)
    history_excerpts: list[DocumentCitation] = Field(default_factory=list)
    regulation_excerpts: list[DocumentCitation] = Field(default_factory=list)


class FraudAssessment(BaseModel):
    risk_score: float = Field(ge=0.0, le=1.0)
    flags: list[str] = Field(default_factory=list)
    reasoning: str = ""


class AdjudicationDecision(BaseModel):
    action: AdjudicationAction
    reasoning: str
    citations: list[DocumentCitation] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class ClaimWorkflowState(BaseModel):
    """
    LangGraph state threaded through all agents.

    trace_id correlates audit + structured logs for one claim run.
    """

    trace_id: str = Field(default_factory=lambda: str(uuid4()))
    raw_claim_text: str = ""
    claim_data: ClaimData | None = None
    retrieval: RetrievalBundle | None = None
    fraud: FraudAssessment | None = None
    decision: AdjudicationDecision | None = None
    errors: list[str] = Field(default_factory=list)
    pipeline_status: Literal["pending", "complete", "escalated", "failed"] = "pending"

    def to_audit_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class GoldenClaimExpectation(BaseModel):
    """Eval fixture: synthetic claim + expected adjudication action."""

    claim_id: str
    raw_claim_text: str
    expected_action: AdjudicationAction
    notes: str = ""
