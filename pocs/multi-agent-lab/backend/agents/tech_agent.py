from __future__ import annotations

from services.llm import chat_json

SYSTEM = """You are the Tech Agent in XingAI Agent Lab.
Design technical architecture for the proposed product.
Return JSON with keys: frontend, backend, database, api, agent_flow, deployment."""


def run(user_request: str, product: dict) -> tuple[dict, str]:
    prompt = f"""User request:
{user_request}

Product plan:
{product}

Propose a practical MVP architecture aligned with XingAI patterns (FastAPI + SQLite + OpenAI)."""

    result = chat_json(SYSTEM, prompt)
    if result:
        return result, "openai"

    return {
        "frontend": "Simple HTML demo page served by FastAPI",
        "backend": "Python FastAPI orchestrator with specialist agent modules",
        "database": "SQLite for trace logs and research cache",
        "api": "POST /demo/run, GET /demo/trace/{request_id}",
        "agent_flow": "Orchestrator → Research → Product → Tech → Critic → Final answer",
        "deployment": "Local uvicorn for demo; later Fly.io or internal k8s",
    }, "fallback"


def fallback() -> dict:
    return {
        "frontend": "HTML demo UI",
        "backend": "FastAPI",
        "database": "SQLite",
        "api": "/demo/run, /demo/trace/{id}",
        "agent_flow": "Orchestrator handoffs",
        "deployment": "uvicorn local",
    }
