"""
Structured LLM client with fixture fallback when API keys are missing.

Demo must not fail live — rule-based fallbacks keep the pipeline running.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, TypeVar

from pydantic import BaseModel

from claims_rag.config import get_env_settings, get_policy_config

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def _anthropic_available() -> bool:
    env = get_env_settings()
    return bool(env.anthropic_api_key.strip())


def structured_output(
    system: str,
    user: str,
    schema: type[T],
    *,
    trace_id: str = "",
) -> tuple[T, str]:
    """
    Return (parsed_model, backend) where backend is 'anthropic' or 'fixture'.
    """
    if _anthropic_available():
        try:
            return _call_anthropic(system, user, schema, trace_id=trace_id), "anthropic"
        except Exception as exc:
            logger.warning(
                "anthropic_call_failed",
                extra={"trace_id": trace_id, "error": str(exc)},
            )
    return _fixture_for_schema(schema, user), "fixture"


def _call_anthropic(
    system: str,
    user: str,
    schema: type[T],
    *,
    trace_id: str,
) -> T:
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage

    policy = get_policy_config()
    env = get_env_settings()
    llm = ChatAnthropic(
        model=policy.llm.model,
        temperature=policy.llm.temperature,
        max_tokens=policy.llm.max_tokens,
        api_key=env.anthropic_api_key,
    )
    structured = llm.with_structured_output(schema)
    result = structured.invoke(
        [SystemMessage(content=system), HumanMessage(content=user)],
        config={"metadata": {"trace_id": trace_id}},
    )
    if isinstance(result, schema):
        return result
    if isinstance(result, dict):
        return schema.model_validate(result)
    raise ValueError(f"Unexpected LLM response type: {type(result)}")


def _fixture_for_schema(schema: type[T], user: str) -> T:
    name = schema.__name__
    if name == "ClaimData":
        from claims_rag.agents.intake_agent import extract_claim_fixture

        return schema.model_validate(extract_claim_fixture(user))
    if name == "AdjudicationDecision":
        from claims_rag.agents.adjudication_agent import adjudicate_fixture

        payload = json.loads(user) if user.strip().startswith("{") else {"raw": user}
        return schema.model_validate(adjudicate_fixture(payload))
    raise ValueError(f"No fixture for schema {name}")


def narrative_fraud_flags(description: str) -> list[str]:
    """Lightweight LLM substitute — keyword inconsistency checks."""
    flags: list[str] = []
    lower = description.lower()
    if "third" in lower and "claim" in lower:
        flags.append("narrative_reports_high_claim_frequency")
    if re.search(r"\b(staged|fake|not real)\b", lower):
        flags.append("narrative_suspicious_language")
    return flags
