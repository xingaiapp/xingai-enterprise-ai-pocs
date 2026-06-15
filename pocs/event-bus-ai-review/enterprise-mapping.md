# Enterprise Mapping: Event Bus AI Review

Maps the POC design to the XingAI Enterprise Agent Platform roadmap.

## What This POC Proves vs What Multi-Agent Lab Proves

| Dimension | Multi-Agent Lab | Event Bus AI Review |
|---|---|---|
| Trigger | User submits a goal via UI | A business event fires asynchronously |
| Coordination | Orchestrator routes sequentially | Event bus fans out to parallel subscribers |
| Compliance | Critic Agent embedded in pipeline | Independent compliance checker (parallel) |
| Human role | None (fully automated) | Required approval step before decision is final |
| Audit trail | SQLite trace after the fact | Immutable event log before and after decision |
| Failure model | Fallback JSON | Event is retained; worker retries independently |

**The core insight:** decoupling AI review from compliance review means either can be updated, replaced, or paused independently — without touching the other.

## POC → Platform Mapping

| POC Component | Enterprise Platform Equivalent | Phase |
|---|---|---|
| Simulated event emitter | Real event bus (Kafka, Pub/Sub, SQS) | Phase 3 |
| AI review worker | Orchestrator + specialist agents | Phase 2+ |
| In-memory compliance checker | Compliance Agent with policy registry | Phase 2 |
| Human approval stub | Full approval UI with context packet | Phase 3 |
| SQLite audit log | Immutable audit store (append-only DB) | Phase 3 |
| Synchronous flow | Async workers with retry + DLQ | Phase 3 |

## What This POC Does NOT Prove

- Real event durability (events lost on restart)
- Parallel execution of AI + compliance workers
- Real human approval UI
- Retry logic on worker failure
- Multi-tenant event routing

These belong in Phase 3.

## Why Build This POC

The Multi-Agent Lab proves orchestrator + handoffs in a request/response model.

The Event Bus POC proves a different pattern: **AI is one subscriber, not the orchestrator.** This matters for regulated industries where compliance review must be independent of the AI recommendation — legally, the compliance check cannot be inside the AI's own prompt chain.

## Positioning for Leadership

> "This POC answers: what happens when the AI is wrong, or the compliance rule changes?
> In the request/response model, you have to change the orchestrator.
> In the event-driven model, you replace one subscriber. The audit log, the human approval, and the other workers are untouched."

## Related

- [Multi-Agent Lab](../multi-agent-lab/) — request/response orchestration (Phase 1, runnable)
- [Enterprise Agent Platform](../../docs/ENTERPRISE-AGENT-PLATFORM.md)
- Design docs: see `references.md`
