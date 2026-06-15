from __future__ import annotations

import logging

from agents.prompts import CRITIC_SYSTEM
from services.llm import chat_json

logger = logging.getLogger(__name__)


def run(user_request: str, product: dict, tech: dict, request_id: str = "") -> tuple[dict, str]:
    prompt = f"""User request:
{user_request}

Product plan:
{product}

Technical architecture:
{tech}

List key risks and mitigations for this POC/demo."""

    result = chat_json(CRITIC_SYSTEM, prompt, request_id=request_id)
    if result:
        logger.debug("[%s] Critic Agent: OpenAI result received", request_id)
        return result, "openai"

    logger.info("[%s] Critic Agent: using fallback (OpenAI unavailable)", request_id)
    return fallback(), "fallback"


def fallback() -> dict:
    return {
        "product_risk": "Demo may feel too synthetic if research tool is obviously fake",
        "tech_risk": "OpenAI latency or rate limits during live demo",
        "data_risk": "Trace logs may contain sensitive user input if reused in production",
        "demo_risk": "Audience may confuse POC with production-ready system",
        "mitigation": [
            "Label fake research tool clearly in trace timeline",
            "Cache repeated demo inputs for faster second run",
            "Show 'Not Production Yet' banner in UI",
            "Use trace log to explain handoffs instead of hidden chain-of-thought",
        ],
    }
