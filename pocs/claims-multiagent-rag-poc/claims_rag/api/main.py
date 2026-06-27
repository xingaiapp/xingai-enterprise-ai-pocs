"""
FastAPI endpoints for claims submission and audit retrieval.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from claims_rag.audit.audit_logger import AuditLogger
from claims_rag.graph.supervisor_graph import run_claim_pipeline
from claims_rag.logging_setup import configure_logging
from claims_rag.models import ClaimWorkflowState

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Claims Multi-Agent RAG POC",
    description="Supervisor + RAG + human-in-the-loop insurance claims demo",
    version="0.1.0",
)


class ClaimSubmitRequest(BaseModel):
    raw_claim_text: str = Field(min_length=10)


class ClaimSubmitResponse(BaseModel):
    trace_id: str
    pipeline_status: str
    decision: dict[str, Any] | None
    errors: list[str]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/claims/submit", response_model=ClaimSubmitResponse)
def submit_claim(body: ClaimSubmitRequest) -> ClaimSubmitResponse:
    logger.info("claim_submitted", extra={"text_len": len(body.raw_claim_text)})
    result: ClaimWorkflowState = run_claim_pipeline(body.raw_claim_text)
    return ClaimSubmitResponse(
        trace_id=result.trace_id,
        pipeline_status=result.pipeline_status,
        decision=result.decision.model_dump(mode="json") if result.decision else None,
        errors=result.errors,
    )


@app.get("/claims/{trace_id}/audit")
def get_claim_audit(trace_id: str) -> dict[str, Any]:
    rows = AuditLogger().get_trace(trace_id)
    if not rows:
        raise HTTPException(status_code=404, detail="trace_id not found")
    return {"trace_id": trace_id, "steps": rows}
