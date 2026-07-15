from __future__ import annotations

from datetime import date

import pytest

from claims_workflow.agents.payment import reset_settlements_for_tests
from claims_workflow.models import Claim, Photo


@pytest.fixture(autouse=True)
def _reset_payment_store():
    """Payment idempotency store is module-level (mirrors a real payments
    table shared across requests) — reset it between tests so cases don't
    leak into each other via a shared claim_id."""
    reset_settlements_for_tests()
    yield
    reset_settlements_for_tests()


def make_claim(**overrides) -> Claim:
    """A baseline claim that clears every stage with no escalation —
    individual tests override specific fields to trigger each scenario."""
    defaults = dict(
        claim_id="CLM-TEST-0001",
        policy_id="POL-1001",  # auto, limit $15,000
        claimant_id="CLAIMANT-1",
        loss_type="auto",
        reported_amount=3000.0,
        loss_date=date(2026, 6, 1),
        policy_start_date=date(2025, 1, 1),  # long tenure — no anomaly
        prior_claims_count=0,  # below velocity threshold
        documents=["police_report", "photos"],
        photos=[Photo(url="https://example.com/p1.jpg", reused=False)],
        assessed_cost_hint=None,  # damage assessment lands close to reported — no anomaly
    )
    defaults.update(overrides)
    return Claim(**defaults)
