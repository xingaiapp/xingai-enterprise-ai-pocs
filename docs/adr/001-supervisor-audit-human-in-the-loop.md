# ADR-001: Supervisor Orchestration, Audit Trail, and Human-in-the-Loop

**Date:** 2026-06-17  
**Status:** Accepted  
**Author:** Xing @ XingAI  
**Supersedes:** —  
**Superseded by:** —  
**Also available:** [中文](001-supervisor-audit-human-in-the-loop.zh.md)

## Context

`xingai-enterprise-ai-pocs` validates patterns for the future **XingAI Enterprise Agent Platform** before productizing them for clients. Early POCs (`multi-agent-lab`, `claims-multiagent-rag-poc`) share the same governance problems:

- Free-form agent swarms are hard to test, audit, and explain to non-technical stakeholders.
- LLM-only decisions without document citations are not acceptable in regulated workflows (insurance, finance, HR).
- High-stakes outcomes must route to humans — never silent auto-approval.

We need one repo-level ADR so every POC implements the same minimum bar.

## Decision

### 1. Supervisor pattern (not agent swarms)

Every runnable POC uses an **explicit orchestrator** — LangGraph state machine or equivalent — where:

- Exactly one specialist agent is active at each step.
- State is a typed object (Pydantic / TypedDict) passed between nodes.
- Conditional edges handle escalation (e.g. low intake confidence → human review).
- The graph file must be readable in a live demo (screen-share friendly).

Agents do **not** call each other ad hoc without going through the supervisor.

### 2. Append-only audit trail

Every agent step logs:

- `trace_id` (correlates one end-to-end run)
- Agent name
- Redacted input / output JSON
- Optional metadata (backend, latency, tool name)
- UTC timestamp

Storage: SQLite append-only table for POCs; production path is immutable compliance store.

**PII:** `redact()` strips SSN-like patterns before any log line. Synthetic data only in POCs.

### 3. Human-in-the-loop thresholds

Config-driven thresholds (YAML — no magic numbers in code):

| Signal | Default POC behavior |
|--------|----------------------|
| Low extraction / decision confidence | `ESCALATE_TO_HUMAN` |
| High fraud / risk score | Escalate — **never auto-deny on fraud alone** |
| High dollar amount | Escalate regardless of model confidence |
| Retrieval or LLM failure | Escalate with error reason — no silent guess |

Adjudication agents must cite at least one source document for APPROVE/DENY when `require_policy_citation: true`.

### 4. RAG citation discipline

When retrieval is used:

- Separate vector collections per domain (policy / history / regulations — never mixed).
- Every chunk exposed to downstream agents includes `document_id`, `chunk_id`, similarity score.
- No agent sees retrieved text without citation metadata attached.

### 5. Observability

Minimum POC observability:

- Structured JSON logs with `trace_id`
- LangSmith or OpenTelemetry when API keys present
- Golden-set eval for decision accuracy (target ≥ 80% on synthetic fixtures)

### 6. POC documentation requirements

Each POC folder includes: `README.md`, `architecture.md`, `enterprise-mapping.md`, `flow.mmd`, `references.md` per [POC-STANDARDS.md](../POC-STANDARDS.md).

## Alternatives considered

- **Single monolithic prompt** — rejected (untestable, no audit granularity).
- **Agent swarm with shared memory** — rejected for Phase 1 (hard to explain in enterprise reviews).
- **Auto-deny on fraud** — rejected (liability; escalate instead).

## Consequences

Positive: consistent demo narrative across insurance, ideation, and future vertical POCs; maps cleanly to Platform orchestrator + audit + approval queue.

Tradeoff: more boilerplate per POC (graph, audit, config YAML, golden eval).

## Implementation status

- [x] ADR-001 documented
- [x] `multi-agent-lab` — trace timeline + orchestrator
- [x] `claims-multiagent-rag-poc` — LangGraph supervisor + SQLite audit + golden eval
- [ ] Platform service extraction (Phase 2)

## Related

- [Enterprise Agent Platform](../ENTERPRISE-AGENT-PLATFORM.md)
- [POC Standards](../POC-STANDARDS.md)
- [Claims POC](../../pocs/claims-multiagent-rag-poc/)
- [Multi-Agent Lab](../../pocs/multi-agent-lab/)
- Invest AI [ADR-028](https://github.com/xingaiapp/xingai-invest-ai/blob/main/docs/adr/028-robinhood-mcp-execution-gates.md) (execution gates — parallel human-in-the-loop pattern)
