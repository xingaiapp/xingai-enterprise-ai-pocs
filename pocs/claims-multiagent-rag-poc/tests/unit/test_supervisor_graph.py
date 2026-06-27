"""Supervisor graph integration tests."""

from claims_rag.graph.supervisor_graph import run_claim_pipeline
from claims_rag.models import AdjudicationAction


def test_pipeline_demo_approve(vector_store_dir, audit_db_path, monkeypatch) -> None:
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(vector_store_dir))
    from claims_rag.config import get_env_settings

    get_env_settings.cache_clear()

    raw = (
        "Policy POL-1001. Alex Rivera. Date of loss 2026-06-20. "
        "Windshield crack from rock $450 auto glass."
    )
    result = run_claim_pipeline(raw)
    assert result.decision is not None
    assert result.decision.action == AdjudicationAction.APPROVE
    assert len(result.decision.citations) >= 1


def test_pipeline_demo_escalate_amount(vector_store_dir, audit_db_path, monkeypatch) -> None:
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(vector_store_dir))
    from claims_rag.config import get_env_settings

    get_env_settings.cache_clear()

    raw = "Policy POL-2002. Jordan Lee. Kitchen fire smoke damage $18500 on 2026-06-10."
    result = run_claim_pipeline(raw)
    assert result.decision is not None
    assert result.decision.action == AdjudicationAction.ESCALATE_TO_HUMAN
