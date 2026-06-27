"""Intake agent unit tests."""

from claims_rag.agents.intake_agent import extract_claim_fixture, intake_needs_human_review, run_intake
from claims_rag.models import ClaimData


def test_extract_claim_fixture_parses_policy_and_amount() -> None:
    raw = "Policy POL-1001. Alex Rivera. Windshield crack $450 on 2026-06-20."
    data = extract_claim_fixture(raw)
    assert data["policy_number"] == "POL-1001"
    assert data["claimed_amount"] == 450.0
    assert data["extraction_confidence"] >= 0.75


def test_intake_low_confidence_missing_policy() -> None:
    raw = "I had damage last week, no policy number."
    data = extract_claim_fixture(raw)
    claim = ClaimData.model_validate(data)
    assert intake_needs_human_review(claim) is True


def test_run_intake_returns_claim_data() -> None:
    raw = "Policy POL-1001. Alex Rivera. Glass $450 on 2026-06-20."
    claim, backend = run_intake(raw, trace_id="test-intake")
    assert claim.policy_number == "POL-1001"
    assert backend in {"fixture", "anthropic"}
