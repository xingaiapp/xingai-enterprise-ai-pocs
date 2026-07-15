"""Adverse-action letter drafting — part of Fix 3 (Compliance & Audit Trail).

ledger.adverse_action_letter() (unchanged from ADR-008) produces the
structured facts: policy_clause, explanation, model_version. This module's
job is turning those facts into letter prose a claimant can actually read.
Low hallucination risk by construction: the LLM is given only already-
verified structured ledger data, not asked to invent facts — see ADR-009
Phase 2 table.

Heuristic path (template string) is what runs whenever ANTHROPIC_API_KEY
is unset, so /claims/{id}/adverse-action-letter never returns nothing.
"""
from __future__ import annotations

from typing import Optional

from .. import llm_client
from ..ledger import DecisionLedger

_SYSTEM_PROMPT = """You draft adverse-action letters for insurance claim denials. \
You are given the specific policy clause and reasoning that produced the denial. \
Write a short, plain-language letter paragraph (3-5 sentences) explaining the denial \
to the claimant, citing the policy clause by name, and stating their right to appeal. \
Do not invent any facts beyond what is given. Respond with ONLY the letter paragraph, \
no other text, no salutation or signature block."""


def _draft_heuristic(facts: dict) -> str:
    return (
        f"We have reviewed claim {facts['claim_id']} and are unable to approve payment. "
        f"This decision is based on {facts['policy_clause']}. {facts['explanation']}. "
        f"If you believe this decision was made in error, you have the right to request "
        f"a review by contacting our claims department and referencing decision "
        f"{facts['source_decision_id']}."
    )


def _draft_llm(facts: dict) -> str:
    user_prompt = (
        f"claim_id: {facts['claim_id']}\n"
        f"policy_clause: {facts['policy_clause']}\n"
        f"reasoning: {facts['explanation']}\n"
        f"decision_id: {facts['source_decision_id']}"
    )
    return llm_client.complete_text(_SYSTEM_PROMPT, user_prompt)


def draft_letter(ledger: DecisionLedger, claim_id: str) -> Optional[dict]:
    """Returns ledger.adverse_action_letter()'s dict with two fields added:
    letter_text (the drafted prose) and drafted_by (which path produced
    it). Returns None if the claim was never denied, same as the
    underlying ledger method."""
    facts = ledger.adverse_action_letter(claim_id)
    if facts is None:
        return None

    if llm_client.is_available():
        try:
            facts["letter_text"] = _draft_llm(facts)
            facts["drafted_by"] = f"llm-{llm_client.DEFAULT_MODEL}"
            return facts
        except llm_client.LLMError:
            pass

    facts["letter_text"] = _draft_heuristic(facts)
    facts["drafted_by"] = "heuristic-template-v1"
    return facts
