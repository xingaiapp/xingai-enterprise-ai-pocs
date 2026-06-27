"""Fraud-check agent unit tests."""

from claims_rag.agents.fraud_check_agent import run_fraud_check
from claims_rag.agents.intake_agent import extract_claim_fixture
from claims_rag.agents.retrieval_agent import run_retrieval
from claims_rag.models import ClaimData


def test_fraud_frequency_flag(vector_store_dir) -> None:
    raw = "Policy POL-3003. Sam Chen. Third glass claim in the last month. $920 on 2026-06-22."
    claim = ClaimData.model_validate(extract_claim_fixture(raw))
    bundle = run_retrieval(claim, persist_dir=vector_store_dir)
    assessment = run_fraud_check(claim, bundle)
    assert assessment.risk_score >= 0.7
    assert assessment.flags


def test_fraud_low_risk_clean_claim(vector_store_dir) -> None:
    raw = "Policy POL-1001. Alex Rivera. Windshield $450 on 2026-06-20."
    claim = ClaimData.model_validate(extract_claim_fixture(raw))
    bundle = run_retrieval(claim, persist_dir=vector_store_dir)
    assessment = run_fraud_check(claim, bundle)
    assert assessment.risk_score < 0.7
