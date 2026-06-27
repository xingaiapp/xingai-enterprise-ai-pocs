"""Tests for claims_rag.config."""

from pathlib import Path

from claims_rag.config import POC_ROOT, load_policy_yaml


def test_load_policy_yaml_thresholds() -> None:
    cfg = load_policy_yaml(POC_ROOT / "config" / "claims_policy.yml")
    assert cfg.fraud.escalate_risk_score == 0.70
    assert cfg.adjudication.human_review_threshold_usd == 5000.0
    assert cfg.retrieval.top_k_per_collection == 4


def test_vector_collections_defined() -> None:
    cfg = load_policy_yaml()
    assert "policy_documents" in cfg.vector_store.collections
    assert cfg.vector_store.chunk_size > 0
