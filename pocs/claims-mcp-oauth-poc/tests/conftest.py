"""Shared test fixtures.

The mock claims/review/idempotency stores in mcp_server.policies and
mcp_server.tools are module-level dicts mutated in place (submit_claim_decision
sets claim["status"] = "adjudicated"). Autouse-reset them before every test so
tests don't leak state into each other through import-time singletons.
"""
from __future__ import annotations

import pytest

from mcp_server import policies, tools


@pytest.fixture(autouse=True)
def reset_mock_state():
    original_statuses = {claim_id: claim["status"] for claim_id, claim in policies.MOCK_CLAIMS.items()}
    yield
    for claim_id, status in original_statuses.items():
        policies.MOCK_CLAIMS[claim_id]["status"] = status
    tools._reviews.clear()
    tools._idempotency_results.clear()
