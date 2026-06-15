from __future__ import annotations

import logging

from agents.prompts import TECH_SYSTEM
from services.llm import chat_json

logger = logging.getLogger(__name__)


def run(user_request: str, product: dict, request_id: str = "") -> tuple[dict, str]:
    prompt = f"""User request:
{user_request}

Product plan:
{product}

Propose a practical MVP architecture aligned with XingAI patterns (FastAPI + SQLite + OpenAI)."""

    result = chat_json(TECH_SYSTEM, prompt, request_id=request_id)
    if result:
        logger.debug("[%s] Tech Agent: OpenAI result received", request_id)
        return result, "openai"

    logger.info("[%s] Tech Agent: using fallback (OpenAI unavailable)", request_id)
    return fallback(), "fallback"


def fallback() -> dict:
    return {
        "frontend": "Simple HTML demo page served by FastAPI",
        "backend": "Python FastAPI orchestrator with specialist agent modules",
        "database": "SQLite for trace logs and research cache",
        "api": "POST /demo/run, GET /demo/trace/{request_id}",
        "agent_flow": "Orchestrator → Research → Product → Tech → Critic → Final answer",
        "deployment": "Local uvicorn for demo; later Fly.io or internal k8s",
    }
