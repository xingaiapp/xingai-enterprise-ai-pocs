"""Fix 3: Compliance & Audit Trail — every stage writes to the ledger, and
that ledger can produce an adverse-action letter and support fairness
audits (model version pinned per decision)."""
from __future__ import annotations

from claims_workflow.agents.payment import run_payment
from claims_workflow.pipeline import submit_claim

from .conftest import make_claim

EXPECTED_HAPPY_PATH_DOMAINS = {
    "intake",
    "doc_verification",
    "fraud_triage",
    "damage_assessment",
    "fraud_scoring",
    "policy_coverage",
    "approval",
    "payment",
}


def test_every_stage_writes_a_ledger_row_on_the_happy_path():
    claim = make_claim()

    claim, ledger = submit_claim(claim)

    domains = {r.domain for r in ledger.for_claim(claim.claim_id)}
    assert domains == EXPECTED_HAPPY_PATH_DOMAINS


def test_every_row_has_reasoning_and_a_bounded_confidence():
    claim = make_claim()
    claim, ledger = submit_claim(claim)

    for row in ledger.for_claim(claim.claim_id):
        assert row.reasoning, f"{row.domain} row has no reasoning"
        assert 0.0 <= row.confidence <= 1.0
        assert row.model_version


def test_adverse_action_letter_cites_the_specific_policy_clause():
    claim = make_claim(loss_type="property", documents=["photos", "receipts"])  # POL-1001 only covers "auto"

    claim, ledger = submit_claim(claim)

    assert claim.status == "denied"
    letter = ledger.adverse_action_letter(claim.claim_id)
    assert letter is not None
    assert letter["policy_clause"] == claim.denial_clause
    assert letter["claim_id"] == claim.claim_id
    assert letter["explanation"]


def test_no_adverse_action_letter_for_a_paid_claim():
    claim = make_claim()
    claim, ledger = submit_claim(claim)

    assert claim.status == "paid"
    assert ledger.adverse_action_letter(claim.claim_id) is None


def test_fraud_triage_and_scoring_pin_different_model_versions():
    """Fairness/bias audits need to trace a flagged decision back to the
    exact model that produced it — triage and scoring must not share one
    undifferentiated 'the fraud model' version string."""
    claim = make_claim()
    claim, ledger = submit_claim(claim)

    triage_row = next(r for r in ledger.for_claim(claim.claim_id) if r.domain == "fraud_triage")
    scoring_row = next(r for r in ledger.for_claim(claim.claim_id) if r.domain == "fraud_scoring")

    assert triage_row.model_version != scoring_row.model_version
    assert "triage" in triage_row.model_version
    assert "scoring" in scoring_row.model_version


def test_idempotent_payment_replay_is_logged_not_silently_skipped():
    claim = make_claim()
    claim, ledger = submit_claim(claim)
    assert claim.status == "paid"
    first_settlement = dict(claim.settlement)

    # Simulate a retried payment write for the same claim (e.g. a client
    # timeout-and-retry) — must not double-pay, and must say so in the ledger.
    second_record = run_payment(claim, ledger)

    assert second_record == first_settlement
    replay_rows = [r for r in ledger.for_claim(claim.claim_id) if r.recommendation == "idempotent_replay"]
    assert len(replay_rows) == 1
