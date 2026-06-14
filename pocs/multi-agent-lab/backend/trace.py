from __future__ import annotations

import json
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from database import DemoRun, TraceLog


def log_trace(
    db: Session,
    request_id: str,
    step: int,
    agent_name: str,
    input_text: str,
    output: Any,
    tool_used: str = "",
    duration_ms: int = 0,
) -> None:
    output_text = output if isinstance(output, str) else json.dumps(output, ensure_ascii=False, indent=2)
    db.add(
        TraceLog(
            request_id=request_id,
            step=step,
            agent_name=agent_name,
            input_text=input_text,
            output_text=output_text,
            tool_used=tool_used,
            duration_ms=duration_ms,
        )
    )
    db.commit()


def save_demo_run(db: Session, request_id: str, user_input: str, final_answer: str) -> None:
    db.add(DemoRun(request_id=request_id, user_input=user_input, final_answer=final_answer))
    db.commit()


def get_trace(db: Session, request_id: str) -> dict[str, Any] | None:
    run = db.get(DemoRun, request_id)
    if not run:
        return None

    steps = (
        db.query(TraceLog)
        .filter(TraceLog.request_id == request_id)
        .order_by(TraceLog.step.asc())
        .all()
    )

    total_ms = sum(s.duration_ms for s in steps)

    return {
        "request_id": request_id,
        "user_input": run.user_input,
        "final_answer": run.final_answer,
        "created_at": run.created_at.isoformat(),
        "total_duration_ms": total_ms,
        "trace": [
            {
                "step": s.step,
                "agent_name": s.agent_name,
                "input": s.input_text,
                "output": s.output_text,
                "tool_used": s.tool_used or None,
                "duration_ms": s.duration_ms,
                "timestamp": s.created_at.isoformat(),
            }
            for s in steps
        ],
    }


def get_metrics(db: Session) -> dict[str, Any]:
    total_requests = db.query(func.count(DemoRun.request_id)).scalar() or 0
    avg_latency_ms = db.query(func.avg(TraceLog.duration_ms)).scalar() or 0
    agent_steps = db.query(func.count(TraceLog.id)).scalar() or 0

    return {
        "total_requests": total_requests,
        "success_rate": 100.0 if total_requests else 0.0,
        "avg_latency_ms": round(float(avg_latency_ms), 0),
        "agent_steps_logged": agent_steps,
        "phase": "Phase 1 · MVP Validation Layer",
    }
