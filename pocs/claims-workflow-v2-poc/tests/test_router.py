"""Fix 2: Case Resolution Router — every escalation resumes at a specific
stage, never a blind restart from intake, and every route is logged."""
from __future__ import annotations

from datetime import date

from claims_workflow.models import Photo
from claims_workflow.pipeline import resume_claim, submit_claim

from .conftest import make_claim


def _domain_rows(ledger, claim_id, domain):
    return [r for r in ledger.for_claim(claim_id) if r.domain == domain]


def test_missing_docs_resolved_resumes_at_doc_verification_not_intake():
    claim = make_claim(documents=["photos"])  # missing police_report for auto

    claim, ledger = submit_claim(claim)
    assert claim.escalation.reason == "missing_docs"
    assert claim.escalation.stage == "doc_verification"

    claim.documents.append("police_report")  # claimant supplies the missing doc
    claim, ledger = resume_claim(claim, ledger, {"outcome": "resolved"})

    assert claim.status == "paid"
    # Proves resume did NOT restart from intake — exactly one intake row.
    assert len(_domain_rows(ledger, claim.claim_id, "intake")) == 1


def test_fraud_cleared_from_triage_resumes_at_damage_assessment():
    claim = make_claim(prior_claims_count=5)  # triggers triage

    claim, ledger = submit_claim(claim)
    assert claim.escalation.stage == "fraud_triage"

    claim, ledger = resume_claim(claim, ledger, {"outcome": "cleared"})

    # Triage-stage clearance still needs assessment + scoring to run —
    # they hadn't yet when triage raised the flag.
    assert len(_domain_rows(ledger, claim.claim_id, "damage_assessment")) == 1
    assert len(_domain_rows(ledger, claim.claim_id, "fraud_scoring")) == 1
    assert len(_domain_rows(ledger, claim.claim_id, "fraud_triage")) == 1  # not re-run
    assert claim.status == "paid"


def test_fraud_cleared_from_scoring_skips_reassessment():
    claim = make_claim(reported_amount=1000.0, assessed_cost_hint=1000.0, photos=[Photo(url="x.jpg", reused=True)])

    claim, ledger = submit_claim(claim)
    assert claim.escalation.stage == "fraud_scoring"

    claim, ledger = resume_claim(claim, ledger, {"outcome": "cleared"})

    # Scoring-stage clearance already has damage_cost — router jumps
    # straight to Policy Coverage, does not re-run assessment or scoring.
    assert len(_domain_rows(ledger, claim.claim_id, "damage_assessment")) == 1
    assert len(_domain_rows(ledger, claim.claim_id, "fraud_scoring")) == 1
    assert claim.status == "paid"


def test_fraud_confirmed_denies_with_siu_reference_not_a_loop():
    claim = make_claim(prior_claims_count=5)

    claim, ledger = submit_claim(claim)
    claim, ledger = resume_claim(claim, ledger, {"outcome": "confirmed"})

    assert claim.status == "denied"
    rows = [r for r in ledger.for_claim(claim.claim_id) if r.adverse_action]
    assert rows, "expected an adverse-action ledger row"
    assert "SIU" in rows[-1].policy_clause


def test_estimate_dispute_adjusted_resumes_at_approval_skips_coverage_recheck():
    claim = make_claim(reported_amount=16000.0, assessed_cost_hint=16000.0)  # over POL-1001's $15,000 limit

    claim, ledger = submit_claim(claim)
    assert claim.escalation.reason == "estimate_dispute"
    assert claim.escalation.stage == "policy_coverage"

    claim, ledger = resume_claim(claim, ledger, {"outcome": "adjusted", "adjusted_amount": 4000.0})

    assert claim.status == "paid"
    assert claim.approved_amount == 4000.0
    assert claim.settlement["amount"] == 4000.0
    # Adjusted-and-approved skips re-checking coverage — only the original
    # escalating coverage row exists.
    assert len(_domain_rows(ledger, claim.claim_id, "policy_coverage")) == 1


def test_high_value_review_approved_skips_straight_to_payment():
    claim = make_claim(reported_amount=6000.0, assessed_cost_hint=5700.0)  # over $5,000 auto-approve threshold

    claim, ledger = submit_claim(claim)
    assert claim.escalation.reason == "high_value_review"

    claim, ledger = resume_claim(claim, ledger, {"outcome": "approved"})

    assert claim.status == "paid"
    # "skip every agent that already ran and doesn't need to run again" —
    # approval is not re-invoked a second time.
    assert len(_domain_rows(ledger, claim.claim_id, "approval")) == 1


def test_upheld_deny_terminates_without_restarting_pipeline():
    claim = make_claim(documents=["photos"])  # missing_docs escalation

    claim, ledger = submit_claim(claim)
    claim, ledger = resume_claim(claim, ledger, {"outcome": "upheld_deny"})

    assert claim.status == "denied"
    assert len(_domain_rows(ledger, claim.claim_id, "intake")) == 1


def test_unrecognized_outcome_defaults_to_safe_deny_not_silent_restart():
    """The router must never guess its way back to intake for a combination
    it doesn't recognize — see router.SAFE_DEFAULT_TARGET."""
    claim = make_claim(documents=["photos"])

    claim, ledger = submit_claim(claim)
    claim, ledger = resume_claim(claim, ledger, {"outcome": "something_unexpected"})

    assert claim.status == "denied"
    assert len(_domain_rows(ledger, claim.claim_id, "intake")) == 1
