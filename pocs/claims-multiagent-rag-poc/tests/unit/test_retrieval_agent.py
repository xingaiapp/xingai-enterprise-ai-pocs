"""Retrieval agent unit tests."""

from claims_rag.agents.intake_agent import extract_claim_fixture
from claims_rag.agents.retrieval_agent import build_retrieval_query, run_retrieval
from claims_rag.models import ClaimData


def test_build_retrieval_query_includes_policy() -> None:
    claim = ClaimData.model_validate(extract_claim_fixture("Policy POL-1001 glass $450"))
    query = build_retrieval_query(claim)
    assert "POL-1001" in query


def test_run_retrieval_returns_citations(vector_store_dir) -> None:
    claim = ClaimData.model_validate(
        extract_claim_fixture(
            "Policy POL-1001. Alex Rivera. Windshield glass damage $450 on 2026-06-20."
        )
    )
    bundle = run_retrieval(claim, trace_id="test-retrieval", persist_dir=vector_store_dir)
    assert len(bundle.policy_excerpts) >= 1
    excerpt = bundle.policy_excerpts[0]
    assert excerpt.document_id
    assert excerpt.chunk_id
    assert excerpt.similarity_score > 0


def test_retrieval_flood_policy_chunk(vector_store_dir) -> None:
    claim = ClaimData.model_validate(
        extract_claim_fixture(
            "Policy POL-2002. Jordan Lee. Basement flooded storm surge $3200 on 2026-06-18."
        )
    )
    bundle = run_retrieval(claim, persist_dir=vector_store_dir)
    top_docs = {e.document_id for e in bundle.policy_excerpts}
    assert "POL-2002-homeowners" in top_docs or any("POL-2002" in d for d in top_docs)
