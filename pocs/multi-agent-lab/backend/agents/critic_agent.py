from __future__ import annotations

from services.llm import chat_json

SYSTEM = """You are the Critic Agent in XingAI Agent Lab.
Review the product and technical plan for risks.
Return JSON with keys: product_risk, tech_risk, data_risk, demo_risk, mitigation (array)."""


def run(user_request: str, product: dict, tech: dict) -> tuple[dict, str]:
    prompt = f"""User request:
{user_request}

Product plan:
{product}

Technical architecture:
{tech}

List key risks and mitigations for this POC/demo."""

    result = chat_json(SYSTEM, prompt)
    if result:
        return result, "openai"

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
    }, "fallback"


def fallback() -> dict:
    return {
        "product_risk": "Over-scoping beyond demo",
        "tech_risk": "API dependency",
        "data_risk": "Input retention",
        "demo_risk": "Expectation mismatch",
        "mitigation": ["Cache", "Clear labels", "Trace transparency"],
    }
