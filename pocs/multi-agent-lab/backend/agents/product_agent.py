from __future__ import annotations

from services.llm import chat_json

SYSTEM = """You are the Product Agent in XingAI Agent Lab.
Turn research insight into a product concept for XingAI.
Return JSON with keys: product_name, target_user, pain_point, mvp_features (array), value_proposition."""


def run(user_request: str, research: dict) -> tuple[dict, str]:
    prompt = f"""User request:
{user_request}

Research insight:
{research}

Propose a product concept and MVP feature list."""

    result = chat_json(SYSTEM, prompt)
    if result:
        return result, "openai"

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
    }, "fallback"


def fallback() -> dict:
    return {
        "product_name": "XingAI Agent Lab",
        "target_user": "Enterprise AI teams",
        "pain_point": "Opaque AI answers",
        "mvp_features": ["Orchestrator", "Trace log", "Specialist agents"],
        "value_proposition": "Visible multi-agent collaboration",
    }
