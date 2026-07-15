"""End-to-end smoke tests: pipeline directly, and through the FastAPI layer."""
from __future__ import annotations

from claims_workflow.pipeline import submit_claim

from .conftest import make_claim


def test_intake_rejects_incomplete_claim():
    claim = make_claim(policy_id="")

    claim, ledger = submit_claim(claim)

    assert claim.status == "rejected_incomplete"
    assert len(ledger.all()) == 1  # pipeline never proceeds past intake


def test_happy_path_reaches_paid_with_full_ledger():
    claim = make_claim()

    claim, ledger = submit_claim(claim)

    assert claim.status == "paid"
    assert claim.settlement is not None
    assert claim.settlement["claim_id"] == claim.claim_id


def test_denied_claim_never_reaches_payment():
    claim = make_claim(loss_type="property", documents=["photos", "receipts"])  # not covered by POL-1001

    claim, ledger = submit_claim(claim)

    assert claim.status == "denied"
    assert claim.settlement is None
    assert not any(r.domain == "payment" for r in ledger.for_claim(claim.claim_id))


class TestApi:
    def setup_method(self):
        from fastapi.testclient import TestClient

        from claims_workflow.api.main import app

        self.client = TestClient(app)

    def _submit_payload(self, **overrides):
        payload = dict(
            policy_id="POL-1001",
            claimant_id="CLAIMANT-1",
            loss_type="auto",
            reported_amount=3000.0,
            loss_date="2026-06-01",
            policy_start_date="2025-01-01",
            prior_claims_count=0,
            documents=["police_report", "photos"],
            photos=[{"url": "https://example.com/p1.jpg", "reused": False}],
        )
        payload.update(overrides)
        return payload

    def test_submit_happy_path_via_api(self):
        resp = self.client.post("/claims/submit", json=self._submit_payload())
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "paid"

        audit = self.client.get(f"/claims/{body['claim_id']}/audit")
        assert audit.status_code == 200
        assert len(audit.json()) >= 8

    def test_submit_and_resolve_missing_docs_via_api(self):
        resp = self.client.post("/claims/submit", json=self._submit_payload(documents=["photos"]))
        body = resp.json()
        assert body["status"] == "escalated"
        assert body["escalation_reason"] == "missing_docs"

        resolve = self.client.post(
            f"/claims/{body['claim_id']}/resolve",
            json={"outcome": "resolved", "documents_added": ["police_report"]},
        )
        assert resolve.status_code == 200
        assert resolve.json()["status"] == "paid"

    def test_adverse_action_letter_endpoint(self):
        resp = self.client.post(
            "/claims/submit", json=self._submit_payload(loss_type="property", documents=["photos", "receipts"])
        )
        body = resp.json()
        assert body["status"] == "denied"

        letter = self.client.get(f"/claims/{body['claim_id']}/adverse-action-letter")
        assert letter.status_code == 200
        assert letter.json()["policy_clause"]
