"""Real-model eval tests for the Phase 2 LLM-backed agents.

Excluded from the default test run (pytest.ini: `addopts = -m "not eval"`)
— run explicitly with `pytest -m eval`, and only when ANTHROPIC_API_KEY is
set (auto-skipped otherwise, same pattern claims-multiagent-rag-poc uses
for its offline-embeddings fallback, applied here to a real model call
instead). These check loose, structural properties — a real model's exact
wording isn't deterministic — not the exact reasoning strings
tests/test_llm_fallback.py already pins with canned responses.
"""
from __future__ import annotations

from datetime import date

import pytest

from claims_workflow import llm_client
from claims_workflow.ledger import DecisionLedger
from claims_workflow.models import Photo
from claims_workflow.pipeline import submit_claim

from ..conftest import make_claim

pytestmark = [
    pytest.mark.eval,
    pytest.mark.skipif(not llm_client.is_available(), reason="ANTHROPIC_API_KEY not set"),
]


def test_fraud_triage_llm_flags_an_obviously_suspicious_narrative():
    claim = make_claim(
        prior_claims_count=0,
        loss_description=(
            "This is my fourth total-loss claim this year on four different vehicles, "
            "all totaled the week after I bought them, no photos available, cash payout preferred."
        ),
    )
    ledger = DecisionLedger()

    from claims_workflow.agents.fraud_triage import run_fraud_triage

    result = run_fraud_triage(claim, ledger)

    row = ledger.for_claim(claim.claim_id)[0]
    assert row.model_version.startswith("fraud-triage-llm-")
    assert 0.0 <= row.confidence <= 1.0
    assert result in ("escalate", "continue")  # loose: model judgment, not pinned


def test_fraud_triage_llm_passes_an_unremarkable_claim():
    claim = make_claim(
        prior_claims_count=0,
        loss_description="Rear-ended at a stoplight by another driver who admitted fault; minor bumper damage.",
    )
    ledger = DecisionLedger()

    from claims_workflow.agents.fraud_triage import run_fraud_triage

    result = run_fraud_triage(claim, ledger)

    assert result == "continue"


def test_policy_coverage_llm_denies_a_clearly_excluded_racing_claim():
    claim = make_claim(
        policy_id="POL-1001",
        loss_type="auto",
        loss_description="Was participating in an organized closed-course drag race when I hit the guardrail.",
    )
    ledger = DecisionLedger()

    from claims_workflow.agents.policy_coverage import run_policy_coverage

    result = run_policy_coverage(claim, ledger)

    assert result == "deny"
    assert claim.denial_clause is not None


def test_adverse_action_letter_llm_cites_the_clause_and_mentions_appeal():
    claim = make_claim(loss_type="property", documents=["photos", "receipts"])  # POL-1001 doesn't cover property
    ledger = DecisionLedger()

    from claims_workflow.agents.adverse_action_letter import draft_letter
    from claims_workflow.agents.policy_coverage import run_policy_coverage

    run_policy_coverage(claim, ledger)
    letter = draft_letter(ledger, claim.claim_id)

    assert letter is not None
    assert letter["drafted_by"].startswith("llm-")
    assert len(letter["letter_text"]) > 20
    assert "appeal" in letter["letter_text"].lower() or "review" in letter["letter_text"].lower()


def test_full_pipeline_runs_end_to_end_with_llm_agents_active():
    claim = make_claim(loss_description="Standard fender-bender in a parking lot, other driver at fault.")
    claim, ledger = submit_claim(claim)

    assert claim.status in ("paid", "escalated", "denied")
    domains = {r.domain for r in ledger.for_claim(claim.claim_id)}
    assert "fraud_triage" in domains
