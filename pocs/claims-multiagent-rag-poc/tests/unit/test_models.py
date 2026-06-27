"""Tests for claims_rag.models."""

import json
from pathlib import Path

from claims_rag.config import POC_ROOT
from claims_rag.models import (
    AdjudicationAction,
    ClaimData,
    ClaimType,
    DocumentCitation,
    GoldenClaimExpectation,
)


def test_claim_data_schema() -> None:
    claim = ClaimData(
        claimant_name="Alex Rivera",
        policy_number="POL-1001",
        incident_date="2026-06-20",
        incident_description="Windshield crack from debris",
        claimed_amount=450.0,
        claim_type=ClaimType.AUTO_GLASS,
        extraction_confidence=0.92,
    )
    assert claim.policy_number == "POL-1001"


def test_document_citation_requires_scores() -> None:
    cite = DocumentCitation(
        document_id="POL-1001-auto-comprehensive",
        chunk_id="POL-1001-auto-comprehensive::chunk-0",
        collection="policy_documents",
        text="Glass repair covered up to $1,500",
        similarity_score=0.88,
    )
    assert cite.similarity_score == 0.88


def test_golden_set_loads() -> None:
    path = POC_ROOT / "data" / "golden_claims" / "golden_set.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    assert len(rows) >= 3
    first = GoldenClaimExpectation.model_validate(rows[0])
    assert first.expected_action == AdjudicationAction.APPROVE
