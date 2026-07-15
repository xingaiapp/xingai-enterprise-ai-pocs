"""Tests for the Phase 2 LLM-path plumbing (dispatch, JSON parsing, and
fallback-to-heuristic-on-error) — all run with ANTHROPIC_API_KEY unset in
this environment, so they monkeypatch llm_client._call_anthropic directly
to inject canned model responses. This is deliberately at the lowest
level (the actual network call) so the test still exercises real parsing,
scope-checking, and ledger-writing code, not a mocked-away shortcut.

Real end-to-end LLM behavior (does the model actually make good fraud/
coverage judgment calls) is out of scope here — that's tests/eval/,
which only runs with a real ANTHROPIC_API_KEY (`pytest -m eval`).
"""
from __future__ import annotations

import json

import pytest

from claims_workflow import llm_client
from claims_workflow.agents.adverse_action_letter import draft_letter
from claims_workflow.agents.fraud_scoring import run_fraud_scoring
from claims_workflow.agents.fraud_triage import run_fraud_triage
from claims_workflow.agents.policy_coverage import run_policy_coverage
from claims_workflow.ledger import DecisionLedger

from .conftest import make_claim


@pytest.fixture
def with_fake_api_key(monkeypatch):
    """Makes llm_client.is_available() return True without touching real
    network — the actual call is monkeypatched separately per test."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-tests")


def _canned(response_dict: dict):
    def _fake_call(system: str, user: str, model: str) -> str:
        return json.dumps(response_dict)
    return _fake_call


def _raising(message: str = "simulated network failure"):
    def _fake_call(system: str, user: str, model: str) -> str:
        raise RuntimeError(message)
    return _fake_call


# ---------------------------------------------------------------------------
# llm_client.complete_json parsing
# ---------------------------------------------------------------------------

def test_complete_json_raises_without_api_key():
    with pytest.raises(llm_client.LLMError):
        llm_client.complete_json("sys", "user")


def test_complete_json_extracts_json_from_prose_wrapper(with_fake_api_key, monkeypatch):
    monkeypatch.setattr(
        llm_client, "_call_anthropic",
        lambda system, user, model: 'Sure, here is the result:\n```json\n{"escalate": true, "signals": ["x"], "confidence": 0.8}\n```',
    )
    result = llm_client.complete_json("sys", "user")
    assert result == {"escalate": True, "signals": ["x"], "confidence": 0.8}


def test_complete_json_raises_on_unparseable_response(with_fake_api_key, monkeypatch):
    monkeypatch.setattr(llm_client, "_call_anthropic", lambda system, user, model: "not json at all")
    with pytest.raises(llm_client.LLMError):
        llm_client.complete_json("sys", "user")


# ---------------------------------------------------------------------------
# Fraud Triage — LLM path
# ---------------------------------------------------------------------------

def test_fraud_triage_llm_escalates_on_narrative_signal(with_fake_api_key, monkeypatch):
    monkeypatch.setattr(
        llm_client, "_call_anthropic",
        _canned({"escalate": True, "signals": ["loss_description is inconsistent with a rear-end collision"], "confidence": 0.82}),
    )
    claim = make_claim(loss_description="I was definitely not speeding, my car spontaneously combusted while parked, twice.")
    ledger = DecisionLedger()

    result = run_fraud_triage(claim, ledger)

    assert result == "escalate"
    row = ledger.for_claim(claim.claim_id)[0]
    assert row.model_version.startswith("fraud-triage-llm-")
    assert row.confidence == 0.82


def test_fraud_triage_llm_passes(with_fake_api_key, monkeypatch):
    monkeypatch.setattr(
        llm_client, "_call_anthropic",
        _canned({"escalate": False, "signals": [], "confidence": 0.7}),
    )
    claim = make_claim()
    ledger = DecisionLedger()

    result = run_fraud_triage(claim, ledger)

    assert result == "continue"
    assert claim.status == "triage_passed"


def test_fraud_triage_falls_back_to_heuristic_on_llm_error(with_fake_api_key, monkeypatch):
    monkeypatch.setattr(llm_client, "_call_anthropic", _raising())
    claim = make_claim(prior_claims_count=5)  # would trip the heuristic
    ledger = DecisionLedger()

    result = run_fraud_triage(claim, ledger)

    assert result == "escalate"
    row = ledger.for_claim(claim.claim_id)[0]
    assert row.model_version == "fraud-triage-heuristic-v1-fallback-after-llm-error"


# ---------------------------------------------------------------------------
# Fraud Scoring — LLM path
# ---------------------------------------------------------------------------

def test_fraud_scoring_llm_escalates(with_fake_api_key, monkeypatch):
    monkeypatch.setattr(
        llm_client, "_call_anthropic",
        _canned({"escalate": True, "signals": ["cost anomaly beyond threshold"], "confidence": 0.9}),
    )
    claim = make_claim(damage_cost=1000.0)
    ledger = DecisionLedger()

    result = run_fraud_scoring(claim, ledger)

    assert result == "escalate"
    assert claim.escalation.stage == "fraud_scoring"


def test_fraud_scoring_falls_back_to_heuristic_on_llm_error(with_fake_api_key, monkeypatch):
    monkeypatch.setattr(llm_client, "_call_anthropic", _raising())
    claim = make_claim(reported_amount=3000.0, damage_cost=1000.0)  # would trip heuristic cost-anomaly
    ledger = DecisionLedger()

    result = run_fraud_scoring(claim, ledger)

    assert result == "escalate"
    row = ledger.for_claim(claim.claim_id)[0]
    assert row.model_version == "fraud-scoring-heuristic-v1-fallback-after-llm-error"


# ---------------------------------------------------------------------------
# Policy Coverage — LLM path (genuine redetermination via retrieved clauses)
# ---------------------------------------------------------------------------

def test_policy_coverage_llm_can_deny_via_exclusion_even_when_flat_dict_says_covered(with_fake_api_key, monkeypatch):
    """The flat MOCK_POLICIES dict would say POL-1001/auto is covered — the
    LLM path is expected to be able to override that via an exclusion
    clause it found in the retrieved text (e.g. racing use), which the
    heuristic path structurally cannot do."""
    monkeypatch.setattr(
        llm_client, "_call_anthropic",
        _canned({
            "covered": False,
            "limit": None,
            "clause_id": "5.1",
            "reasoning": ["loss occurred during a racing event, excluded under clause 5.1"],
            "confidence": 0.88,
        }),
    )
    claim = make_claim(loss_description="Was racing a friend on a closed course when I hit a wall.")
    ledger = DecisionLedger()

    result = run_policy_coverage(claim, ledger)

    assert result == "deny"
    assert claim.status == "denied"
    assert "5.1" in claim.denial_clause
    letter = ledger.adverse_action_letter(claim.claim_id)
    assert letter is not None
    assert "5.1" in letter["policy_clause"]


def test_policy_coverage_llm_confirms_coverage(with_fake_api_key, monkeypatch):
    monkeypatch.setattr(
        llm_client, "_call_anthropic",
        _canned({"covered": True, "limit": 15000.0, "clause_id": "4.2(b)", "reasoning": ["clean collision claim, within limit"], "confidence": 0.9}),
    )
    claim = make_claim()
    ledger = DecisionLedger()

    result = run_policy_coverage(claim, ledger)

    assert result == "continue"
    assert claim.status == "coverage_confirmed"


def test_policy_coverage_falls_back_to_heuristic_on_llm_error(with_fake_api_key, monkeypatch):
    monkeypatch.setattr(llm_client, "_call_anthropic", _raising())
    claim = make_claim(loss_type="property", documents=["photos", "receipts"])  # not covered by POL-1001
    ledger = DecisionLedger()

    result = run_policy_coverage(claim, ledger)

    assert result == "deny"
    row = ledger.for_claim(claim.claim_id)[0]
    assert row.model_version == "policy-coverage-heuristic-v1-fallback-after-llm-error"


# ---------------------------------------------------------------------------
# Adverse-action letter drafting
# ---------------------------------------------------------------------------

def test_adverse_action_letter_uses_llm_when_available(with_fake_api_key, monkeypatch):
    monkeypatch.setattr(
        llm_client, "_call_anthropic",
        lambda system, user, model: "We are unable to approve your claim under Section 2.3. You may appeal this decision.",
    )
    claim = make_claim(loss_type="property", documents=["photos", "receipts"])
    ledger = DecisionLedger()
    run_policy_coverage(claim, ledger)  # heuristic path since is_available() only affects agents that check it — but here we want the letter drafter to see the LLM path
    # Force the letter drafter's own LLM check by re-affirming the fake key is set (fixture already did).

    letter = draft_letter(ledger, claim.claim_id)

    assert letter is not None
    assert letter["drafted_by"].startswith("llm-")
    assert "appeal" in letter["letter_text"].lower()


def test_adverse_action_letter_falls_back_to_template_on_llm_error(with_fake_api_key, monkeypatch):
    monkeypatch.setattr(llm_client, "_call_anthropic", _raising())
    claim = make_claim(loss_type="property", documents=["photos", "receipts"])
    ledger = DecisionLedger()
    run_policy_coverage(claim, ledger)

    letter = draft_letter(ledger, claim.claim_id)

    assert letter is not None
    assert letter["drafted_by"] == "heuristic-template-v1"
    assert claim.claim_id in letter["letter_text"]


def test_adverse_action_letter_none_for_non_denied_claim():
    claim = make_claim()
    ledger = DecisionLedger()
    run_policy_coverage(claim, ledger)  # covered, no denial

    assert draft_letter(ledger, claim.claim_id) is None
