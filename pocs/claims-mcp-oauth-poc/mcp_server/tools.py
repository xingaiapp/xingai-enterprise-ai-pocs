"""The four MCP tool implementations for the Claims MCP OAuth POC.

Two reads (get_claim, get_policy_coverage) and a Review → Adjudicate pair
(review_claim_decision → submit_claim_decision) — the same two-phase shape
xingai-robinhood-mcp uses for review_equity_order → place_equity_order, and
for the same reason: a human (or an automated policy check) must be able to
see and cap exactly what's about to happen *before* it becomes binding, and
the binding step must not be able to change what was reviewed.
"""
from __future__ import annotations

import os
import threading
import time
from typing import Any

from fastapi import HTTPException

from mcp_server.policies import (
    MOCK_POLICIES,
    check_adjudication_policy,
    get_claim_or_404,
    get_policy_or_404,
)

# ---------------------------------------------------------------------------
# Review store (in-memory; production: DB row with SELECT FOR UPDATE)
# ---------------------------------------------------------------------------

_review_lock = threading.Lock()
_reviews: dict[str, dict] = {}   # review_id → review record

_idempotency_lock = threading.Lock()
_idempotency_results: dict[str, dict] = {}   # idempotency_key → adjudication result

REVIEW_TTL_SECONDS = 300   # 5 minutes — long enough for an adjuster to actually read the summary


# ---------------------------------------------------------------------------
# Tool: get_claim
# ---------------------------------------------------------------------------

def tool_get_claim(claim_id: str) -> dict:
    """Scope required: claims.read"""
    claim = get_claim_or_404(claim_id)
    return dict(claim)


# ---------------------------------------------------------------------------
# Tool: get_policy_coverage
# ---------------------------------------------------------------------------

def tool_get_policy_coverage(policy_number: str) -> dict:
    """Scope required: policy.read"""
    policy = get_policy_or_404(policy_number)
    return dict(policy)


# ---------------------------------------------------------------------------
# Tool: review_claim_decision (phase 1: draft, never binding)
# ---------------------------------------------------------------------------

def tool_review_claim_decision(
    claim_id: str,
    decision: str,          # "approve" | "deny" | "partial"
    settlement_amount: float,
    rationale: str,
    user_id: str,
) -> dict:
    """Generate a decision preview and return a review_id (TTL 300s). Does
    NOT touch claim status. Scope required: claims.review

    Key design, mirroring xingai-robinhood-mcp's review_equity_order:
    - claim_id, decision, and settlement_amount are all frozen inside the
      review record the instant it's created.
    - submit_claim_decision (below) accepts only review_id — it cannot
      change the amount, the claim, or the decision type. If the agent
      wants a different settlement, it must create a new review, which
      re-runs the full policy check.
    """
    decision = decision.lower()
    if decision not in ("approve", "deny", "partial"):
        raise HTTPException(status_code=400, detail="decision must be approve, deny, or partial")

    claim = get_claim_or_404(claim_id)

    # deny doesn't touch the settlement cap — $0 is not "under authority",
    # it's "not a payout at all"
    effective_amount = 0.0 if decision == "deny" else settlement_amount
    if decision != "deny":
        check_adjudication_policy(claim, effective_amount)  # wall #2, run at review time

    review_id = f"rev_{os.urandom(12).hex()}"
    review = {
        "review_id": review_id,
        "user_id": user_id,
        "claim_id": claim["claim_id"],
        "decision": decision,
        "settlement_amount": round(effective_amount, 2),
        "rationale": rationale,
        "expires_at": time.time() + REVIEW_TTL_SECONDS,
        "used": False,
        "created_at": time.time(),
    }

    with _review_lock:
        _reviews[review_id] = review

    return {
        "review_id": review_id,
        "summary": (
            f"{decision.upper()} claim {claim['claim_id']} "
            f"({'no payout' if decision == 'deny' else f'${effective_amount:,.2f} settlement'})"
        ),
        "rationale": rationale,
        "expires_in_seconds": REVIEW_TTL_SECONDS,
        "action_required": "A human adjuster must confirm before calling submit_claim_decision",
    }


# ---------------------------------------------------------------------------
# Tool: submit_claim_decision (phase 2: binding, idempotent)
# ---------------------------------------------------------------------------

def tool_submit_claim_decision(review_id: str, idempotency_key: str, user_id: str) -> dict:
    """Finalize a decision using review_id. Scope required: claims.adjudicate

    Security design (same three properties as xingai-robinhood-mcp's
    place_equity_order):
    1. review_id is single-use — a stolen/replayed review_id can finalize
       the same decision at most once.
    2. Same idempotency_key → same cached result — a network retry from the
       calling agent (timeout, dropped connection) can't double-adjudicate
       the same claim.
    3. Accepts no claim/amount/decision fields directly — there is no way to
       call this tool and finalize something that was never reviewed.
    """
    with _idempotency_lock:
        cached = _idempotency_results.get(idempotency_key)
        if cached:
            return {**cached, "idempotent": True}

    with _review_lock:
        review = _reviews.get(review_id)
        if not review:
            raise HTTPException(status_code=400, detail="Invalid review_id")
        if review["used"]:
            raise HTTPException(status_code=409, detail="review_id already used — cannot adjudicate the same decision twice")
        if time.time() > review["expires_at"]:
            raise HTTPException(status_code=400, detail="review_id has expired — create a new review")
        if review["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="review_id does not belong to the current agent session")

        review["used"] = True   # inside the lock — prevents a concurrent replay from both winning

    claim = get_claim_or_404(review["claim_id"])
    # Re-check policy at submit time too, not just at review time — a claim
    # could in principle have been re-routed out of the AI-assist queue by an
    # ops lead in the seconds between review and submit; the binding step
    # must not trust a stale review blindly.
    if review["decision"] != "deny":
        check_adjudication_policy(claim, review["settlement_amount"])

    claim["status"] = "adjudicated"
    decision_id = f"dec_{os.urandom(12).hex()}"

    result = {
        "decision_id": decision_id,
        "review_id": review_id,
        "idempotency_key": idempotency_key,
        "claim_id": review["claim_id"],
        "decision": review["decision"],
        "settlement_amount": review["settlement_amount"],
        "rationale": review["rationale"],
        "status": "finalized",
        "finalized_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "finalized_by": user_id,
    }

    with _idempotency_lock:
        _idempotency_results[idempotency_key] = result

    return result
