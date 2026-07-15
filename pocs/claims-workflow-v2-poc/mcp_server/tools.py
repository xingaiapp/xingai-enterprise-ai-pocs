"""The four MCP tool implementations for the Claims Workflow MCP Server.

Each function is the server-side handler main.py's tools/call dispatch
invokes after auth + scope checks pass.
"""
from __future__ import annotations

from typing import List, Optional

from . import rag, store


def tool_get_policy_coverage(policy_id: str, loss_type: str) -> dict:
    """Scope required: policy.read"""
    return store.get_policy_coverage(policy_id, loss_type)


def tool_search_policy_documents(policy_id: str, query: str, k: int = 3) -> dict:
    """Scope required: policy.read

    Phase 2 addition (ADR-009): retrieves the top-k most relevant policy
    clause chunks for a query (e.g. the claim's loss_description) instead
    of returning a single flat {covered: bool}. Used by Policy Coverage's
    LLM path so a coverage decision — and its adverse-action citation —
    comes from actual clause text.
    """
    return {"chunks": rag.search_policy_documents(policy_id, query, k)}


def tool_record_ledger_decision(
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
) -> dict:
    """Scope required: audit.write"""
    return store.record_ledger_row(
        domain=domain,
        question=question,
        recommendation=recommendation,
        reasoning=reasoning,
        confidence=confidence,
        claim_id=claim_id,
        alternatives=alternatives,
        risks=risks,
        model_version=model_version,
        source_ref=source_ref,
        adverse_action=adverse_action,
        policy_clause=policy_clause,
        product=product,
    )


def tool_get_audit_trail(claim_id: Optional[str] = None) -> dict:
    """Scope required: audit.read"""
    return {"rows": store.get_ledger_rows(claim_id)}


def tool_create_payment(claim_id: str, amount: float, idempotency_key: str) -> dict:
    """Scope required: payments.write"""
    return store.create_payment(claim_id, amount, idempotency_key)
