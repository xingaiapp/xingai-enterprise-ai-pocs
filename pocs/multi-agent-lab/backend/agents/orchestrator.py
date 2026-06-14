from __future__ import annotations

import json
import time
import uuid
from typing import Any

from sqlalchemy.orm import Session

from agents import critic_agent, product_agent, research_agent, tech_agent
from config import settings
from services.llm import chat_json
from tools.fake_research_tool import fake_research_lookup
from trace import log_trace, save_demo_run

DEFAULT_PROMPT = (
    "I want to build a new XingAI product from latest AI research ideas. "
    "Find one idea, turn it into a product concept, propose MVP features, "
    "and explain technical architecture."
)


def _format_final_answer(
    research: dict,
    product: dict,
    tech: dict,
    critic: dict,
    synthesized: dict | None = None,
) -> str:
    if synthesized:
        sections = [
            ("Research insight", synthesized.get("research_insight", "")),
            ("Product opportunity", synthesized.get("product_opportunity", "")),
            ("MVP feature list", synthesized.get("mvp_features", "")),
            ("Technical architecture", synthesized.get("technical_architecture", "")),
            ("Risks", synthesized.get("risks", "")),
            ("Next actions", synthesized.get("next_actions", "")),
        ]
    else:
        sections = [
            ("Research insight", json.dumps(research, ensure_ascii=False, indent=2)),
            ("Product opportunity", json.dumps(product, ensure_ascii=False, indent=2)),
            ("MVP feature list", json.dumps(product.get("mvp_features", []), ensure_ascii=False, indent=2)),
            ("Technical architecture", json.dumps(tech, ensure_ascii=False, indent=2)),
            ("Risks", json.dumps(critic, ensure_ascii=False, indent=2)),
            (
                "Next actions",
                "- Run the demo twice to show cache + trace\n"
                "- Review trace timeline with the team\n"
                "- Pick one insight to productize in XingAI family",
            ),
        ]

    parts = []
    for idx, (title, body) in enumerate(sections, start=1):
        if isinstance(body, list):
            body = "\n".join(f"- {item}" for item in body)
        parts.append(f"{idx}. {title}\n{body}")
    return "\n\n".join(parts)


def _synthesize_final(user_request: str, research: dict, product: dict, tech: dict, critic: dict) -> dict | None:
    if not settings.openai_configured:
        return None

    system = """You are the Orchestrator Agent in XingAI Agent Lab.
Combine specialist agent outputs into a final demo answer.
Return JSON with keys:
research_insight, product_opportunity, mvp_features, technical_architecture, risks, next_actions.
Keep each section concise for a live team demo."""

    user = f"""User request:
{user_request}

Research:
{research}

Product:
{product}

Tech:
{tech}

Critic:
{critic}"""

    return chat_json(system, user) or None


def run_pipeline(db: Session, user_input: str) -> dict[str, Any]:
    request_id = str(uuid.uuid4())
    text = user_input.strip() or DEFAULT_PROMPT
    step = 1
    t0 = time.monotonic()

    decision = {
        "decision": "Route to Research, Product, Tech, and Critic agents",
        "agents": ["Research Agent", "Product Agent", "Tech Agent", "Critic Agent"],
        "reason": "User asked for idea → research → product plan → architecture → risks",
        "phase": "Phase 1 · MVP Validation Layer",
    }
    log_trace(
        db, request_id, step, "Orchestrator Agent", text, decision,
        tool_used="handoff_planning", duration_ms=int((time.monotonic() - t0) * 1000),
    )
    step += 1

    t1 = time.monotonic()
    research_seed, research_tool = fake_research_lookup(db, text)
    research, research_backend = research_agent.run(db, text, research_seed)
    log_trace(
        db,
        request_id,
        step,
        "Research Agent",
        json.dumps({"user_request": text, "seed": research_seed}, ensure_ascii=False),
        research,
        tool_used=research_tool if research_backend.startswith("fake") else f"{research_tool}, {research_backend}",
        duration_ms=int((time.monotonic() - t1) * 1000),
    )
    step += 1

    t2 = time.monotonic()
    product, product_backend = product_agent.run(text, research)
    log_trace(
        db,
        request_id,
        step,
        "Product Agent",
        json.dumps(research, ensure_ascii=False),
        product,
        tool_used=product_backend,
        duration_ms=int((time.monotonic() - t2) * 1000),
    )
    step += 1

    t3 = time.monotonic()
    tech, tech_backend = tech_agent.run(text, product)
    log_trace(
        db,
        request_id,
        step,
        "Tech Agent",
        json.dumps(product, ensure_ascii=False),
        tech,
        tool_used=tech_backend,
        duration_ms=int((time.monotonic() - t3) * 1000),
    )
    step += 1

    t4 = time.monotonic()
    critic, critic_backend = critic_agent.run(text, product, tech)
    log_trace(
        db,
        request_id,
        step,
        "Critic Agent",
        json.dumps({"product": product, "tech": tech}, ensure_ascii=False),
        critic,
        tool_used=critic_backend,
        duration_ms=int((time.monotonic() - t4) * 1000),
    )
    step += 1

    t5 = time.monotonic()
    synthesized = _synthesize_final(text, research, product, tech, critic)
    final_answer = _format_final_answer(research, product, tech, critic, synthesized)
    log_trace(
        db,
        request_id,
        step,
        "Orchestrator Agent",
        "Combine specialist outputs",
        {"final_answer_preview": final_answer[:500] + ("..." if len(final_answer) > 500 else "")},
        tool_used="synthesis",
        duration_ms=int((time.monotonic() - t5) * 1000),
    )

    save_demo_run(db, request_id, text, final_answer)

    return {
        "request_id": request_id,
        "user_input": text,
        "final_answer": final_answer,
        "openai_configured": settings.openai_configured,
        "sections": {
            "research": research,
            "product": product,
            "tech": tech,
            "critic": critic,
        },
    }
