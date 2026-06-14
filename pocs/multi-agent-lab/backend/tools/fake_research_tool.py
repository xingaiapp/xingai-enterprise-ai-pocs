from __future__ import annotations

from sqlalchemy.orm import Session

from tools.cache_tool import cache_get, cache_set


def fake_research_lookup(db: Session, topic: str) -> tuple[dict, str]:
    """Simulated research feed — cached by topic hash."""
    cached = cache_get(db, "research", topic)
    if cached:
        return cached, "cache_tool"

    insight = {
        "trend": "Agentic AI workflows for product discovery",
        "opportunity": "Teams need visible multi-agent collaboration, not black-box chat",
        "evidence": [
            "OpenAI Agents SDK documents handoffs and tracing for specialist agents",
            "Enterprise buyers ask how AI decisions are made, not just what answer was returned",
            "XingAI product family already uses orchestrator + specialist agent patterns",
        ],
        "why_it_matters": (
            "A demo that shows orchestrator routing, specialist outputs, and trace logs "
            "helps non-technical stakeholders understand agent systems quickly."
        ),
        "source": "fake_research_tool (simulated research feed for POC demo)",
    }
    cache_set(db, "research", topic, insight)
    return insight, "fake_research_tool"
