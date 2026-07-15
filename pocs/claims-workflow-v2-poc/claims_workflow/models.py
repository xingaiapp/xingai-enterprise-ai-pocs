"""Core data model for the claims workflow POC.

Kept deliberately small and dependency-free (plain dataclasses) so the POC
runs without a database — see README "Not Production Yet" for what a real
deployment would need instead (persistent storage, tenant isolation, etc.).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import List, Optional


@dataclass
class Photo:
    url: str
    # Simulates a photo-forensics finding (reused stock image, stripped/
    # mismatched EXIF, etc.) — Fraud Scoring reads this, Fraud Triage does
    # not (it runs before photos are meaningfully analyzed).
    reused: bool = False


@dataclass
class Escalation:
    """Carries WHY a claim is sitting with a human — the thing the original
    single "Human Review & Escalation" box didn't represent explicitly."""

    reason: str  # missing_docs | fraud_investigation | estimate_dispute | high_value_review
    stage: str  # which agent raised it, e.g. "fraud_triage", "fraud_scoring"
    notes: str


@dataclass
class Claim:
    claim_id: str
    policy_id: str
    claimant_id: str
    loss_type: str
    reported_amount: float
    loss_date: date
    policy_start_date: date
    prior_claims_count: int = 0
    documents: List[str] = field(default_factory=list)
    photos: List[Photo] = field(default_factory=list)

    # Optional test/demo hook: lets a scenario specify what Damage
    # Assessment "finds" independent of what the claimant reported, so
    # cost-inflation fraud can be simulated deterministically. If unset,
    # Damage Assessment estimates close to the reported amount (no anomaly).
    assessed_cost_hint: Optional[float] = None

    # Populated as the claim moves through the pipeline.
    status: str = "submitted"
    damage_cost: Optional[float] = None
    photo_forensics_flag: bool = False
    coverage_limit: Optional[float] = None
    approved_amount: Optional[float] = None
    denial_clause: Optional[str] = None
    escalation: Optional[Escalation] = None
    settlement: Optional[dict] = None

    received_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
