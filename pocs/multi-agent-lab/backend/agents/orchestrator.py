from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

from sqlalchemy.orm import Session

from agents import critic_agent, product_agent, research_agent, tech_agent
from agents.prompts import SYNTHESIS_SYSTEM
from config import settings
from services.llm import chat_json
from tools.fake_research_tool import fake_research_lookup
from trace import log_trace, save_demo_run

logger = logging.getLogger(__name__)

DEFAULT_PROMPT = (
    "I want to build a new XingAI product from latest AI research ideas. "
    "Find one idea, turn it into a product concept, propose MVP features, "
    "and explain technical architecture."
)


def _run_safe(
    agent_name: str,
    fn,
    *args,
    fallback_fn=None,
) -> tuple[dict, str, str | None]:
    """Run an agent function safely.

    Returns (result, backend, error_message).
    On empty result or exception, falls back to fallback_fn() and surfaces the error.
    """
    try:
        result, backend = fn(*args)
        if not result:
            msg = f"{agent_name} returned empty result (OpenAI may be unavailable or returned empty JSON)"
            logger.warning(msg)
            fb = fallback_fn() if fallback_fn else {}
            return fb, "fallback", msg
        return result, backend, None
    except Exception as exc:
        msg = f"{agent_name} raised {type(exc).__name__}: {exc}"
        logger.error(msg)
        fb = fallback_fn() if fallback_fn else {}
        return fb, "error", msg


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


def _synthesize_final(
    user_request: str,
    research: dict,
    product: dict,
    tech: dict,
    critic: dict,
    request_id: str = "",
) -> dict | None:
    if not settings.openai_configured:
        return None

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

    return chat_json(SYNTHESIS_SYSTEM, user, request_id=request_id) or None


def run_pipeline(db: Session, user_input: str) -> dict[str, Any]:
    request_id = str(uuid.uuid4())
    text = user_input.strip() or DEFAULT_PROMPT
    step = 1
    pipeline_errors: list[dict] = []
    t0 = time.monotonic()

    logger.info("[%s] Pipeline start: %s…", request_id, text[:80])

    # Step 1 — Orchestrator planning
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

    # Step 2 — Research Agent
    t1 = time.monotonic()
    research_seed, research_tool = fake_research_lookup(db, text)
    research, research_backend, research_err = _run_safe(
        "Research Agent",
        lambda: research_agent.run(db, text, research_seed, request_id=request_id),
        fallback_fn=lambda: research_agent.fallback(research_seed),
    )
    if research_err:
        pipeline_errors.append({"step": step, "agent": "Research Agent", "error": research_err})
    log_trace(
        db, request_id, step, "Research Agent",
        json.dumps({"user_request": text, "seed": research_seed}, ensure_ascii=False),
        research,
        tool_used=research_tool if not research_err else f"{research_tool}, error",
        duration_ms=int((time.monotonic() - t1) * 1000),
    )
    step += 1

    # Step 3 — Product Agent
    t2 = time.monotonic()
    product, product_backend, product_err = _run_safe(
        "Product Agent",
        lambda: product_agent.run(text, research, request_id=request_id),
        fallback_fn=product_agent.fallback,
    )
    if product_err:
        pipeline_errors.append({"step": step, "agent": "Product Agent", "error": product_err})
    log_trace(
        db, request_id, step, "Product Agent",
        json.dumps(research, ensure_ascii=False),
        product,
        tool_used=product_backend,
        duration_ms=int((time.monotonic() - t2) * 1000),
    )
    step += 1

    # Step 4 — Tech Agent
    t3 = time.monotonic()
    tech, tech_backend, tech_err = _run_safe(
        "Tech Agent",
        lambda: tech_agent.run(text, product, request_id=request_id),
        fallback_fn=tech_agent.fallback,
    )
    if tech_err:
        pipeline_errors.append({"step": step, "agent": "Tech Agent", "error": tech_err})
    log_trace(
        db, request_id, step, "Tech Agent",
        json.dumps(product, ensure_ascii=False),
        tech,
        tool_used=tech_backend,
        duration_ms=int((time.monotonic() - t3) * 1000),
    )
    step += 1

    # Step 5 — Critic Agent
    t4 = time.monotonic()
    critic, critic_backend, critic_err = _run_safe(
        "Critic Agent",
        lambda: critic_agent.run(text, product, tech, request_id=request_id),
        fallback_fn=critic_agent.fallback,
    )
    if critic_err:
        pipeline_errors.append({"step": step, "agent": "Critic Agent", "error": critic_err})
    log_trace(
        db, request_id, step, "Critic Agent",
        json.dumps({"product": product, "tech": tech}, ensure_ascii=False),
        critic,
        tool_used=critic_backend,
        duration_ms=int((time.monotonic() - t4) * 1000),
    )
    step += 1

    # Step 6 — Orchestrator synthesis
    t5 = time.monotonic()
    synthesized = _synthesize_final(text, research, product, tech, critic, request_id=request_id)
    final_answer = _format_final_answer(research, product, tech, critic, synthesized)
    log_trace(
        db, request_id, step, "Orchestrator Agent",
        "Combine specialist outputs",
        {"final_answer_preview": final_answer[:500] + ("…" if len(final_answer) > 500 else "")},
        tool_used="synthesis",
        duration_ms=int((time.monotonic() - t5) * 1000),
    )

    save_demo_run(db, request_id, text, final_answer)

    total_ms = int((time.monotonic() - t0) * 1000)
    logger.info(
        "[%s] Pipeline complete in %dms, errors=%d",
        request_id, total_ms, len(pipeline_errors),
    )

    return {
        "request_id": request_id,
        "user_input": text,
        "final_answer": final_answer,
        "openai_configured": settings.openai_configured,
        "pipeline_errors": pipeline_errors,
        "sections": {
            "research": research,
            "product": product,
            "tech": tech,
            "critic": critic,
        },
    }
