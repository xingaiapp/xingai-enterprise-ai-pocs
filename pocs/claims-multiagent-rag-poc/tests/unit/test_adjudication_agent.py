"""Adjudication agent unit tests."""

from claims_rag.agents.adjudication_agent import run_adjudication
from claims_rag.agents.fraud_check_agent import run_fraud_check
from claims_rag.agents.intake_agent import extract_claim_fixture
from claims_rag.agents.retrieval_agent import run_retrieval
from claims_rag.models import AdjudicationAction, ClaimData


def test_adjudication_approve_glass(vector_store_dir) -> None:
    raw = "Policy POL-1001. Alex Rivera. Windshield glass $450 on 2026-06-20."
    claim = ClaimData.model_validate(extract_claim_fixture(raw))
    bundle = run_retrieval(claim, persist_dir=vector_store_dir)
    fraud = run_fraud_check(claim, bundle)
    decision, _ = run_adjudication(claim, bundle, fraud)
    assert decision.action == AdjudicationAction.APPROVE
    assert len(decision.citations) >= 1


def test_adjudication_deny_flood(vector_store_dir) -> None:
    raw = "Policy POL-2002. Jordan Lee. Basement flooded storm surge $3200 on 2026-06-18."
    claim = ClaimData.model_validate(extract_claim_fixture(raw))
    bundle = run_retrieval(claim, persist_dir=vector_store_dir)
    fraud = run_fraud_check(claim, bundle)
    decision, _ = run_adjudication(claim, bundle, fraud)
    assert decision.action == AdjudicationAction.DENY
    assert len(decision.citations) >= 1


def test_high_amount_never_auto_approve(vector_store_dir) -> None:
    raw = "Policy POL-2002. Jordan Lee. Kitchen fire damage $18500 on 2026-06-10."
    claim = ClaimData.model_validate(extract_claim_fixture(raw))
    bundle = run_retrieval(claim, persist_dir=vector_store_dir)
    fraud = run_fraud_check(claim, bundle)
    decision, _ = run_adjudication(claim, bundle, fraud)
    assert decision.action == AdjudicationAction.ESCALATE_TO_HUMAN
    assert decision.action != AdjudicationAction.APPROVE
