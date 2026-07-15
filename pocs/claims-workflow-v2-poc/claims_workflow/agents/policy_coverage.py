"""Stage 6 — Policy Coverage Agent.

Heuristic path (unchanged from ADR-008): calls the get_policy_coverage MCP
tool, a flat {covered, limit, clause} lookup — it can tell you a loss_type
is nominally covered, but has no way to apply an exclusion clause to this
specific claim's facts.

Per ADR-009 Phase 2, the LLM path is a genuine redetermination, not just
prettier text: it retrieves the actual policy clause chunks (including
exclusions) via search_policy_documents, and reasons over them against the
claim's loss_description — so it can deny a claim the flat dict would call
"covered" if an exclusion clause genuinely applies (e.g. loss_description
mentions racing use against POL-1001's clause 5.1). This can only ever
run when ANTHROPIC_API_KEY is set, so it never executes in the ADR-008
test suite and can't change that suite's behavior — see tests/eval/.
"""
from __future__ import annotations

from .. import llm_client
from ..ledger import DecisionLedger
from ..mcp_client import get_client
from ..models import Claim, Escalation

_SYSTEM_PROMPT = """You are the Policy Coverage agent in an insurance claims pipeline. \
You are given a claim's facts and the most relevant clauses retrieved from the actual \
policy document, including any exclusions. Decide whether this specific claim is \
covered, citing the specific clause_id that supports your decision — including denying \
coverage if an exclusion clause applies even though the loss_type is nominally covered.

Respond with ONLY a JSON object, no other text:
{"covered": <bool>, "limit": <number or null>, "clause_id": <string>, "reasoning": [<string>, ...], "confidence": <number 0-1>}"""


def run_policy_coverage(claim: Claim, ledger: DecisionLedger) -> str:
    if llm_client.is_available():
        try:
            return _run_llm(claim, ledger)
        except llm_client.LLMError:
            return _run_heuristic(claim, ledger, model_suffix="-fallback-after-llm-error")
    return _run_heuristic(claim, ledger)


def _run_heuristic(claim: Claim, ledger: DecisionLedger, model_suffix: str = "") -> str:
    result = get_client().call_tool(
        "get_policy_coverage", {"policy_id": claim.policy_id, "loss_type": claim.loss_type}
    )
    model_version = f"policy-coverage-heuristic-v1{model_suffix}"

    if not result["covered"]:
        clause = result["clause"]
        claim.status = "denied"
        claim.denial_clause = clause
        ledger.record(
            domain="policy_coverage",
            question=f"Is claim {claim.claim_id}'s loss_type={claim.loss_type} covered under policy {claim.policy_id}?",
            recommendation="deny:not_covered",
            reasoning=[
                f"policy {claim.policy_id} {'not found' if not result['found'] else 'does not cover loss_type=' + claim.loss_type}"
            ],
            confidence=0.97,
            claim_id=claim.claim_id,
            adverse_action=True,
            policy_clause=clause,
            model_version=model_version,
        )
        return "deny"

    limit = result["limit"]
    if claim.damage_cost is not None and claim.damage_cost > limit:
        claim.status = "escalated"
        claim.escalation = Escalation(
            reason="estimate_dispute",
            stage="policy_coverage",
            notes=f"assessed ${claim.damage_cost} exceeds policy limit ${limit}",
        )
        ledger.record(
            domain="policy_coverage",
            question=f"Is claim {claim.claim_id}'s assessed cost within policy {claim.policy_id}'s limit?",
            recommendation="escalate:estimate_dispute",
            reasoning=[f"assessed ${claim.damage_cost} > limit ${limit}"],
            confidence=0.85,
            claim_id=claim.claim_id,
            model_version=model_version,
        )
        return "escalate"

    claim.status = "coverage_confirmed"
    claim.coverage_limit = limit
    ledger.record(
        domain="policy_coverage",
        question=f"Is claim {claim.claim_id} covered and within limit under policy {claim.policy_id}?",
        recommendation="covered",
        reasoning=[f"loss_type covered, within limit ${limit}"],
        confidence=0.9,
        claim_id=claim.claim_id,
        model_version=model_version,
    )
    return "continue"


def _run_llm(claim: Claim, ledger: DecisionLedger) -> str:
    query = claim.loss_description or f"{claim.loss_type} loss coverage and exclusions"
    search_result = get_client().call_tool(
        "search_policy_documents", {"policy_id": claim.policy_id, "query": query, "k": 4}
    )
    chunks = search_result["chunks"]
    model_version = f"policy-coverage-llm-{llm_client.DEFAULT_MODEL}"

    if not chunks:
        # No policy document at all — same terminal outcome as "not found"
        # in the heuristic path, no LLM call needed for an empty corpus.
        clause = "Section 1.1 — No Active Policy on File"
        claim.status = "denied"
        claim.denial_clause = clause
        ledger.record(
            domain="policy_coverage",
            question=f"Is claim {claim.claim_id}'s loss_type={claim.loss_type} covered under policy {claim.policy_id}?",
            recommendation="deny:not_covered",
            reasoning=[f"no policy document found for {claim.policy_id}"],
            confidence=0.97,
            claim_id=claim.claim_id,
            adverse_action=True,
            policy_clause=clause,
            model_version=model_version,
        )
        return "deny"

    chunk_text = "\n\n".join(f"[{c['clause_id']}] {c['title']}: {c['text']}" for c in chunks)
    user_prompt = (
        f"claim_id: {claim.claim_id}\n"
        f"policy_id: {claim.policy_id}\n"
        f"loss_type: {claim.loss_type}\n"
        f"reported_amount: {claim.reported_amount}\n"
        f"assessed_damage_cost: {claim.damage_cost}\n"
        f"loss_description: {claim.loss_description or '(none provided)'}\n\n"
        f"Retrieved policy clauses:\n{chunk_text}"
    )
    result = llm_client.complete_json(_SYSTEM_PROMPT, user_prompt)

    covered = bool(result.get("covered", False))
    reasoning = list(result.get("reasoning", []))
    confidence = float(result.get("confidence", 0.7))
    clause_id = result.get("clause_id", chunks[0]["clause_id"])
    clause_title = next((c["title"] for c in chunks if c["clause_id"] == clause_id), chunks[0]["title"])
    clause_text = f"Section {clause_id} — {clause_title}"

    if not covered:
        claim.status = "denied"
        claim.denial_clause = clause_text
        ledger.record(
            domain="policy_coverage",
            question=f"Is claim {claim.claim_id}'s loss_type={claim.loss_type} covered under policy {claim.policy_id}?",
            recommendation="deny:not_covered",
            reasoning=reasoning or [f"LLM determined clause {clause_id} excludes this claim"],
            confidence=round(confidence, 2),
            claim_id=claim.claim_id,
            adverse_action=True,
            policy_clause=clause_text,
            model_version=model_version,
            source_ref=f"policy_doc:{claim.policy_id}:{clause_id}",
        )
        return "deny"

    limit = result.get("limit")
    if limit is not None and claim.damage_cost is not None and claim.damage_cost > float(limit):
        claim.status = "escalated"
        claim.escalation = Escalation(
            reason="estimate_dispute",
            stage="policy_coverage",
            notes=f"assessed ${claim.damage_cost} exceeds policy limit ${limit}",
        )
        ledger.record(
            domain="policy_coverage",
            question=f"Is claim {claim.claim_id}'s assessed cost within policy {claim.policy_id}'s limit?",
            recommendation="escalate:estimate_dispute",
            reasoning=reasoning or [f"assessed ${claim.damage_cost} > limit ${limit}"],
            confidence=round(confidence, 2),
            claim_id=claim.claim_id,
            model_version=model_version,
        )
        return "escalate"

    claim.status = "coverage_confirmed"
    claim.coverage_limit = limit
    ledger.record(
        domain="policy_coverage",
        question=f"Is claim {claim.claim_id} covered and within limit under policy {claim.policy_id}?",
        recommendation="covered",
        reasoning=reasoning or [f"clause {clause_id} supports coverage"],
        confidence=round(confidence, 2),
        claim_id=claim.claim_id,
        model_version=model_version,
        source_ref=f"policy_doc:{claim.policy_id}:{clause_id}",
    )
    return "continue"
