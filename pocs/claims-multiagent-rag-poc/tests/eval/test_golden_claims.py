"""Golden-set evaluation — reports decision action accuracy."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from claims_rag.graph.supervisor_graph import run_claim_pipeline
from claims_rag.models import AdjudicationAction, GoldenClaimExpectation

GOLDEN_PATH = Path(__file__).resolve().parents[2] / "data" / "golden_claims" / "golden_set.json"


def _load_golden() -> list[GoldenClaimExpectation]:
    raw = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    return [GoldenClaimExpectation.model_validate(item) for item in raw]


@pytest.mark.eval
def test_golden_claims_accuracy(vector_store_dir, audit_db_path, monkeypatch) -> None:
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(vector_store_dir))
    from claims_rag.config import get_env_settings

    get_env_settings.cache_clear()

    golden = _load_golden()
    correct = 0
    failures: list[str] = []

    for case in golden:
        result = run_claim_pipeline(case.raw_claim_text, trace_id=case.claim_id)
        assert result.decision is not None, case.claim_id
        if result.decision.action == case.expected_action:
            correct += 1
        else:
            failures.append(
                f"{case.claim_id}: expected {case.expected_action.value}, "
                f"got {result.decision.action.value}"
            )
        if result.decision.action in {AdjudicationAction.APPROVE, AdjudicationAction.DENY}:
            assert len(result.decision.citations) >= 1, f"{case.claim_id} missing citations"

    accuracy = correct / len(golden)
    print(f"\nGolden-set accuracy: {accuracy:.1%} ({correct}/{len(golden)})")
    if failures:
        print("Failures:\n" + "\n".join(failures))
    assert accuracy >= 0.80, f"Accuracy {accuracy:.1%} below 80% threshold"
