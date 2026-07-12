"""Wall #2: claims-adjuster-assist agent policy — independent of OAuth scope.

Mirrors a real insurance concept: **settlement authority**. A junior (Level 1)
adjuster is authorized to settle small, low-complexity claims without
escalation; anything larger or more complex requires a senior adjuster or
committee. This module encodes exactly that limit for the *agent*, treating
it like the most junior possible adjuster on the team — narrow claim-type
allowlist, low dollar cap, and restricted to claims an ops lead has
explicitly routed into the "AI-assist queue" (see AI_ASSIST_QUEUE_STATUS
below — the claims-domain equivalent of Robinhood's isolated, separately
funded "Agentic account": the agent can only act on a firewalled subset of
claims, never the whole book).

Passing the OAuth `claims.adjudicate` scope check in auth.py proves the
*agent* is allowed to call the adjudicate tool at all. It says nothing about
*this specific claim*. That's exactly why this check exists as a second,
independent wall — see docs/mcp-auth-deep-dive.md §"Scope is not policy".
"""
from __future__ import annotations

from fastapi import HTTPException

# ---------------------------------------------------------------------------
# Agent policy configuration
# Production: load from a policy-admin system per agent deployment / branch
# office, not hardcoded — see README.md "Not Production Yet".
# ---------------------------------------------------------------------------

# Claim types the agent may adjudicate without human escalation. Narrow and
# low-complexity on purpose — mirrors a real "straight-through processing"
# allowlist insurers use for fast-track claims.
ALLOWED_CLAIM_TYPES = {
    "auto_glass",
    "auto_comprehensive_small",
    "homeowners_water_damage_small",
}

# Maximum settlement amount (USD) the agent may finalize per claim — the
# agent's settlement authority limit, same concept as a Level 1 adjuster's
# dollar cap in a real authority matrix.
MAX_SETTLEMENT_USD = 2_500.0

# Only claims an ops lead has explicitly routed here are eligible for
# agent adjudication at all — even a small, allowed-type, under-cap claim is
# refused if it isn't in this queue. This is the isolation boundary: it
# firewalls the agent's write access to a deliberately small, reviewable
# subset of the full claims book.
AI_ASSIST_QUEUE_STATUS = "ai-assist-queue"

# ---------------------------------------------------------------------------
# Mock claims data (synthetic — mirrors the sibling claims-multiagent-rag-poc's
# policy numbers POL-1001/2002/3003 for narrative continuity across POCs in
# this repo; no real claimant or policy data)
# ---------------------------------------------------------------------------

MOCK_CLAIMS: dict[str, dict] = {
    "CLM-8841": {
        "claim_id": "CLM-8841",
        "policy_number": "POL-1001",
        "claim_type": "auto_glass",
        "claimant_name": "Alex Rivera",
        "loss_description": "Windshield cracked by road debris on I-5",
        "filed_amount": 640.00,
        "status": AI_ASSIST_QUEUE_STATUS,
        "filed_at": "2026-07-08T14:20:00Z",
    },
    "CLM-8842": {
        "claim_id": "CLM-8842",
        "policy_number": "POL-2002",
        "claim_type": "homeowners_water_damage_small",
        "claimant_name": "Jordan Lee",
        "loss_description": "Burst supply line under kitchen sink, minor cabinetry damage",
        "filed_amount": 1_850.00,
        "status": AI_ASSIST_QUEUE_STATUS,
        "filed_at": "2026-07-09T09:05:00Z",
    },
    "CLM-9010": {
        "claim_id": "CLM-9010",
        "policy_number": "POL-3003",
        "claim_type": "auto_comprehensive_total_loss",
        "claimant_name": "Morgan Diaz",
        "loss_description": "Vehicle fire, total loss",
        "filed_amount": 28_500.00,
        # Deliberately NOT in the AI-assist queue: high dollar amount and a
        # claim type outside the allowlist even if it were queued — this
        # claim exists in the fixtures specifically to exercise both refusal
        # paths in tests (see tests/test_claim_flow.py).
        "status": "standard-queue",
        "filed_at": "2026-07-10T11:40:00Z",
    },
}

MOCK_POLICIES: dict[str, dict] = {
    "POL-1001": {
        "policy_number": "POL-1001",
        "policy_type": "auto_comprehensive",
        "state": "CA",
        "coverages": {
            "collision": {"limit": 25_000, "deductible": 500},
            "comprehensive": {"limit": 25_000, "deductible": 250},
            "glass": {"limit": 1_500, "deductible": 0},
        },
    },
    "POL-2002": {
        "policy_number": "POL-2002",
        "policy_type": "homeowners",
        "state": "TX",
        "coverages": {
            "dwelling": {"limit": 350_000, "deductible": 1_000},
            "water_damage": {"limit": 10_000, "deductible": 500},
        },
    },
    "POL-3003": {
        "policy_number": "POL-3003",
        "policy_type": "auto_comprehensive",
        "state": "CA",
        "coverages": {
            "collision": {"limit": 40_000, "deductible": 1_000},
            "comprehensive": {"limit": 40_000, "deductible": 500},
        },
    },
}


def get_claim_or_404(claim_id: str) -> dict:
    claim = MOCK_CLAIMS.get(claim_id.upper())
    if claim is None:
        raise HTTPException(status_code=404, detail=f"No claim found: {claim_id}")
    return claim


def get_policy_or_404(policy_number: str) -> dict:
    policy = MOCK_POLICIES.get(policy_number.upper())
    if policy is None:
        raise HTTPException(status_code=404, detail=f"No policy found: {policy_number}")
    return policy


def check_adjudication_policy(claim: dict, settlement_amount: float) -> None:
    """The second wall. Every one of these checks is independent of what
    OAuth scope the caller presented — a caller with a perfectly valid
    `claims.adjudicate` token still gets refused here if the claim itself is
    out of the agent's authority. Order chosen so the error message tells an
    adjuster the *most specific* reason first."""
    if claim["status"] != AI_ASSIST_QUEUE_STATUS:
        raise HTTPException(
            status_code=403,
            detail=(
                f"policy_violation: claim {claim['claim_id']} is not in the AI-assist queue "
                f"(status={claim['status']!r}) — route it there first if agent adjudication is intended"
            ),
        )

    if claim["claim_type"] not in ALLOWED_CLAIM_TYPES:
        raise HTTPException(
            status_code=403,
            detail=f"policy_violation: claim type {claim['claim_type']!r} is outside agent settlement authority",
        )

    if settlement_amount <= 0:
        raise HTTPException(status_code=400, detail="settlement_amount must be > 0")

    if settlement_amount > MAX_SETTLEMENT_USD:
        raise HTTPException(
            status_code=403,
            detail=(
                f"policy_violation: settlement ${settlement_amount:,.2f} exceeds agent settlement "
                f"authority of ${MAX_SETTLEMENT_USD:,.2f} — escalate to a senior adjuster"
            ),
        )
