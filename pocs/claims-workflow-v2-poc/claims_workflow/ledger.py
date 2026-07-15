"""Decision Ledger — the Compliance & Audit Trail Agent's backing store (Fix 3).

Same row shape as `xingai-engineering-system/patterns/decision-ledger-schema.md`,
already adopted by several XingAI products (most recently `xingai-learn`
ADR-003) and reused here as the claims-domain compliance backbone: one
immutable row per decision, with `reasoning`, `confidence`, a pointer to the
model/heuristic version that produced it, and — specific to this domain —
an `adverse_action` + `policy_clause` pair so a denial can produce a real
adverse-action letter instead of a generic "claim denied" message.

In-memory only, per POC-STANDARDS.md precedent (see claims-mcp-oauth-poc's
MOCK_CLAIMS): a real deployment persists this table and never lets it be
mutated or deleted, only appended to.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


@dataclass
class DecisionRecord:
    id: str
    product: str
    domain: str
    claim_id: Optional[str]
    question: str
    recommendation: str
    reasoning: List[str]
    confidence: float
    alternatives: List[str]
    risks: List[str]
    model_version: str
    source_ref: Optional[str]
    adverse_action: bool
    policy_clause: Optional[str]
    created_at: datetime


class DecisionLedger:
    """Append-only ledger. One instance per claim in this POC (see
    pipeline.py); a real deployment would key this by product+domain in a
    shared table instead, same as the schema pattern this mirrors."""

    def __init__(self) -> None:
        self._rows: List[DecisionRecord] = []

    def record(
        self,
        *,
        domain: str,
        question: str,
        recommendation: str,
        reasoning: List[str],
        confidence: float,
        claim_id: Optional[str] = None,
        alternatives: Optional[List[str]] = None,
        risks: Optional[List[str]] = None,
        model_version: str = "heuristic-v1",
        source_ref: Optional[str] = None,
        adverse_action: bool = False,
        policy_clause: Optional[str] = None,
        product: str = "claims-workflow-v2-poc",
    ) -> DecisionRecord:
        row = DecisionRecord(
            id=str(uuid.uuid4()),
            product=product,
            domain=domain,
            claim_id=claim_id,
            question=question,
            recommendation=recommendation,
            reasoning=reasoning,
            confidence=confidence,
            alternatives=alternatives or [],
            risks=risks or [],
            model_version=model_version,
            source_ref=source_ref,
            adverse_action=adverse_action,
            policy_clause=policy_clause,
            created_at=datetime.now(timezone.utc),
        )
        self._rows.append(row)
        return row

    def all(self) -> List[DecisionRecord]:
        return list(self._rows)

    def for_claim(self, claim_id: str) -> List[DecisionRecord]:
        return [r for r in self._rows if r.claim_id == claim_id]

    def adverse_action_letter(self, claim_id: str) -> Optional[dict]:
        """Fix 3's concrete deliverable: draft an adverse-action letter from
        the specific ledger row that produced the denial, citing the exact
        policy clause — not a generic 'claim denied' message."""
        rows = [r for r in self.for_claim(claim_id) if r.adverse_action]
        if not rows:
            return None
        row = rows[-1]
        return {
            "claim_id": claim_id,
            "decided_at": row.created_at.isoformat(),
            "reason": row.recommendation,
            "policy_clause": row.policy_clause,
            "explanation": "; ".join(row.reasoning),
            "model_version": row.model_version,
            "source_decision_id": row.id,
        }
