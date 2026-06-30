# ADR-004: Event Bus AI Review — Design-Only Placeholder Policy

**Date:** 2026-06-28  
**Status:** Accepted  
**Author:** Xing @ XingAI  
**Supersedes:** —  
**Superseded by:** —  
**Also available:** [中文](004-event-bus-ai-review-placeholder.zh.md)

## Context

[Event Bus AI Review](../../pocs/event-bus-ai-review/) is **architecture design only** — no runnable worker yet. Flow target:

```text
event → AI review → compliance review → human approval → audit log
```

Runnable POCs today are [Multi-Agent Lab](../../pocs/multi-agent-lab/) and [Claims Multi-Agent RAG](../../pocs/claims-multiagent-rag-poc/). Reviewers ask how event-bus fits the same governance bar as [ADR-001](./001-supervisor-audit-human-in-the-loop.md) without shipping a fake "auto-approved" pipeline.

## Decision

### 1. Design-only until Phase 2 implementation

| Artifact | Allowed now | Blocked until implementation ADR |
|----------|-------------|----------------------------------|
| `architecture.md`, `flow.mmd`, `enterprise-mapping.md` | Yes | — |
| Simulated trace in slides/docs | Yes, labeled **design preview** | — |
| Runnable Kafka/SQS consumer | No | New ADR + supervisor pattern |
| Auto-publish after AI review | **Never** in docs or demos |

### 2. Placeholder rules (docs and future code)

| Rule | Requirement |
|------|-------------|
| **E1 Independent workers** | AI review and compliance review are **separate subscribers** — compliance must not be hidden inside the AI agent prompt |
| **E2 Human gate** | No action side-effect until human approval node passes ([ADR-001](./001-supervisor-audit-human-in-the-loop.md)) |
| **E3 Audit append-only** | Every step logs: event id, worker name, redacted input/output, timestamp, reviewer decision |
| **E4 Failure isolation** | One worker failure must not delete the original event or prior audit rows |
| **E5 No silent writes** | Downstream systems receive `WOULD_ACT` in POC stubs only — same as [ADR-003](./003-mcp-gateway-placeholder-policy.md) MCP write policy |

### 3. Relationship to orchestrator vs gateway

| Layer | Event-bus role |
|-------|----------------|
| **Orchestrator / supervisor** | Routes event to AI review → compliance → human queue |
| **MCP gateway** | Unchanged — tool calls to external systems still go through gateway ALLOW/DENY when implemented |
| **Event bus transport** | Fan-out only — not a third "Orchestration MCP" |

### 4. Success criteria (unchanged from POC architecture)

- AI and compliance workers independently replaceable.
- Human receives a **recommendation packet** — not raw logs.
- Audit sufficient for regulated demo (insurance, finance).

### 5. When to implement

Trigger runnable POC when **any**:

- Claims or lab POC needs async handoff from external event source (webhook, queue).
- Enterprise design article ships with customer ask for event-driven review.
- Second independent compliance worker pattern is needed beyond LangGraph supervisor.

Until then, keep `pocs/event-bus-ai-review/` as design reference only.

## Alternatives considered

- **Build minimal Kafka POC immediately** — rejected; infra friction before Claims pattern is proven.
- **Fold event-bus into Claims LangGraph** — rejected for demo clarity; insurance POC is synchronous supervisor today.
- **Skip ADR, wiki only** — rejected; same governance questions as MCP gateway ADR-003.

## Consequences

Positive: honest enterprise narrative; implementation checklist ready.  
Tradeoff: no runnable event-bus demo yet — multi-agent-lab + Claims cover Phase 1.

## Implementation status

- [x] ADR-004 documented
- [x] Design docs in `pocs/event-bus-ai-review/`
- [ ] Runnable event consumer
- [ ] Integration test with audit SQLite

## Related

- [ADR-001: Supervisor, audit, human-in-the-loop](./001-supervisor-audit-human-in-the-loop.md)
- [ADR-003: MCP gateway placeholder](./003-mcp-gateway-placeholder-policy.md)
- [Event Bus AI Review architecture](../../pocs/event-bus-ai-review/architecture.md)
- [Enterprise Agent Platform](../ENTERPRISE-AGENT-PLATFORM.md)
