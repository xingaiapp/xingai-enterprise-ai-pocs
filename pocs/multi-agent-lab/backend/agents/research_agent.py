from __future__ import annotations

from sqlalchemy.orm import Session

from services.llm import chat_json
from tools.fake_research_tool import fake_research_lookup

SYSTEM = """You are the Research Agent in XingAI Agent Lab.
Find research insight for building a new XingAI product from latest AI ideas.
Return JSON with keys: trend, opportunity, evidence (array), why_it_matters.
Be concise and demo-friendly."""


def run(db: Session, user_request: str, research_seed: dict | None = None) -> tuple[dict, str]:
    seed = research_seed or fake_research_lookup(db, user_request)[0]
    prompt = f"""User request:
{user_request}

Research tool seed data:
{seed}

Enhance this into a clear research insight for the team demo."""

    result = chat_json(SYSTEM, prompt)
    if result:
        return result, "openai + fake_research_tool"

    return {
        "trend": seed.get("trend", "Agentic AI product discovery"),
        "opportunity": seed.get("opportunity", "Visible multi-agent collaboration"),
        "evidence": seed.get("evidence", []),
        "why_it_matters": seed.get("why_it_matters", "Helps teams understand agent workflows"),
    }, "fake_research_tool (fallback)"


def fallback() -> dict:
    return {
        "trend": "Agentic AI workflows",
        "opportunity": "Multi-agent product planning demos",
        "evidence": ["Handoffs pattern", "Trace visibility", "Specialist agents"],
        "why_it_matters": "Teams learn faster when they see orchestration, not just answers.",
    }
