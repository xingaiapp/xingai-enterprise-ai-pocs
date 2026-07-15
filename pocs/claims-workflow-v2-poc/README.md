# Claims Settlement Workflow v2 (XingAI corrected design)

> **Status: Runnable · Phase 1 + 2 + 3** (MCP tool access, LLM-backed fraud/coverage/letter agents with heuristic fallback, LangGraph supervisor — see [ADR-009](../../docs/adr/009-claims-workflow-v2-mcp-multiagent.md))

**Pattern:** Multi-agent claims pipeline with split fraud detection, an explicit escalation router, and a cross-cutting compliance audit trail
**Also available:** [中文](README.zh.md)

---

## What This Proves

A popular claims-automation infographic gets the overall shape right —
sequential specialized agents, tiered approval, a human escalation path —
but breaks in three specific places once you ask "how would this actually
run for a year, with a regulator asking questions": fraud detection runs
before it has the cost/photo data it needs, every escalation dumps into
one generic human-review box with no visible way back into the pipeline,
and nothing writes anything down for later. This POC proves all three
fixes are actually implementable, not just diagrammable: fraud detection
split into a pre-assessment Triage agent and a post-assessment Scoring
agent, a Case Resolution Router that resumes at a specific stage instead
of restarting from intake, and a Decision-Ledger-shaped audit trail every
stage writes to.

## Enterprise Pattern

- Multi-agent pipeline with two entry points (submit / resume) to model a real pause-for-human boundary
- Fraud detection split by information availability, not just by pipeline position
- Explicit, logged routing decisions instead of an implicit "restart the workflow" loop-back
- Compliance-by-construction: every agent decision is a ledger row, not a side effect
- Adverse-action letters generated from the specific ledger row and policy clause that produced a denial
- Idempotent payment writes, same requirement as [claims-partner-api-mcp-poc](../claims-partner-api-mcp-poc/)
- Data access (policy lookup, Decision Ledger, payments) behind an MCP server, not direct dict access — [ADR-009](../../docs/adr/009-claims-workflow-v2-mcp-multiagent.md)
- Fraud Triage/Scoring, Policy Coverage, and adverse-action-letter drafting run as real LLM agents when `ANTHROPIC_API_KEY` is set, with a heuristic fallback (same decision logic as Phase 1) when it isn't — every ledger row's `model_version` records which path actually ran
- Policy Coverage's LLM path retrieves real clause text (including exclusions) via a small dependency-light RAG layer, so it can deny a claim a flat coverage lookup would call "covered" if an exclusion genuinely applies
- Orchestration expressed as a graph (`claims_workflow/graph/`), not nested if/return branch-jumping — the same 8 agent functions are graph nodes, and the Case Resolution Router picks which node the graph resumes at

## Not Production Yet

- No persistence — claims, the Decision Ledger, and settlements all live in in-memory dicts and are lost on restart
- No authentication or authorization in front of the API, and the MCP server itself uses a single static internal service token — see [claims-mcp-oauth-poc](../claims-mcp-oauth-poc/) and [ADR-009](../../docs/adr/009-claims-workflow-v2-mcp-multiagent.md) for the planned upgrade path
- Without `ANTHROPIC_API_KEY`, every LLM-backed agent runs its heuristic fallback — the LLM paths are real but only exercised by `tests/eval/` (`pytest -m eval`) and manual runs, not the default test suite
- `MOCK_POLICIES` / `policy_documents.py` are small fixtures, not a real policy administration system integration
- No multi-tenant isolation, rate limiting, or observability
- `resume_claim()` takes the human's decision as a direct argument — no real review-queue UI or notification system exists yet
- The LangGraph supervisor (`claims_workflow/graph/`) doesn't use real checkpointing — a claim is resolved synchronously within one `submit_claim`/`resume_claim` call, not paused-and-resumed across processes; see ADR-009 "Phase 3 implementation note" for what a production version would need instead
- See [PRODUCTION-READINESS.md](PRODUCTION-READINESS.md) for the full gap analysis, organized by AI agent / MCP / automation / claims-industry-regulatory concerns, with a suggested priority order

## Architecture

See [`flow.mmd`](flow.mmd) for the full diagram and [`architecture.md`](architecture.md) for component-level detail. Summary:

```text
Intake → Document Verification → Fraud Triage → Damage Assessment → Fraud Scoring
       → Policy Coverage → Approval → Payment

Any stage can escalate to the Case Resolution Router, which resumes at a
specific stage (not intake) based on the escalation reason + human outcome.
Every stage writes to the Decision Ledger regardless of outcome.
```

## Quick Start

```bash
cd pocs/claims-workflow-v2-poc
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

pytest -q                      # 40 tests, zero API keys needed — heuristic fallback path
export ANTHROPIC_API_KEY=sk-...  # optional — enables the real LLM path
pytest -m eval -q              # 5 more tests exercising the real model (skipped without a key)

uvicorn claims_workflow.api.main:app --reload --port 8091
# in another terminal, optionally: uvicorn mcp_server.main:app --port 8092
# (not required — claims_workflow talks to mcp_server in-process by default;
#  set MCP_SERVER_URL to point at a separately-running instance instead)
# or: docker compose up --build
```

## API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/claims/submit` | Submit a new claim; runs until settlement, denial, or first escalation |
| `GET` | `/claims/{id}` | Current claim state |
| `POST` | `/claims/{id}/resolve` | Resolve an active escalation with a human outcome; Router decides re-entry point |
| `GET` | `/claims/{id}/audit` | Full Decision Ledger history for the claim |
| `GET` | `/claims/{id}/adverse-action-letter` | Adverse-action letter, if the claim was denied |
| `GET` | `/health` | Liveness check |

## Team Demo Script

1. `POST /claims/submit` a clean auto claim (`policy_id=POL-1001`, `reported_amount=3000`) → walks straight to `status=paid`. `GET /claims/{id}/audit` shows all 8 stages logged.
2. Submit the same claim with `prior_claims_count=5` → escalates at `fraud_triage`, **before** any damage estimate exists (`damage_cost` is `null` in the response). This is Fix 1's first half.
3. Submit a claim with `reported_amount=3000`, `assessed_cost_hint=1000` (in the request body via a claim that reaches Damage Assessment) → passes Triage, gets caught at `fraud_scoring` once the cost anomaly is visible. This is Fix 1's second half — the same claim, two different fraud agents, two different reasons they can or can't see it.
4. Resolve a `missing_docs` escalation with `outcome=resolved` and `documents_added` → claim resumes at Document Verification and completes; `GET /claims/{id}/audit` shows exactly one `intake` row — proof the router didn't restart the pipeline. This is Fix 2.
5. Submit a claim with `loss_type=property` against `POL-1001` (auto-only) → denied. `GET /claims/{id}/adverse-action-letter` returns the specific policy clause, not a generic message. This is Fix 3.
6. With `ANTHROPIC_API_KEY` set, submit an auto claim with `loss_description="Was racing a friend on a closed course when I hit a wall."` against `POL-1001` — the LLM Policy Coverage path denies it via the racing exclusion clause even though `loss_type=auto` is nominally covered, something the flat coverage lookup structurally can't do. Check `GET /claims/{id}/audit` for `model_version` starting with `policy-coverage-llm-`.

## Lessons Learned

- The stage-aware branch in the router (`fraud_investigation` + `cleared` resumes at `damage_assessment` if the escalation came from Triage, but at `policy_coverage` if it came from Scoring) wasn't in the original design article's routing table — that table predates the fraud-detection split. Writing the router in code forced this out: a router that only keys off `reason` can't correctly resume a Triage-stage clearance, because Damage Assessment and Fraud Scoring genuinely haven't run yet. The article's table was right for a single fraud stage; splitting fraud detection required extending the router's key from `(reason, outcome)` to `(reason, stage, outcome)`.
- Building the payment idempotency store as a plain module-level dict made the "replay returns the same record" test almost trivially easy to write — and immediately obvious when it *wasn't* being hit (an early draft generated a new `settled_at` timestamp on replay, which the test caught).
- Modeling `submit_claim` / `resume_claim` as two separate functions instead of one loop with a `human_decision=None` default made the API layer much simpler to reason about (`POST /submit` vs `POST /resolve` map directly onto them) — a single-function version kept tempting the API handler into passing partial state incorrectly.
- (Phase 2) Monkeypatching `llm_client._call_anthropic` directly in tests to simulate a network failure exposed that `complete_json`/`complete_text` were trusting `_call_anthropic` to always raise `LLMError` — a raw exception from a monkeypatched (or genuinely misbehaving) version of that function would have propagated straight past every agent's `except LLMError` fallback. Fixed with a second wrapping layer (`_safe_call_anthropic`) inside `complete_json`/`complete_text` itself, not just inside `_call_anthropic`.
- (Phase 3) LangGraph's normal resume mechanism is a persisted checkpoint + `thread_id` — this POC didn't need that (a claim resolves synchronously within one call), so `build_graph(entry_point)` compiles a fresh graph per call starting at whichever stage the router picked instead of maintaining one long-lived checkpointed graph. Worth being explicit this is a scoped-down substitute, not the same mechanism a "paused for days, resumed by a different process" claim would need.
- (Phase 2) RAG for Policy Coverage didn't need a vector database — the per-policy clause corpus is small enough that a ~40-line pure-Python hashing-trick embedding is enough to retrieve the right exclusion clause, keeping the dependency list exactly where it was instead of adding `chromadb` the way `claims-multiagent-rag-poc` did for its larger, cross-policy retrieval problem.

## Related Design Docs

- EN: [Redesigning the Agentic Claims Workflow](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-14-claims-workflow-redesign-fraud-routing-audit.md)
- 中文: [重新设计理赔工作流](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-14-claims-workflow-redesign-fraud-routing-audit.zh.md)
- [Claims Settlement Workflow v2 diagram](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/assets/ARCHITECTURE-DIAGRAMS.md#claims-settlement-workflow-v2-xingai-corrected-design)
- [Third-Party MCP Access: API Key or OAuth 2.1?](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-15-third-party-mcp-auth-api-key-vs-oauth2.md) · [中文](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-15-third-party-mcp-auth-api-key-vs-oauth2.zh.md)
- [ADR-008: Claims Workflow v2 POC](../../docs/adr/008-claims-workflow-v2-poc.md) · [中文](../../docs/adr/008-claims-workflow-v2-poc.zh.md)
- [ADR-009: MCP tool access, LLM agents, LangGraph supervisor](../../docs/adr/009-claims-workflow-v2-mcp-multiagent.md) · [中文](../../docs/adr/009-claims-workflow-v2-mcp-multiagent.zh.md)
- [PRODUCTION-READINESS.md](PRODUCTION-READINESS.md) · [中文](PRODUCTION-READINESS.zh.md) — production-readiness gap analysis
- See [`references.md`](references.md) for the full list, including sibling POCs
