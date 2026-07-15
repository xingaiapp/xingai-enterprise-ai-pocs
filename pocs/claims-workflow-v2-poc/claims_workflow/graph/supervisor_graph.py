"""LangGraph supervisor — replaces pipeline.py's hand-written
_continue_from_triage / _continue_from_coverage / _continue_from_approval
branch-jumping (ADR-008/ADR-009 Phase 3), reusing the exact same agent
functions as nodes. Same linear-with-conditional-escalation shape
claims-multiagent-rag-poc's supervisor_graph.py uses.

Design note — dynamic entry point instead of checkpointing: the Case
Resolution Router needs to resume at a SPECIFIC stage (not always
"intake"), which LangGraph normally handles via a persisted checkpoint +
thread_id. This POC doesn't need cross-process resume (a claim is
resolved synchronously within one resume_claim() call), so build_graph()
instead compiles a fresh graph starting at whichever stage the router
picked, reusing the same node functions — no checkpointer, no persistence
layer, same node functions as intake through payment. This is a
deliberate scope reduction from "real" LangGraph checkpointed
human-in-the-loop, noted here rather than silently substituted.
"""
from __future__ import annotations

from typing import Callable, Dict, TypedDict

from langgraph.graph import END, StateGraph

from ..agents.approval import run_approval
from ..agents.damage_assessment import run_damage_assessment
from ..agents.doc_verification import run_doc_verification
from ..agents.fraud_scoring import run_fraud_scoring
from ..agents.fraud_triage import run_fraud_triage
from ..agents.intake import run_intake
from ..agents.payment import run_payment
from ..agents.policy_coverage import run_policy_coverage
from ..ledger import DecisionLedger
from ..models import Claim

# Linear stage order — same sequence pipeline.py's docstring and the
# design article's diagram describe.
_ORDER = [
    "intake",
    "doc_verification",
    "fraud_triage",
    "damage_assessment",
    "fraud_scoring",
    "policy_coverage",
    "approval",
    "payment",
]

_TERMINAL_STATUSES = {"rejected_incomplete", "denied", "paid"}


class GraphState(TypedDict):
    claim: Claim
    ledger: DecisionLedger


def _node(agent_fn: Callable[[Claim, DecisionLedger], str]):
    """Wraps an agent function (claim, ledger) -> "continue"/"escalate"/...
    as a LangGraph node. The agent mutates claim.status/claim.escalation
    in place — that's the routing signal downstream conditional edges
    read, not the string return value, since the graph inspects state
    between nodes rather than switching on a return code."""

    def node(state: GraphState) -> GraphState:
        agent_fn(state["claim"], state["ledger"])
        return state

    return node


_NODE_FNS: Dict[str, Callable] = {
    "intake": _node(run_intake),
    "doc_verification": _node(run_doc_verification),
    "fraud_triage": _node(run_fraud_triage),
    "damage_assessment": _node(run_damage_assessment),
    "fraud_scoring": _node(run_fraud_scoring),
    "policy_coverage": _node(run_policy_coverage),
    "approval": _node(run_approval),
    "payment": _node(run_payment),
}


def _stopped(state: GraphState) -> bool:
    claim = state["claim"]
    return claim.escalation is not None or claim.status in _TERMINAL_STATUSES


def _make_router(next_stage: str):
    def router(state: GraphState) -> str:
        return "END" if _stopped(state) else next_stage

    return router


def build_graph(entry_point: str = "intake"):
    """Compiles a fresh graph covering entry_point through payment/END.
    Cheap to call per submit/resume — no shared mutable graph state
    between calls, avoiding any cross-claim leakage risk."""
    if entry_point not in _ORDER:
        raise ValueError(f"unknown entry_point: {entry_point}")

    stages = _ORDER[_ORDER.index(entry_point):]
    graph = StateGraph(GraphState)

    for stage in stages:
        graph.add_node(stage, _NODE_FNS[stage])

    graph.set_entry_point(entry_point)

    for i, stage in enumerate(stages):
        if stage == "damage_assessment":
            # Unconditional — Fraud Scoring always runs immediately after
            # Damage Assessment, it never escalates on its own.
            graph.add_edge("damage_assessment", "fraud_scoring")
        elif stage == "payment":
            graph.add_edge("payment", END)
        else:
            next_stage = stages[i + 1]
            graph.add_conditional_edges(stage, _make_router(next_stage), {next_stage: next_stage, "END": END})

    return graph.compile()


def run_from(claim: Claim, ledger: DecisionLedger, entry_point: str) -> None:
    """Runs the graph in place — claim and ledger are mutated by the
    agent nodes exactly as pipeline.py's imperative version did; nothing
    is returned because there's nothing new to return, the caller already
    holds references to both mutated objects."""
    app = build_graph(entry_point)
    app.invoke({"claim": claim, "ledger": ledger})
