"""Review → Adjudicate state machine, idempotency, wall #2 (agent settlement
policy), and OAuth scope enforcement — all against mocked authentication so
each test focuses on one layer of the two-wall model.
"""
import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from mcp_server.main import app

client = TestClient(app)

FULL_SCOPE_CLAIMS = {
    "sub": "demo-adjuster-001",
    "scope": "claims.read policy.read claims.review claims.adjudicate",
    "client_id": "claims-adjuster-assist-client",
    "iss": "http://localhost:8000",
    "aud": "http://localhost:8001/mcp",
}


def _rpc_with_mock_auth(method: str, params: dict, claims: dict = FULL_SCOPE_CLAIMS) -> dict:
    """Patches mcp_server.auth.verify_token (signature/iss/aud verification)
    only — NOT authenticate_request itself. That distinction matters: mocking
    authenticate_request wholesale would also skip its real require_scopes()
    call, which is exactly the enforcement TestScopeEnforcement below needs
    to actually exercise rather than assume away."""
    with patch("mcp_server.auth.verify_token", return_value=claims):
        resp = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            headers={"Authorization": "Bearer mock-token"},
        )
    return resp.json()


def _review(claim_id="CLM-8841", decision="approve", amount=640.00, rationale="Photo evidence confirms damage."):
    return _rpc_with_mock_auth("tools/call", {
        "name": "review_claim_decision",
        "arguments": {"claim_id": claim_id, "decision": decision, "settlement_amount": amount, "rationale": rationale},
    })


def _submit(review_id: str, idempotency_key: str | None = None):
    return _rpc_with_mock_auth("tools/call", {
        "name": "submit_claim_decision",
        "arguments": {"review_id": review_id, "idempotency_key": idempotency_key or f"idem_{os.urandom(4).hex()}"},
    })


class TestReadTools:
    def test_get_claim_returns_claim_fields(self):
        result = _rpc_with_mock_auth("tools/call", {"name": "get_claim", "arguments": {"claim_id": "CLM-8841"}})
        data = result["result"]["_data"]
        assert data["claim_id"] == "CLM-8841"
        assert data["policy_number"] == "POL-1001"

    def test_get_claim_unknown_id_returns_404_shaped_error(self):
        result = _rpc_with_mock_auth("tools/call", {"name": "get_claim", "arguments": {"claim_id": "CLM-0000"}})
        assert "error" in result
        assert result["error"]["code"] == 404

    def test_get_policy_coverage_returns_coverage_terms(self):
        result = _rpc_with_mock_auth("tools/call", {"name": "get_policy_coverage", "arguments": {"policy_number": "POL-1001"}})
        data = result["result"]["_data"]
        assert data["policy_type"] == "auto_comprehensive"
        assert "glass" in data["coverages"]


class TestReviewAdjudicateFlow:
    def test_review_returns_review_id_and_summary(self):
        result = _review()
        assert "error" not in result
        data = result["result"]["_data"]
        assert data["review_id"].startswith("rev_")
        assert "summary" in data

    def test_review_is_single_use(self):
        review = _review()
        review_id = review["result"]["_data"]["review_id"]

        first = _submit(review_id)
        assert "error" not in first
        assert first["result"]["_data"]["status"] == "finalized"

        second = _submit(review_id)
        assert "error" in second
        assert second["error"]["code"] == 409

    def test_idempotent_retry_returns_same_decision_id(self):
        review = _review()
        review_id = review["result"]["_data"]["review_id"]
        idem_key = f"idem_test_{os.urandom(4).hex()}"

        first = _submit(review_id, idem_key)
        decision_id_1 = first["result"]["_data"]["decision_id"]

        second = _submit(review_id, idem_key)
        decision_id_2 = second["result"]["_data"]["decision_id"]

        assert decision_id_1 == decision_id_2, "Idempotency broken: two calls returned different decision_ids"
        assert second["result"]["_data"]["idempotent"] is True

    def test_submit_finalizes_claim_status(self):
        review = _review()
        _submit(review["result"]["_data"]["review_id"])
        claim = _rpc_with_mock_auth("tools/call", {"name": "get_claim", "arguments": {"claim_id": "CLM-8841"}})
        assert claim["result"]["_data"]["status"] == "adjudicated"

    def test_deny_decision_never_checks_settlement_cap(self):
        """A deny is $0 payout — must succeed even though CLM-9010 (used
        here for its non-queue status) is otherwise off-limits... except
        deny still requires the AI-assist-queue check, so use an in-queue
        claim to isolate just the amount-cap behavior."""
        result = _review(claim_id="CLM-8842", decision="deny", amount=999999)
        assert "error" not in result   # amount is ignored/zeroed for deny — no policy_violation


class TestWall2SettlementAuthority:
    """Agent policy — independent of OAuth scope. A caller with a perfectly
    valid claims.review token still gets refused here."""

    def test_claim_outside_ai_assist_queue_is_refused(self):
        result = _review(claim_id="CLM-9010", decision="approve", amount=100.00)
        assert "error" in result
        assert "AI-assist queue" in result["error"]["message"]

    def test_claim_type_outside_allowlist_is_refused(self):
        # CLM-9010 is both out-of-queue AND out-of-allowlist; route it into
        # the queue first to isolate the claim-type check specifically.
        from mcp_server import policies
        policies.MOCK_CLAIMS["CLM-9010"]["status"] = policies.AI_ASSIST_QUEUE_STATUS
        result = _review(claim_id="CLM-9010", decision="approve", amount=100.00)
        assert "error" in result
        assert "settlement authority" in result["error"]["message"]

    def test_settlement_over_authority_cap_is_refused(self):
        result = _review(claim_id="CLM-8842", decision="approve", amount=50_000.00)
        assert "error" in result
        assert "exceeds agent settlement authority" in result["error"]["message"]

    def test_settlement_at_exact_cap_is_allowed(self):
        from mcp_server.policies import MAX_SETTLEMENT_USD
        result = _review(claim_id="CLM-8842", decision="approve", amount=MAX_SETTLEMENT_USD)
        assert "error" not in result

    def test_zero_or_negative_settlement_rejected(self):
        result = _review(claim_id="CLM-8841", decision="approve", amount=0)
        assert "error" in result


class TestScopeEnforcement:
    def test_read_only_scope_cannot_review(self):
        limited = {**FULL_SCOPE_CLAIMS, "scope": "claims.read"}
        result = _rpc_with_mock_auth(
            "tools/call",
            {"name": "review_claim_decision", "arguments": {
                "claim_id": "CLM-8841", "decision": "approve", "settlement_amount": 640.00, "rationale": "x",
            }},
            claims=limited,
        )
        assert "error" in result
        assert result["error"]["code"] == 403

    def test_review_scope_without_adjudicate_scope_cannot_submit(self):
        """The realistic 'assistant that can propose but not finalize'
        deployment — the whole reason claims.review and claims.adjudicate
        are two separate scopes instead of one."""
        review_claims = {**FULL_SCOPE_CLAIMS, "scope": "claims.read claims.review"}
        review = _rpc_with_mock_auth(
            "tools/call",
            {"name": "review_claim_decision", "arguments": {
                "claim_id": "CLM-8841", "decision": "approve", "settlement_amount": 640.00, "rationale": "x",
            }},
            claims=review_claims,
        )
        review_id = review["result"]["_data"]["review_id"]

        submit = _rpc_with_mock_auth(
            "tools/call",
            {"name": "submit_claim_decision", "arguments": {"review_id": review_id, "idempotency_key": "idem_1"}},
            claims=review_claims,   # missing claims.adjudicate
        )
        assert "error" in submit
        assert submit["error"]["code"] == 403
