"""Decision Ledger — client-side view onto mcp_server's audit-trail tools.

Per ADR-009 Phase 1, the actual rows now live in mcp_server.store, reached
through record_ledger_decision / get_audit_trail. This class keeps the
exact public API it had in ADR-008 (record / all / for_claim /
adverse_action_letter) so every agent file and every existing test keeps
working unchanged — only the internals changed from "append to a local
list" to "call an MCP tool".
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .mcp_client import get_client


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
    created_at: str  # ISO 8601 string, as returned by the server


def _row_to_record(row: dict) -> DecisionRecord:
    return DecisionRecord(**row)


class DecisionLedger:
    """Thin wrapper — every method is one MCP tool call. No local state."""

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
        row = get_client().call_tool(
            "record_ledger_decision",
            {
                "domain": domain,
                "question": question,
                "recommendation": recommendation,
                "reasoning": reasoning,
                "confidence": confidence,
                "claim_id": claim_id,
                "alternatives": alternatives or [],
                "risks": risks or [],
                "model_version": model_version,
                "source_ref": source_ref,
                "adverse_action": adverse_action,
                "policy_clause": policy_clause,
                "product": product,
            },
        )
        return _row_to_record(row)

    def all(self) -> List[DecisionRecord]:
        result = get_client().call_tool("get_audit_trail", {})
        return [_row_to_record(r) for r in result["rows"]]

    def for_claim(self, claim_id: str) -> List[DecisionRecord]:
        result = get_client().call_tool("get_audit_trail", {"claim_id": claim_id})
        return [_row_to_record(r) for r in result["rows"]]

    def adverse_action_letter(self, claim_id: str) -> Optional[dict]:
        rows = [r for r in self.for_claim(claim_id) if r.adverse_action]
        if not rows:
            return None
        row = rows[-1]
        return {
            "claim_id": claim_id,
            "decided_at": row.created_at,
            "reason": row.recommendation,
            "policy_clause": row.policy_clause,
            "explanation": "; ".join(row.reasoning),
            "model_version": row.model_version,
            "source_decision_id": row.id,
        }
