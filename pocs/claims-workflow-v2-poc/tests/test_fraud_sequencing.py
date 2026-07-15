"""Fix 1: fraud detection split into Triage (pre-damage-assessment) and
Scoring (post-damage-assessment) — each catching signals the other can't."""
from __future__ import annotations

from claims_workflow.agents.fraud_triage import run_fraud_triage
from claims_workflow.ledger import DecisionLedger
from claims_workflow.pipeline import submit_claim

from .conftest import make_claim


def test_triage_catches_velocity_fraud_before_damage_assessment_runs():
    claim = make_claim(prior_claims_count=5)  # >= VELOCITY_THRESHOLD

    claim, ledger = submit_claim(claim)

    assert claim.status == "escalated"
    assert claim.escalation is not None
    assert claim.escalation.reason == "fraud_investigation"
    assert claim.escalation.stage == "fraud_triage"
    # The whole point of Fix 1: triage stopped the claim before damage
    # assessment ever ran, so there's no cost estimate yet.
    assert claim.damage_cost is None
    assert not any(r.domain == "damage_assessment" for r in ledger.all())


def test_triage_catches_tenure_anomaly_before_damage_assessment_runs():
    from datetime import date

    claim = make_claim(policy_start_date=date(2026, 5, 25), loss_date=date(2026, 6, 1))  # 7 days

    claim, ledger = submit_claim(claim)

    assert claim.escalation.stage == "fraud_triage"
    assert claim.damage_cost is None


def test_triage_alone_cannot_see_cost_inflation_fraud():
    """Triage has no damage_cost to compare against — calling it directly
    on a claim engineered for cost-inflation fraud must NOT catch it. This
    is the exact gap the original single "Fraud Detection" step had."""
    claim = make_claim(reported_amount=3000.0, assessed_cost_hint=1000.0, prior_claims_count=0)
    ledger = DecisionLedger()

    result = run_fraud_triage(claim, ledger)

    assert result == "continue"  # triage passes it — it cannot see this yet
    assert claim.damage_cost is None


def test_scoring_catches_cost_inflation_fraud_after_assessment():
    """Same claim as above, run through the full pipeline: triage passes
    it, damage assessment produces the cost estimate, and Fraud Scoring —
    which only exists because Fix 1 split it out — catches the anomaly."""
    claim = make_claim(reported_amount=3000.0, assessed_cost_hint=1000.0, prior_claims_count=0)

    claim, ledger = submit_claim(claim)

    triage_rows = [r for r in ledger.for_claim(claim.claim_id) if r.domain == "fraud_triage"]
    assert triage_rows[0].recommendation == "pass"

    assert claim.status == "escalated"
    assert claim.escalation.reason == "fraud_investigation"
    assert claim.escalation.stage == "fraud_scoring"
    # Proves damage assessment ran before scoring flagged it.
    assert claim.damage_cost == 1000.0


def test_scoring_catches_photo_forensics_after_assessment():
    from claims_workflow.models import Photo

    claim = make_claim(photos=[Photo(url="https://example.com/reused.jpg", reused=True)])

    claim, ledger = submit_claim(claim)

    assert claim.escalation.stage == "fraud_scoring"
    assert claim.photo_forensics_flag is True
    assert claim.damage_cost is not None


def test_clean_claim_passes_both_fraud_stages():
    claim = make_claim()

    claim, ledger = submit_claim(claim)

    domains_passed = {r.domain: r.recommendation for r in ledger.for_claim(claim.claim_id)}
    assert domains_passed["fraud_triage"] == "pass"
    assert domains_passed["fraud_scoring"] == "pass"
    assert claim.status == "paid"
