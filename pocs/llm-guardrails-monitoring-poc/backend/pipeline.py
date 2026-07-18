"""
LLM Guardrails & Monitoring POC — 12-step demo pipeline.

Phases: Plan → Build → Validate → Operate
XingAI corrections vs tool-shopping posters are noted on each step.
"""

from __future__ import annotations

import hashlib
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


PHASES = ("Plan", "Build", "Validate", "Operate")

KNOWLEDGE = [
    {
        "id": "pol-refund-01",
        "title": "Premium Refund Policy",
        "text": (
            "Premium subscribers may request a full refund within 14 days of purchase "
            "if unused. Partial refunds after 14 days require manager approval."
        ),
        "tags": ["refund", "premium", "billing"],
    },
    {
        "id": "pol-support-02",
        "title": "Support Scope",
        "text": (
            "Support bots may answer only from approved company policy documents. "
            "They must refuse legal, medical, and investment advice."
        ),
        "tags": ["support", "scope"],
    },
]


INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|system)\s+instructions", re.I),
    re.compile(r"jailbreak", re.I),
    re.compile(r"dump\s+(secrets?|api\s*keys?)", re.I),
    re.compile(r"exfiltrat", re.I),
]

RISKY_TOOL_PATTERNS = [
    re.compile(r"transfer[_ ]?funds?", re.I),
    re.compile(r"wire\s+money", re.I),
    re.compile(r"delete\s+all\s+users", re.I),
]

STEP_META = {
    1: ("Plan", "Define the Use Case"),
    2: ("Plan", "Map Risks & Policy"),
    3: ("Build", "Choose Model & Hosting"),
    4: ("Build", "Add Knowledge with RAG"),
    5: ("Build", "Design Prompt & Context"),
    6: ("Build", "Add Input Guardrails"),
    7: ("Build", "Add Tool & API Controls"),
    8: ("Validate", "Add Output Guardrails"),
    9: ("Validate", "Monitor Quality & Behavior"),
    10: ("Validate", "Evaluate & Red-Team"),
    11: ("Operate", "Deploy Securely"),
    12: ("Operate", "Iterate & Govern"),
}


@dataclass
class StepResult:
    step: int
    phase: str
    name: str
    status: str  # passed | blocked | warned | skipped
    summary: str
    checks: list[str] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    xingai_correction: str = ""


@dataclass
class RunResult:
    run_id: str
    user_input: str
    final_status: str
    final_answer: str | None
    steps: list[StepResult]
    agent_run_trace: list[dict[str, Any]]
    duration_ms: float
    governance: dict[str, Any]


def _step(
    n: int,
    phase: str,
    name: str,
    status: str,
    summary: str,
    checks: list[str] | None = None,
    artifacts: dict[str, Any] | None = None,
    xingai_correction: str = "",
) -> StepResult:
    return StepResult(
        step=n,
        phase=phase,
        name=name,
        status=status,
        summary=summary,
        checks=checks or [],
        artifacts=artifacts or {},
        xingai_correction=xingai_correction,
    )


def run_pipeline(user_input: str, *, require_human_approval: bool = True) -> RunResult:
    """Execute all 12 demo steps for one user request."""
    del require_human_approval  # reserved for future durable-approval toggle
    t0 = time.perf_counter()
    run_id = str(uuid.uuid4())
    steps: list[StepResult] = []
    trace: list[dict[str, Any]] = []
    ctx: dict[str, Any] = {"user_input": user_input.strip()}

    def record(sr: StepResult) -> None:
        steps.append(sr)
        trace.append(
            {
                "event": "step",
                "step": sr.step,
                "name": sr.name,
                "status": sr.status,
                "ts": time.time(),
            }
        )

    record(
        _step(
            1,
            "Plan",
            "Define the Use Case",
            "passed",
            "Support bot answers only from approved policy docs; human-verifiable answers required.",
            checks=[
                "user_job=policy_qa",
                "channels=web_chat",
                "success=grounded_cite",
                "failure_cost=medium",
            ],
            artifacts={
                "use_case": {
                    "job": "Answer support questions from approved docs only",
                    "refuse": ["legal advice", "medical advice", "investment advice"],
                    "success_metrics": ["citation_present", "policy_aligned"],
                }
            },
            xingai_correction="Auth/audit posture starts here with risk — not at Deploy.",
        )
    )

    record(
        _step(
            2,
            "Plan",
            "Map Risks & Policy",
            "passed",
            "Policy matrix: allow policy Q&A; deny secrets dump, fund transfer, jailbreak.",
            checks=[
                "allowed_topics=billing,support_scope",
                "deny=secrets,payments,jailbreak",
                "confidence_threshold=0.6",
            ],
            artifacts={
                "policy_matrix": {
                    "allow": ["refund_policy", "support_scope"],
                    "deny": ["secrets", "wire_transfer", "ignore_system"],
                    "escalation": "human_review",
                    "severity": {"injection": "high", "wrong_answer": "medium"},
                }
            },
            xingai_correction="Risk before model choice (12-step ladder improvement).",
        )
    )
    ctx["policy"] = steps[-1].artifacts["policy_matrix"]

    record(
        _step(
            3,
            "Build",
            "Choose Model & Hosting",
            "passed",
            "Deterministic mock model for this POC (no live LLM). Task class: fast FAQ.",
            checks=["task_class=fast_faq", "hosting=local_mock", "timeout_ms=2000"],
            artifacts={"model": {"id": "mock-faq-v1", "task_class": "fast_faq", "live": False}},
            xingai_correction="Model by task class — never unverified version stickers.",
        )
    )
    ctx["model"] = steps[-1].artifacts["model"]

    query = ctx["user_input"].lower()
    hits: list[dict[str, Any]] = []
    for doc in KNOWLEDGE:
        score = sum(1 for t in doc["tags"] if t in query)
        score += sum(
            1
            for w in ("refund", "premium", "support", "policy")
            if w in query and w in doc["text"].lower()
        )
        if score > 0 or any(w in doc["text"].lower() for w in query.split() if len(w) > 4):
            hits.append({**doc, "score": float(score)})
    hits.sort(key=lambda d: d["score"], reverse=True)
    hits = hits[:3]
    evidence_ok = len(hits) >= 1 and hits[0]["score"] >= 1.0
    record(
        _step(
            4,
            "Build",
            "Add Knowledge with RAG",
            "passed" if evidence_ok else "warned",
            "Retrieved policy chunks with citation ids."
            if evidence_ok
            else "Weak/empty retrieval — evidence not sufficient; escalate later.",
            checks=[
                f"hits={len(hits)}",
                f"top_score={hits[0]['score'] if hits else 0}",
                f"evidence_sufficient={evidence_ok}",
            ],
            artifacts={"retrieval": hits, "evidence_sufficient": evidence_ok},
            xingai_correction="Evidence loop + sufficiency stop — not one-shot Top-K / vector logos.",
        )
    )
    ctx["retrieval"] = hits
    ctx["evidence_sufficient"] = evidence_ok

    record(
        _step(
            5,
            "Build",
            "Design Prompt & Context",
            "passed",
            "System prompt + output contract (JSON with citations) + refusal rules loaded.",
            checks=["output_contract=json_cite", "refusal_rules=loaded", "prompt_version=poc-1"],
            artifacts={
                "prompt": {
                    "system": "Answer only from retrieved policy. Cite doc ids. Refuse out-of-scope.",
                    "output_contract": {
                        "answer": "str",
                        "citations": "list[str]",
                        "confidence": "float",
                    },
                    "version": "poc-1",
                }
            },
            xingai_correction="Output contract + refusal belong in Decide/Build, not only UI copy.",
        )
    )

    observations = {
        "user": ctx["user_input"],
        "rag_join": " ".join(h["text"] for h in hits),
        "tool_desc": "tool: lookup_policy — returns policy text",
    }
    injection_hits = []
    for source, text in observations.items():
        for pat in INJECTION_PATTERNS:
            if pat.search(text or ""):
                injection_hits.append({"source": source, "pattern": pat.pattern})
    input_blocked = any(h["source"] == "user" for h in injection_hits)
    record(
        _step(
            6,
            "Build",
            "Add Input Guardrails",
            "blocked" if input_blocked else ("warned" if injection_hits else "passed"),
            "Blocked jailbreak/injection on user input."
            if input_blocked
            else (
                "Suspicious pattern in non-user observation (logged)."
                if injection_hits
                else "No injection patterns in user/RAG/tool observations."
            ),
            checks=[
                f"sources_scanned={list(observations)}",
                f"injection_hits={len(injection_hits)}",
            ],
            artifacts={"injection_hits": injection_hits},
            xingai_correction=(
                "Sanitize ALL untrusted observations (user, RAG, tools, other agents) "
                "— not jailbreak-only."
            ),
        )
    )
    if input_blocked:
        return _finalize(
            run_id,
            user_input,
            steps,
            trace,
            t0,
            final_status="blocked",
            final_answer=None,
            reason="input_guardrail",
        )

    tool_request = None
    for pat in RISKY_TOOL_PATTERNS:
        if pat.search(ctx["user_input"]):
            tool_request = {"tool": "transfer_funds", "risk": "high"}
            break
    if tool_request:
        record(
            _step(
                7,
                "Build",
                "Add Tool & API Controls",
                "blocked",
                "MCP two-wall blocked risky tool via scope wall; durable approval required.",
                checks=[
                    "wall_1_oauth_scope=support.read",
                    "wall_2_business_policy=no_payments",
                    "human_approval=required",
                ],
                artifacts={"tool_request": tool_request, "blocked_by": "scope"},
                xingai_correction=(
                    "MCP two-wall (scope + policy) + durable approval — not CrewAI/LangGraph logos."
                ),
            )
        )
        return _finalize(
            run_id,
            user_input,
            steps,
            trace,
            t0,
            final_status="blocked",
            final_answer=None,
            reason="tool_wall",
        )

    record(
        _step(
            7,
            "Build",
            "Add Tool & API Controls",
            "passed",
            "Allowed tool: lookup_policy (read-only). Scope=support.read; policy allows retrieval only.",
            checks=[
                "wall_1_oauth_scope=support.read",
                "wall_2_business_policy=retrieval_only",
                "side_effects=none",
            ],
            artifacts={"allowed_tools": ["lookup_policy"], "denied_tools": ["transfer_funds"]},
            xingai_correction=(
                "MCP two-wall (scope + policy) + durable approval — not CrewAI/LangGraph logos."
            ),
        )
    )

    if not evidence_ok:
        draft = {
            "answer": "I do not have enough approved policy evidence to answer confidently.",
            "citations": [],
            "confidence": 0.2,
            "escalate": True,
        }
    else:
        top = hits[0]
        draft = {
            "answer": top["text"],
            "citations": [top["id"]],
            "confidence": min(0.95, 0.55 + 0.1 * top["score"]),
            "escalate": False,
        }
    ctx["draft"] = draft
    trace.append({"event": "model_call", "model": ctx["model"]["id"], "ts": time.time()})

    out_issues = []
    if not draft["citations"] and not draft.get("escalate"):
        out_issues.append("missing_citations")
    if draft["confidence"] < 0.6 and not draft.get("escalate"):
        out_issues.append("low_confidence")
    if re.search(r"(?i)api[_-]?key|secret", draft["answer"]):
        out_issues.append("sensitive_leak")
    if out_issues and not draft.get("escalate"):
        out_status = "blocked"
    elif draft.get("escalate"):
        out_status = "warned"
    else:
        out_status = "passed"
    record(
        _step(
            8,
            "Validate",
            "Add Output Guardrails",
            out_status,
            "Output passed schema/citation/safety checks."
            if out_status == "passed"
            else (
                "Escalating due to insufficient evidence."
                if draft.get("escalate")
                else f"Output blocked: {out_issues}"
            ),
            checks=[
                "schema=ok",
                f"citations={draft['citations']}",
                f"confidence={draft['confidence']}",
                f"issues={out_issues}",
            ],
            artifacts={"draft": draft, "issues": out_issues},
            xingai_correction="Reject/repair/escalate — never hide critical uncertainty.",
        )
    )
    if out_status == "blocked":
        return _finalize(
            run_id,
            user_input,
            steps,
            trace,
            t0,
            final_status="blocked",
            final_answer=None,
            reason="output_guardrail",
            draft=draft,
        )

    record(
        _step(
            9,
            "Validate",
            "Monitor Quality & Behavior",
            "passed",
            "Agent Run trace recorded (goal → steps → model → tools → outcome).",
            checks=["trace_events_ok", "metrics=latency,cost_mock,refusal"],
            artifacts={
                "metrics": {
                    "latency_ms_so_far": round((time.perf_counter() - t0) * 1000, 2),
                    "token_usage_mock": 128,
                    "retrieval_hits": len(hits),
                }
            },
            xingai_correction="Trace Agent Runs (goal→tool→outcome) — not only HTTP latency/cost.",
        )
    )

    red_team_flags = []
    if injection_hits:
        red_team_flags.append("injection_corpus_hit")
    record(
        _step(
            10,
            "Validate",
            "Evaluate & Red-Team",
            "passed",
            "Release gate checks for this request path; golden/injection probes logged.",
            checks=[
                "golden_policy_qa=configured",
                "injection_suite=configured",
                f"run_flags={red_team_flags}",
                "block_on_critical=true",
            ],
            artifacts={"red_team_flags": red_team_flags, "eval_ok": True},
            xingai_correction="Block promote on critical eval failure — Course 06 release gates.",
        )
    )

    record(
        _step(
            11,
            "Operate",
            "Deploy Securely",
            "passed",
            "Demo runtime: no secrets in context; mock auth scope support.read; rate-limit ready.",
            checks=[
                "auth_posture=from_plan",
                "secrets_in_context=false",
                "tenant_isolation=poc_single",
                "ci_eval_gate=documented",
            ],
            artifacts={
                "deploy": {
                    "auth": "mock_bearer_support_read",
                    "gateway": "local",
                    "note": "Continuous controls — not a final checkbox",
                }
            },
            xingai_correction=(
                "Identity/APIM/secrets are continuous from Plan — Deploy is not 'security done'."
            ),
        )
    )

    governance_action = "escalate_human" if draft.get("escalate") else "ship_answer"
    record(
        _step(
            12,
            "Operate",
            "Iterate & Govern",
            "passed",
            f"Ledger row written; action={governance_action}; schedule monthly incident→test loop.",
            checks=[
                "decision_ledger=written",
                f"action={governance_action}",
                "change_requires_eval_evidence=true",
            ],
            artifacts={
                "ledger": {
                    "run_id": run_id,
                    "action": governance_action,
                    "citations": draft["citations"],
                    "policy_version": "poc-1",
                }
            },
            xingai_correction="Close the loop: incidents → new tests (12-step Operate).",
        )
    )

    final_answer = None if draft.get("escalate") else draft["answer"]
    final_status = "escalated" if draft.get("escalate") else "answered"
    return _finalize(
        run_id,
        user_input,
        steps,
        trace,
        t0,
        final_status=final_status,
        final_answer=final_answer,
        reason=governance_action,
        draft=draft,
    )


def _finalize(
    run_id: str,
    user_input: str,
    steps: list[StepResult],
    trace: list[dict[str, Any]],
    t0: float,
    *,
    final_status: str,
    final_answer: str | None,
    reason: str,
    draft: dict[str, Any] | None = None,
) -> RunResult:
    done = {s.step for s in steps}
    for n in range(1, 13):
        if n not in done:
            phase, name = STEP_META[n]
            steps.append(
                _step(
                    n,
                    phase,
                    name,
                    "skipped",
                    f"Skipped because earlier step stopped the run ({reason}).",
                    xingai_correction="Fail closed — do not continue past a wall.",
                )
            )
    steps.sort(key=lambda s: s.step)
    duration_ms = round((time.perf_counter() - t0) * 1000, 2)
    return RunResult(
        run_id=run_id,
        user_input=user_input,
        final_status=final_status,
        final_answer=final_answer,
        steps=steps,
        agent_run_trace=trace,
        duration_ms=duration_ms,
        governance={
            "reason": reason,
            "draft": draft,
            "fingerprint": hashlib.sha256(user_input.encode()).hexdigest()[:12],
        },
    )


def result_to_dict(result: RunResult) -> dict[str, Any]:
    return {
        "run_id": result.run_id,
        "user_input": result.user_input,
        "final_status": result.final_status,
        "final_answer": result.final_answer,
        "duration_ms": result.duration_ms,
        "phases": list(PHASES),
        "steps": [asdict(s) for s in result.steps],
        "agent_run_trace": result.agent_run_trace,
        "governance": result.governance,
    }
