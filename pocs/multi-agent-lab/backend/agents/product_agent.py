from __future__ import annotations

import logging

from agents.prompts import PRODUCT_SYSTEM
from services.llm import chat_json

logger = logging.getLogger(__name__)


def run(user_request: str, research: dict, request_id: str = "") -> tuple[dict, str]:
    prompt = f"""User request:
{user_request}

Research insight:
{research}

Propose a product concept and MVP feature list."""

    result = chat_json(PRODUCT_SYSTEM, prompt, request_id=request_id)
    if result:
        logger.debug("[%s] Product Agent: OpenAI result received", request_id)
        return result, "openai"

    logger.info("[%s] Product Agent: using fallback (OpenAI unavailable)", request_id)
    return fallback(), "fallback"


def fallback() -> dict:
    return {
        "product_name": "XingAI Agent Lab",
        "target_user": "Product and engineering teams evaluating AI agent architecture",
        "pain_point": "Agent demos feel like magic chatbots with no visible workflow",
        "mvp_features": [
            "Orchestrator-led multi-agent pipeline",
            "Research → Product → Tech → Critic handoffs",
            "SQLite trace timeline for every demo run",
            "One-click team demo with sample prompt",
        ],
        "value_proposition": "Show how specialist agents collaborate to turn ideas into plans.",
    }
