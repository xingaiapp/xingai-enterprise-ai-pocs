"""
Supervisor graph — linear LangGraph state machine.

Intake → Retrieval → FraudCheck → Adjudication → Audit
Conditional: low-confidence intake → human_review (skip RAG).
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from langgraph.graph import END, StateGraph

from claims_rag.agents.adjudication_agent import run_adjudication
from claims_rag.agents.fraud_check_agent import run_fraud_check
from claims_rag.agents.intake_agent import intake_needs_human_review, run_intake
from claims_rag.agents.retrieval_agent import run_retrieval
from claims_rag.audit.audit_logger import AuditLogger
from claims_rag.models import (
    AdjudicationAction,
    AdjudicationDecision,
    ClaimWorkflowState,
)

logger = logging.getLogger(__name__)


def _state_to_model(state: dict[str, Any]) -> ClaimWorkflowState:
    return ClaimWorkflowState.model_validate(state)


def _model_to_state(state: ClaimWorkflowState) -> dict[str, Any]:
    return state.model_dump(mode="json")


def intake_node(state: dict[str, Any]) -> dict[str, Any]:
    workflow = _state_to_model(state)
    try:
        claim, backend = run_intake(workflow.raw_claim_text, trace_id=workflow.trace_id)
        workflow.claim_data = claim
        AuditLogger().log_step(
            workflow.trace_id,
            agent="intake",
            input_data={"raw_claim_text": workflow.raw_claim_text},
            output_data=claim.model_dump(mode="json"),
            metadata={"backend": backend},
        )
        if intake_needs_human_review(claim):
            workflow.pipeline_status = "escalated"
            workflow.decision = AdjudicationDecision(
                action=AdjudicationAction.ESCALATE_TO_HUMAN,
                reasoning="Intake confidence below threshold or required fields missing.",
                citations=[],
                confidence=claim.extraction_confidence,
            )
    except Exception as exc:
        workflow.errors.append(f"intake: {exc}")
        workflow.pipeline_status = "escalated"
        workflow.decision = AdjudicationDecision(
            action=AdjudicationAction.ESCALATE_TO_HUMAN,
            reasoning=f"Intake failed: {exc}",
            citations=[],
            confidence=0.0,
        )
    return _model_to_state(workflow)


def retrieval_node(state: dict[str, Any]) -> dict[str, Any]:
    workflow = _state_to_model(state)
    if workflow.claim_data is None:
        workflow.errors.append("retrieval: missing claim_data")
        return _model_to_state(workflow)
    try:
        bundle = run_retrieval(workflow.claim_data, trace_id=workflow.trace_id)
        workflow.retrieval = bundle
        AuditLogger().log_step(
            workflow.trace_id,
            agent="retrieval",
            input_data=workflow.claim_data.model_dump(mode="json"),
            output_data=bundle.model_dump(mode="json"),
        )
    except Exception as exc:
        workflow.errors.append(f"retrieval: {exc}")
        workflow.pipeline_status = "escalated"
        workflow.decision = AdjudicationDecision(
            action=AdjudicationAction.ESCALATE_TO_HUMAN,
            reasoning=f"Retrieval failed: {exc}",
            citations=[],
            confidence=0.0,
        )
    return _model_to_state(workflow)


def fraud_node(state: dict[str, Any]) -> dict[str, Any]:
    workflow = _state_to_model(state)
    if workflow.claim_data is None or workflow.retrieval is None:
        workflow.errors.append("fraud: missing upstream data")
        return _model_to_state(workflow)
    assessment = run_fraud_check(
        workflow.claim_data,
        workflow.retrieval,
        trace_id=workflow.trace_id,
    )
    workflow.fraud = assessment
    AuditLogger().log_step(
        workflow.trace_id,
        agent="fraud_check",
        input_data={
            "claim": workflow.claim_data.model_dump(mode="json"),
            "history_excerpts": [c.model_dump(mode="json") for c in workflow.retrieval.history_excerpts],
        },
        output_data=assessment.model_dump(mode="json"),
    )
    return _model_to_state(workflow)


def adjudication_node(state: dict[str, Any]) -> dict[str, Any]:
    workflow = _state_to_model(state)
    if workflow.claim_data is None or workflow.retrieval is None or workflow.fraud is None:
        workflow.errors.append("adjudication: missing upstream data")
        return _model_to_state(workflow)
    try:
        decision, backend = run_adjudication(
            workflow.claim_data,
            workflow.retrieval,
            workflow.fraud,
            trace_id=workflow.trace_id,
        )
        workflow.decision = decision
        workflow.pipeline_status = (
            "escalated" if decision.action == AdjudicationAction.ESCALATE_TO_HUMAN else "complete"
        )
        AuditLogger().log_step(
            workflow.trace_id,
            agent="adjudication",
            input_data={
                "claim": workflow.claim_data.model_dump(mode="json"),
                "fraud": workflow.fraud.model_dump(mode="json"),
            },
            output_data=decision.model_dump(mode="json"),
            metadata={"backend": backend},
        )
    except Exception as exc:
        workflow.errors.append(f"adjudication: {exc}")
        workflow.pipeline_status = "escalated"
        workflow.decision = AdjudicationDecision(
            action=AdjudicationAction.ESCALATE_TO_HUMAN,
            reasoning=f"Adjudication failed: {exc}",
            citations=[],
            confidence=0.0,
        )
    return _model_to_state(workflow)


def human_review_node(state: dict[str, Any]) -> dict[str, Any]:
    workflow = _state_to_model(state)
    if workflow.decision is None:
        workflow.decision = AdjudicationDecision(
            action=AdjudicationAction.ESCALATE_TO_HUMAN,
            reasoning="Routed to human review.",
            citations=[],
            confidence=0.0,
        )
    workflow.pipeline_status = "escalated"
    AuditLogger().log_step(
        workflow.trace_id,
        agent="human_review",
        input_data=workflow.to_audit_dict(),
        output_data=workflow.decision.model_dump(mode="json"),
    )
    return _model_to_state(workflow)


def audit_finalize_node(state: dict[str, Any]) -> dict[str, Any]:
    workflow = _state_to_model(state)
    AuditLogger().log_step(
        workflow.trace_id,
        agent="audit_finalize",
        input_data={},
        output_data=workflow.to_audit_dict(),
    )
    return _model_to_state(workflow)


def route_after_intake(state: dict[str, Any]) -> Literal["human_review", "retrieval"]:
    workflow = _state_to_model(state)
    if workflow.pipeline_status == "escalated" or workflow.decision is not None:
        return "human_review"
    if workflow.claim_data and intake_needs_human_review(workflow.claim_data):
        return "human_review"
    return "retrieval"


def route_after_retrieval(state: dict[str, Any]) -> Literal["human_review", "fraud_check"]:
    workflow = _state_to_model(state)
    if workflow.pipeline_status == "escalated":
        return "human_review"
    return "fraud_check"


def build_supervisor_graph():
    graph = StateGraph(dict)
    graph.add_node("intake", intake_node)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("fraud_check", fraud_node)
    graph.add_node("adjudication", adjudication_node)
    graph.add_node("human_review", human_review_node)
    graph.add_node("audit_finalize", audit_finalize_node)

    graph.set_entry_point("intake")
    graph.add_conditional_edges("intake", route_after_intake, {
        "human_review": "human_review",
        "retrieval": "retrieval",
    })
    graph.add_conditional_edges("retrieval", route_after_retrieval, {
        "human_review": "human_review",
        "fraud_check": "fraud_check",
    })
    graph.add_edge("fraud_check", "adjudication")
    graph.add_edge("adjudication", "audit_finalize")
    graph.add_edge("human_review", "audit_finalize")
    graph.add_edge("audit_finalize", END)
    return graph.compile()


def run_claim_pipeline(raw_claim_text: str, *, trace_id: str | None = None) -> ClaimWorkflowState:
    """Execute the full supervisor workflow for one claim."""
    initial = ClaimWorkflowState(raw_claim_text=raw_claim_text)
    if trace_id:
        initial.trace_id = trace_id
    logger.info("pipeline_start", extra={"trace_id": initial.trace_id})
    app = build_supervisor_graph()
    final_state = app.invoke(_model_to_state(initial))
    result = _state_to_model(final_state)
    logger.info(
        "pipeline_complete",
        extra={
            "trace_id": result.trace_id,
            "status": result.pipeline_status,
            "action": result.decision.action.value if result.decision else None,
        },
    )
    return result
