from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from agents.prompts import RESEARCH_SYSTEM
from services.llm import chat_json
from tools.fake_research_tool import fake_research_lookup

logger = logging.getLogger(__name__)


def run(
    db: Session,
    user_request: str,
    research_seed: dict | None = None,
    request_id: str = "",
) -> tuple[dict, str]:
    seed = research_seed or fake_research_lookup(db, user_request)[0]
    prompt = f"""User request:
{user_request}

Research tool seed data:
{seed}

Enhance this into a clear research insight for the team demo."""

    result = chat_json(RESEARCH_SYSTEM, prompt, request_id=request_id)
    if result:
        logger.debug("[%s] Research Agent: OpenAI result received", request_id)
        return result, "openai + fake_research_tool"

    logger.info("[%s] Research Agent: using fallback (OpenAI unavailable)", request_id)
    return fallback(seed), "fake_research_tool (fallback)"


def fallback(seed: dict | None = None) -> dict:
    base = seed or {}
    return {
        "trend": base.get("trend", "Agentic AI product discovery"),
        "opportunity": base.get("opportunity", "Visible multi-agent collaboration"),
        "evidence": base.get("evidence", ["Handoffs pattern", "Trace visibility", "Specialist agents"]),
        "why_it_matters": base.get(
            "why_it_matters",
            "Teams learn faster when they see orchestration, not just answers.",
        ),
    }
