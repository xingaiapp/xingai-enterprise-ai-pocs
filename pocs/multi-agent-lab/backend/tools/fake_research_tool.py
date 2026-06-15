from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from tools.cache_tool import cache_get, cache_set

logger = logging.getLogger(__name__)

# Topic-aware fixture data — keyed by keyword found in user input.
# Each fixture represents a distinct research scenario for demo variety.
_FIXTURES: dict[str, dict] = {
    "invest": {
        "trend": "AI-powered portfolio analysis and real-time risk scoring",
        "opportunity": "Retail investors lack institutional-grade research tools accessible on mobile",
        "evidence": [
            "Bloomberg reports 65% of retail investors rely on social media for investment signals",
            "Robinhood and Webull have 30M+ users but no AI-driven decision layer",
            "XingAI Invest AI already validates demand for structured AI decision output",
        ],
        "why_it_matters": (
            "An AI agent that explains its reasoning — not just gives a verdict — "
            "builds trust and positions XingAI as the decision layer for retail investors."
        ),
        "source": "fake_research_tool (invest scenario fixture)",
    },
    "meal": {
        "trend": "Personalized nutrition AI driven by dietary goals and food image recognition",
        "opportunity": "Health-conscious users want meal guidance that adapts to real ingredients they have",
        "evidence": [
            "MyFitnessPal has 200M users but no AI meal planning beyond calorie logging",
            "Food image recognition accuracy exceeds 90% with modern vision models",
            "XingAI Meal AI validates demand for structured nutrition + recipe output",
        ],
        "why_it_matters": (
            "Combining image recognition with dietary constraints and local cuisine preferences "
            "creates a personalized coach that generic nutrition apps cannot replicate."
        ),
        "source": "fake_research_tool (meal scenario fixture)",
    },
    "learn": {
        "trend": "Adaptive AI tutoring that adjusts difficulty based on real-time learner response",
        "opportunity": "Online learners drop out at 85%+ rates; personalized pacing reduces churn",
        "evidence": [
            "Duolingo's AI-powered streak and difficulty adjustment drove 45% retention improvement",
            "SAT prep market is $1B+ with no dominant AI-native product",
            "XingAI Learn validates demand for structured study planning with explanation",
        ],
        "why_it_matters": (
            "An agent that identifies weak concepts, generates targeted practice, and explains "
            "mistakes in the learner's language is 10x more useful than static video courses."
        ),
        "source": "fake_research_tool (learn scenario fixture)",
    },
    "enterprise": {
        "trend": "Agentic AI replacing manual knowledge work in finance, legal, and operations",
        "opportunity": "Enterprise teams spend 40% of time on research and synthesis tasks that agents can do",
        "evidence": [
            "McKinsey estimates 70% of knowledge worker tasks are partially automatable by LLMs",
            "OpenAI's enterprise contracts exceeded $1B ARR driven by workflow automation",
            "XingAI multi-agent POC validates orchestrator + specialist handoff architecture",
        ],
        "why_it_matters": (
            "Specialist agents that explain their reasoning, attribute sources, and log every "
            "decision step are the only enterprise-acceptable form of AI automation."
        ),
        "source": "fake_research_tool (enterprise scenario fixture)",
    },
    "default": {
        "trend": "Agentic AI workflows for product discovery and decision support",
        "opportunity": "Teams need visible multi-agent collaboration, not black-box chat responses",
        "evidence": [
            "OpenAI Agents SDK documents handoffs and tracing for specialist agent systems",
            "Enterprise buyers ask how AI decisions are made, not just what answer was returned",
            "XingAI product family already uses orchestrator + specialist agent patterns",
        ],
        "why_it_matters": (
            "A demo that shows orchestrator routing, specialist outputs, and trace logs "
            "helps non-technical stakeholders understand agent systems quickly."
        ),
        "source": "fake_research_tool (default fixture)",
    },
}

_KEYWORD_MAP: dict[str, str] = {
    "invest": "invest",
    "stock": "invest",
    "portfolio": "invest",
    "finance": "invest",
    "meal": "meal",
    "food": "meal",
    "nutrition": "meal",
    "recipe": "meal",
    "learn": "learn",
    "study": "learn",
    "sat": "learn",
    "education": "learn",
    "tutor": "learn",
    "enterprise": "enterprise",
    "workflow": "enterprise",
    "automation": "enterprise",
    "knowledge work": "enterprise",
}


def _match_topic(text: str) -> str:
    lower = text.lower()
    for keyword, topic in _KEYWORD_MAP.items():
        if keyword in lower:
            return topic
    return "default"


def fake_research_lookup(db: Session, topic: str) -> tuple[dict, str]:
    """Return topic-aware research fixture, cached by topic hash."""
    cached = cache_get(db, "research", topic)
    if cached:
        logger.debug("Research cache hit for topic (len=%d)", len(topic))
        return cached, "cache_tool"

    matched = _match_topic(topic)
    insight = _FIXTURES[matched]
    logger.debug("Research cache miss — using fixture '%s'", matched)
    cache_set(db, "research", topic, insight)
    return insight, "fake_research_tool"
