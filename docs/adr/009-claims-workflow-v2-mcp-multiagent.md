# ADR-009: Claims Workflow v2 — Deepening into Real MCP Tool Access, LLM Agents, and a LangGraph Supervisor

**Date:** 2026-07-15
**Status:** Accepted (Phase 1, 2, and 3 implemented)
**Author:** Xing @ XingAI
**Also available:** [中文](009-claims-workflow-v2-mcp-multiagent.zh.md)

## Context

[ADR-008](008-claims-workflow-v2-poc.md) added `claims-workflow-v2-poc`: a runnable proof that the design article's three fixes (fraud-detection split, Case Resolution Router, compliance audit trail) work, implemented as plain Python functions calling each other directly and reading/writing in-memory dicts. That was deliberate — ADR-008 scoped out LLM calls and MCP entirely so the fixes themselves could be verified deterministically. But it means the POC's "agents" are agents in name only: no reasoning, no tool-call boundary, no protocol between them.

This ADR covers deepening that POC in three layers, and — separately — the authentication question for if/when a third-party vendor is meant to consume this POC's tools directly.

## Decision

**Implement in three phases, each independently shippable:**

### Phase 1 — MCP as the data-access boundary (this ADR's implemented scope)

Move `MOCK_POLICIES`, `DecisionLedger`, and the payment settlement store behind a new `mcp_server/` package (hand-rolled JSON-RPC `/mcp` endpoint over FastAPI, same pattern as `claims-mcp-oauth-poc/mcp_server/main.py` — no official MCP SDK dependency, consistent with existing precedent in this repo). Four tools, scoped to exactly the three local stores being moved (no speculative extra tools without a Phase-1 caller): `get_policy_coverage` (`policy.read`), `record_ledger_decision` (`audit.write`), `get_audit_trail` (`audit.read`), `create_payment` (`payments.write`, idempotent). `claims_workflow.ledger.DecisionLedger` and the policy-coverage/payment agents stop touching local dicts directly and instead go through a thin MCP client (`claims_workflow/mcp_client.py`) — in-process via ASGI transport by default (no separate process needed to run this POC's own tests), real HTTP when `MCP_SERVER_URL` is set (the docker-compose path). `get_claim_history` and a `get_claim` lookup tool are deliberately deferred to Phase 2, where the LLM-backed Fraud Triage agent is the first real caller that needs them — Phase 1 only moves stores that already existed, it doesn't add new capability. No LLM involved yet: this phase is purely "replace a direct Python call with a tool-call protocol call," so all 26 existing tests are expected to keep passing unchanged in behavior (verified — see Implementation status).

### Phase 2 — LLM agents for the judgment-heavy stages (planned, not started)

Not every stage benefits from becoming an LLM call. Converted:

| Stage | Becomes LLM-backed? | Why |
|---|---|---|
| Fraud Triage | Yes | Real velocity/tenure fraud detection needs to reason over free-text claim history, not just threshold-compare two numbers |
| Fraud Scoring | Yes | Cost-anomaly and photo-forensics judgment benefits from reasoning over unstructured evidence |
| Policy Coverage | Yes, and RAG-backed | Reuses `claims-multiagent-rag-poc`'s vector-store pattern so coverage determination reads actual policy language instead of a 3-entry dict — this is also what makes the adverse-action letter's clause citation genuine rather than a mock string |
| Adverse-action letter drafting | Yes | Turns a Decision Ledger row's structured `reasoning` into a real letter; low hallucination risk because the input is already-verified structured data, not open-ended generation |
| Approval (dollar-threshold check) | No | Pure number comparison; an LLM adds inconsistency risk with no benefit |
| Payment | No, never | Money-moving writes stay deterministic and idempotent, same rule `claims-partner-api-mcp-poc` established |
| Case Resolution Router | No — mapping table stays deterministic | An LLM should not invent a new route; it may classify a free-text human note into a structured `outcome` value that feeds the existing deterministic router, but the routing table itself is not LLM-decided |

Each LLM-backed agent keeps a heuristic fallback (its current Phase-1/ADR-008 implementation) so the test suite stays runnable with zero API keys — see "Testing strategy" below.

### Phase 3 — LangGraph supervisor (planned, not started)

Replace `pipeline.py`'s hand-written `_continue_from_triage` / `_continue_from_coverage` / `_continue_from_approval` branch-jumping with a LangGraph `StateGraph`, matching `claims-multiagent-rag-poc`'s supervisor pattern. The graph's nodes are the same nine stages; edges encode the same transitions `pipeline.py` currently hardcodes. This does **not** change where MCP sits: per the `xingai-enterprise-ai-design` article [Orchestrator vs MCP Gateway](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-06-13-orchestrator-vs-mcp-gateway.md), the supervisor/orchestrator itself is not an MCP server — MCP stays scoped to tool/data access for individual agent nodes, not to inter-agent handoff logic.

### Authentication for third-party MCP consumption (decided now, not yet wired)

If/when an external vendor is meant to call this POC's MCP tools directly (a future "Phase 4 / Direction D," not in this ADR's scope), **OAuth 2.1 + PKCE + JWT with per-tool scopes is required, not a static API key** — same conclusion [ADR-006](006-claims-mcp-oauth-poc-real-auth.md) already reached for claims adjudication generally, and it applies more strongly here because this pipeline moves money and produces legally-consequential denials:

- A static key carries no scope — a leaked key can do everything a legitimate caller can. OAuth scopes (`claims.read` / `policy.read` / `claims.adjudicate` / `payments.write`, reusing `claims-mcp-oauth-poc`'s existing vocabulary) let read access and payment-writing access be separately granted and separately revoked.
- This domain needs `claims-mcp-oauth-poc`'s two-wall model — OAuth scope plus an independent settlement-authority policy (dollar cap, claim-type allowlist) — because scope alone doesn't express a business-rule limit like "this partner may not authorize settlements over $10,000."
- A JWT's `sub` claim ties every Decision Ledger row to a specific caller identity, which the adverse-action-letter and regulatory-reporting use cases need; a shared static key can't provide that.

**What's actually built now:** Phase 1's `mcp_server/` uses a single static internal service token, because its only caller in this phase is our own process (no external trust boundary crossed yet) — same bootstrap `claims-partner-api-mcp-poc` used before ADR-007 added real auth. The tool scope names are chosen to match this repo's existing vocabulary rather than invent a new one: `policy.read` matches `claims-mcp-oauth-poc` exactly, `payments.write` matches `claims-partner-api-mcp-poc` exactly; `audit.read`/`audit.write` are new (neither sibling POC has an audit-trail tool to name a scope after) and documented as such. This is specifically so that wiring a real Authorization Server in front of this server later is a drop-in scope-mapping exercise, per the same combination pattern ADR-007 already documented for `claims-partner-api-mcp-poc`, not a rewrite.

### Testing strategy

Main `pytest` suite stays runnable with zero API keys: every LLM-backed agent (Phase 2) keeps its heuristic implementation as a fallback used whenever `ANTHROPIC_API_KEY` is unset, and Phase 1's MCP client/server round-trip is tested directly (spin up the FastAPI test client, call tools, assert on responses) with no model involved. A separate `tests/eval/` directory, marked `@pytest.mark.eval`, exercises the real LLM path and only runs when a key is present (`pytest -m eval`) — this is `claims-multiagent-rag-poc`'s existing pattern ("offline hash embeddings when OPENAI_API_KEY is unset"), applied here instead of invented fresh.

## Alternatives considered

- **Skip MCP, call an LLM directly from each agent function** — rejected. Without a tool-call boundary there's nothing forcing agents to go through a reviewable, scoped interface for data access; it would also make Phase 4 (third-party exposure) a rewrite instead of "add an Authorization Server in front of the server that already exists."
- **Build Phase 2 and Phase 3 in the same pass as Phase 1** — rejected for delivery risk. A+B+C together roughly doubles the POC's size and adds LLM prompt design, RAG wiring, and a new orchestration framework all at once; shipping Phase 1 alone first (data-access boundary only, no behavior change, same 26 tests) gives a checkpoint before committing to the more speculative parts.
- **Use the official `mcp` Python SDK / FastMCP instead of hand-rolling JSON-RPC over FastAPI** — rejected for this phase, purely for consistency: `claims-mcp-oauth-poc` already hand-rolls the same `/mcp` JSON-RPC endpoint pattern in this repo, and matching it means the eventual "put an Authorization Server in front of this" step is a known quantity instead of a second integration pattern to reconcile.
- **Require real API keys for all tests** — rejected; it would make this POC's CI-free "runnable" claim dependent on a paid external service, the same reasoning `claims-multiagent-rag-poc` already used to justify its offline-embeddings fallback.

## Consequences

Positive:
- Phase 1 introduces the MCP tool boundary with zero behavior change and zero new external dependency — lowest-risk step, fully verified by the existing test suite.
- Scope names chosen up front to match `claims-mcp-oauth-poc` mean Phase 4 (third-party exposure, if it happens) reuses an already-built Authorization Server instead of a new auth implementation.
- The Phase 2 stage-by-stage LLM/no-LLM table is a reusable decision framework other XingAI claims or adjacent-domain POCs can apply instead of re-litigating "should this agent be an LLM" per case.

Tradeoffs:
- Three-phase plan means this ADR documents work that is only partially done (Phase 1) — anyone reading it needs to check the Implementation status section, not assume the whole design is live.
- Phase 1's static internal service token is explicitly not safe past this repo's own process boundary; a reader who only skims the "Decision" section and misses "What's actually built now" could mistake the scope-name alignment for actual OAuth enforcement, which does not exist yet.
- Adding a LangGraph dependency (Phase 3) introduces this POC's first non-FastAPI/pydantic runtime dependency, same tradeoff `claims-multiagent-rag-poc` already accepted for the same reason (real supervisor pattern).

## Phase 2 implementation notes

Two things worth recording that weren't obvious from the Phase 2 table above until the code was written:

- **`complete_json`/`complete_text` need their own defense against a misbehaving `_call_anthropic`, not just the try/except already inside it.** The first version of `tests/test_llm_fallback.py` monkeypatched `llm_client._call_anthropic` directly to simulate a network failure — which bypassed that function's own internal try/except entirely (monkeypatching replaces the whole function body) and let a raw `RuntimeError` propagate past `complete_json`, past every agent's `except llm_client.LLMError`, and fail the test instead of triggering the fallback path it was supposed to test. Fixed by adding `_safe_call_anthropic()`, a second wrapping layer inside `complete_json`/`complete_text` that catches any exception — not just ones `_call_anthropic` itself chose to wrap — and re-raises as `LLMError`. This is the correct fix, not a workaround for the test: every agent's fallback logic depends on catching exactly `LLMError`, so the boundary that guarantees that has to be enforced at more than one layer.
- **RAG didn't need a vector database to be genuinely useful here.** Policy Coverage's corpus is a handful of clause chunks per policy (coverage grant, exclusions, conditions) — a hashing-trick bag-of-words embedding in pure Python (`mcp_server/rag.py`, ~40 lines, no numpy) is enough to retrieve the right exclusion clause for a query like "was racing when the loss occurred." This keeps the POC's dependency footprint exactly where it was (still just `fastapi`/`pydantic`/`httpx`/`anthropic`) instead of adding `chromadb` the way `claims-multiagent-rag-poc` did for its larger, cross-policy retrieval problem — a reminder that "add RAG" doesn't always mean "add a vector database," especially when the corpus per query is small and known in advance (here, scoped to one `policy_id` at a time, never a cross-policy search).

## Phase 3 implementation note

The Case Resolution Router needs to resume a claim at a *specific* stage — LangGraph's usual mechanism for that is a persisted checkpoint plus a `thread_id`, resumed later. This POC doesn't need cross-process resume (a claim is fully resolved synchronously within one `resume_claim()` call, same as Phase 0/1/2), so `build_graph(entry_point)` instead compiles a fresh `StateGraph` starting at whichever stage the router picked, reusing the same eight node functions every time rather than the same compiled graph object. This is a deliberate, scoped-down substitute for real LangGraph checkpointing — noted here rather than silently presented as the same thing, since a production version of this pattern (a claim genuinely paused for hours or days awaiting a human, resumed by a different process) would need the real checkpoint/thread_id mechanism this POC intentionally didn't build.

## Implementation status

- [x] `mcp_server/` — JSON-RPC `/mcp` endpoint, 4 tools (`get_policy_coverage`, `record_ledger_decision`, `get_audit_trail`, `create_payment`), static internal service token, scope names aligned with `claims-mcp-oauth-poc`/`claims-partner-api-mcp-poc`
- [x] `claims_workflow.ledger.DecisionLedger` and the policy-coverage/payment agents rewired to call MCP tools via a thin client (`claims_workflow/mcp_client.py`) instead of direct dict access
- [x] All 26 existing tests pass against the MCP-backed implementation, no behavior change (verified by re-running the full suite unmodified except `tests/conftest.py`'s reset fixture, which now resets the MCP server's store instead of a local dict)
- [x] Phase 2: Fraud Triage / Fraud Scoring / Policy Coverage (RAG) / adverse-action-letter drafting as real LLM-backed agents with heuristic fallback — each dispatches on `llm_client.is_available()`, falls back to its unchanged ADR-008 heuristic (tagged `-fallback-after-llm-error` in `model_version`) on any `LLMError`
- [x] Policy Coverage's RAG path: a dependency-light hashing-trick embedding (`mcp_server/rag.py`, pure Python, no vector DB) over a small per-policy clause corpus (`mcp_server/policy_documents.py`, including exclusion clauses the flat `MOCK_POLICIES` dict can't express) — retrieved via a new `search_policy_documents` MCP tool (scope `policy.read`, reused, not new)
- [x] `tests/eval/` — 5 eval-marked tests exercising the real LLM path (`pytest -m eval`, auto-skipped without `ANTHROPIC_API_KEY`); 14 additional non-eval tests in `tests/test_llm_fallback.py` monkeypatch `llm_client._call_anthropic` directly to test JSON-parsing, dispatch, and fallback-on-error without a real key — 40 tests total, all passing (`pytest.ini`: `addopts = -m "not eval"` keeps eval tests out of the default run)
- [x] Phase 3: LangGraph `StateGraph` supervisor (`claims_workflow/graph/supervisor_graph.py`) replacing `pipeline.py`'s hand-written branch-jumping — same 8 agent functions as graph nodes, conditional edges reproduce the exact same control flow, verified against the full 40-test suite plus a manual submit→escalate→resume run
- [ ] Phase 4 (not scheduled): `claims-mcp-oauth-poc` Authorization Server wired in front of `mcp_server/` for real third-party access

## Related

- [ADR-006: Claims MCP OAuth POC — real auth, not a placeholder](006-claims-mcp-oauth-poc-real-auth.md) — source of the OAuth/two-wall recommendation this ADR applies
- [ADR-007: Claims Partner API MCP POC — full API coverage, auth deferred](007-claims-partner-api-mcp-poc-full-coverage.md) — source of the "align scope names now, wire auth later" combination pattern
- [ADR-008: Claims Workflow v2 POC](008-claims-workflow-v2-poc.md) — the Phase-0 implementation this ADR deepens
- [pocs/claims-workflow-v2-poc/](../../pocs/claims-workflow-v2-poc/)
- [pocs/claims-mcp-oauth-poc/](../../pocs/claims-mcp-oauth-poc/) — Authorization Server this design reuses for Phase 4
- [pocs/claims-multiagent-rag-poc/](../../pocs/claims-multiagent-rag-poc/) — LangGraph supervisor and RAG patterns this design reuses for Phase 2/3
- `xingai-enterprise-ai-design` [Orchestrator vs MCP Gateway](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-06-13-orchestrator-vs-mcp-gateway.md) — source of the "supervisor is not an MCP server" constraint on Phase 3
- `xingai-enterprise-ai-design` [Third-Party MCP Access: API Key or OAuth 2.1?](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-15-third-party-mcp-auth-api-key-vs-oauth2.md) — the generalized decision framework this ADR's auth reasoning was distilled into
