# XingAI Enterprise AI POCs

**Version:** 0.7.1

Runnable proof-of-concept projects for enterprise AI decision systems and architecture patterns.

This repository pairs with [xingai-enterprise-ai-design](https://github.com/xingaiapp/xingai-enterprise-ai-design), which explains the architecture patterns. This repo keeps the runnable POCs, reference implementations, experiments, and deployment notes.

## What This Repository Is

- A home for runnable enterprise AI POCs
- A place to test architecture patterns before productizing them
- A reference implementation library for articles in `xingai-enterprise-ai-design`
- A record of tradeoffs, failures, and lessons learned

## What This Repository Is Not

- Not a product repo
- Not a marketing demo collection
- Not production-ready enterprise software
- Not a replacement for product-specific XingAI apps

## POC Index

| POC | Pattern | Status | Related Design Topic |
|---|---|---|---|
| [Multi-Agent Lab](pocs/multi-agent-lab/) | Orchestrator + specialist handoffs | Runnable · Phase 1 MVP | [Enterprise Agent Platform](docs/ENTERPRISE-AGENT-PLATFORM.md) |
| [Claims Multi-Agent RAG](pocs/claims-multiagent-rag-poc/) | Supervisor + RAG + citations + human-in-the-loop | Runnable · Phases 1–6 | Insurance / enterprise RAG demo |
| [Claims MCP OAuth POC](pocs/claims-mcp-oauth-poc/) | Real OAuth 2.1 + PKCE + JWT auth, two-wall authorization, Review→Adjudicate | Runnable · Phase 1 | [MCP in Production](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-11-mcp-in-production-robinhood-case.md), [OAuth PKCE Lab](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md) |
| [Claims Partner API MCP POC](pocs/claims-partner-api-mcp-poc/) | Full OpenAPI-to-MCP tool coverage (18 tools/7 domains), auth deferred | Runnable · Phase 1 | [MCP API Coverage vs. Workflow Tools](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-13-mcp-api-coverage-vs-workflow-tools.md) |
| [Claims Workflow v2 POC](pocs/claims-workflow-v2-poc/) | Split fraud triage/scoring, Case Resolution Router, compliance audit trail; MCP data boundary, LLM agents + RAG, LangGraph supervisor | Runnable · Phase 1+2+3 (ADR-009) | [Redesigning the Agentic Claims Workflow](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-14-claims-workflow-redesign-fraud-routing-audit.md), [Third-Party MCP Auth](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-15-third-party-mcp-auth-api-key-vs-oauth2.md) |
| [Event Bus AI Review](pocs/event-bus-ai-review/) | Event-driven AI decisions | Architecture Design Only | Enterprise AI decision systems |
| Human-in-the-Loop Decision | Approval workflow | Planned | Human approval layers |
| Memory Layer Demo | User + organization memory | Planned | Memory architectures |
| MCP Tool Gateway | Cross-domain tool routing and governance (builds on Claims MCP OAuth POC's auth layer) | Planned | MCP in enterprise AI |

## Repository Structure

```text
pocs/
  multi-agent-lab/
  claims-multiagent-rag-poc/
  claims-mcp-oauth-poc/
  claims-partner-api-mcp-poc/
  claims-workflow-v2-poc/
  event-bus-ai-review/
  human-in-the-loop-decision/
  memory-layer-demo/
  mcp-tool-gateway/
shared/
  schemas/
  docker/
docs/
  adr/                          # Cross-POC ADRs (supervisor, audit, human-in-the-loop)
  ENTERPRISE-AGENT-PLATFORM.md
  ENTERPRISE-AGENT-PLATFORM.zh.md
  CONTRIBUTING.md
  POC-STANDARDS.md
```

## POC Standard

Every POC should answer four questions:

1. What architecture pattern does this prove?
2. What is intentionally missing because this is not production?
3. What did we learn from building it?
4. Which English and Chinese design docs does it support?

See [`docs/POC-STANDARDS.md`](docs/POC-STANDARDS.md) and [`docs/adr/README.md`](docs/adr/README.md).

## Contributing

See [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) for contribution guidelines.

## Version Notes

### 0.7.1

- **Claims Workflow v2 POC: production-readiness gap analysis** — new `PRODUCTION-READINESS.md` (EN + 中文) organizes what's missing before a real pilot across four lenses: AI agent layer (prompt-injection risk on the free-text `loss_description` field, uncalibrated heuristic thresholds, no model risk governance, no LLM cost controls), MCP layer (tool versioning, call resilience, ledger retention), automation/ops (observability, DR, load testing, canary rollout), and claims-industry-specific regulatory concerns not covered by a generic production checklist (prompt-payment law deadlines, SIU/fraud-bureau reporting, jurisdiction-aware adverse-action letters, PII handling around the LLM call, model change management). Linked from the POC's README, `references.md`, and `docs/adr/README.md`.
- **`docs/adr/README.md` correction** — ADR-009's status column updated from "Phase 1+2 done" to "Phase 1+2+3 done" (Phase 3 was completed and documented but the index row was missed at the time).

### 0.7.0

- **Claims Workflow v2 Phase 3: LangGraph supervisor (ADR-009)** — `pipeline.py`'s hand-written `_continue_from_triage`/`_continue_from_coverage`/`_continue_from_approval` branch-jumping is replaced by a `StateGraph` (`claims_workflow/graph/supervisor_graph.py`) built from the same 8 agent functions as nodes. The Case Resolution Router's "resume at a specific stage" requirement is handled by compiling a fresh graph per call starting at the router's chosen entry point, rather than real LangGraph checkpointing — a deliberate, documented scope reduction (a claim is still resolved synchronously within one call, not paused across processes).
- All 40 existing tests pass unmodified against the graph-based implementation; verified with an additional manual submit→escalate→resume run and a `-W error::DeprecationWarning` pass with zero warnings.
- `architecture.md` rewritten to reflect the full Phase 1/2/3 shape (was still describing the ADR-008-only version); `enterprise-mapping.md` updated with the graph, RAG, and MCP-auth-upgrade rows.

### 0.6.0

- **Claims Workflow v2 Phase 2 LLM agents (ADR-009)** — Fraud Triage, Fraud Scoring, Policy Coverage, and adverse-action-letter drafting now run as real Claude-backed agents when `ANTHROPIC_API_KEY` is set, each falling back to its unchanged Phase 1 heuristic (tagged `-fallback-after-llm-error`) on any failure. Policy Coverage's LLM path adds a dependency-light RAG layer (`mcp_server/rag.py`, `mcp_server/policy_documents.py` — pure Python hashing-trick embeddings, no vector DB) that retrieves real clause text including exclusions, so it can deny a claim the flat coverage lookup would call "covered."
- **Claims Workflow v2 POC: 40 tests, zero API keys for the default run** — 14 new tests in `tests/test_llm_fallback.py` monkeypatch the LLM call directly to verify JSON parsing, dispatch, and error fallback; 5 new eval-marked tests in `tests/eval/` exercise the real model and only run with `pytest -m eval` (`pytest.ini`: `addopts = -m "not eval"` keeps them out of the default suite, same pattern `claims-multiagent-rag-poc` uses for its offline-embeddings fallback).
- **New design article: Third-Party MCP Access — API Key or OAuth 2.1?** (`xingai-enterprise-ai-design`, 2026-07-15) — generalizes ADR-006/007/009's auth reasoning into a reusable decision framework, using this repo's three claims MCP POCs as the worked example.

### 0.5.1

- **Claims Workflow v2 Phase 1 MCP boundary (ADR-009)** — policy coverage, decision ledger, and payment settlement move behind `mcp_server/` (JSON-RPC `/mcp` over FastAPI) with four tools; workflow agents call via `mcp_client.py` (in-process ASGI by default). Static internal service token for now; scopes pre-aligned for later OAuth (see third-party MCP auth design article).
- **ADR-009** documents Phase 1 (done) plus planned Phase 2 LLM agents and Phase 3 LangGraph supervisor.

### 0.5.0

- **New POC: Claims Workflow v2 POC** (`pocs/claims-workflow-v2-poc/`) — a runnable Python implementation of the three fixes proposed in `xingai-enterprise-ai-design`'s claims-workflow redesign article: fraud detection split into pre-assessment Triage and post-assessment Scoring agents, a Case Resolution Router that resumes at a specific stage instead of restarting from intake, and a Decision-Ledger-shaped Compliance & Audit Trail every stage writes to — see [ADR-008](docs/adr/008-claims-workflow-v2-poc.md).
- **Claims Workflow v2 POC: 26 tests, one module per fix** — `test_fraud_sequencing.py` proves Triage can't see cost-inflation fraud and Scoring can; `test_router.py` proves every escalation resumes at a specific stage (never intake) and unrecognized outcomes default to a safe deny, not a silent restart; `test_audit_trail.py` proves every stage logs to the ledger and denials produce a clause-citing adverse-action letter.
- **Claims Workflow v2 POC: router had to become stage-aware** — implementing the design article's routing table against a genuinely two-stage fraud pipeline surfaced a case the article didn't disambiguate (a Triage-stage fraud clearance still needs Damage Assessment + Fraud Scoring to run; a Scoring-stage clearance doesn't) — see the POC's "Lessons Learned" and ADR-008.
- **Claims Workflow v2 POC: idempotent payments**, same pattern as Claims Partner API MCP POC — a retried settlement for the same claim returns the original record and logs the replay instead of paying twice.

### 0.4.0

- **New POC: Claims Partner API MCP POC** (`pocs/claims-partner-api-mcp-poc/`) — a TypeScript MCP server exposing a full 18-endpoint claims-business OpenAPI contract (`claims-api-openapi.yaml`) as 18 MCP tools across 7 domains (claims, status, notes, documents, claimants, policies, payments), the API-coverage counterpart to Claims MCP OAuth POC's narrow-tools-plus-real-auth pattern — see [ADR-007](docs/adr/007-claims-partner-api-mcp-poc-full-coverage.md).
- **Claims Partner API MCP POC: runnable mock upstream** — `mock-api/` implements every endpoint in the OpenAPI contract against in-memory fixtures (shared policy numbers/claimant names with Claims MCP OAuth POC for narrative continuity) and enforces the claim-status state machine, so the whole stack runs via `docker compose up` with no external dependency.
- **Claims Partner API MCP POC: idempotent settlement payments** — `claims_create_payment` requires an `Idempotency-Key`; a retried call returns the original payment instead of creating a second one.
- **Claims Partner API MCP POC: end-to-end test** (`tests/e2e.mjs`) — drives the full happy path (claimant → claim → coverage check → note → status transitions → illegal-transition rejection → settlement payment → status history) against the real running services.
- **Claims Partner API MCP POC: explicitly no auth layer yet** — deferred by design per ADR-007; see the POC's `enterprise-mapping.md` for the plan to combine it with Claims MCP OAuth POC's Authorization Server.

### 0.3.0

- **New POC: Claims MCP OAuth POC** (`pocs/claims-mcp-oauth-poc/`) — real OAuth 2.1 + PKCE + JWT Authorization Server and Claims MCP Server, ported from `xingai-enterprise-ai-design`'s brokerage-domain OAuth lab into insurance claims adjudication. First POC in this repo with real (not placeholder-per-ADR-003) authentication — see [ADR-006](docs/adr/006-claims-mcp-oauth-poc-real-auth.md).
- **Claims MCP OAuth POC: two-wall authorization model** — OAuth scope (`claims.read`/`policy.read`/`claims.review`/`claims.adjudicate`) plus an independent agent settlement-authority policy (claim-type allowlist, dollar cap, "AI-assist queue" isolation) in `mcp_server/policies.py`
- **Claims MCP OAuth POC: Review → Adjudicate + idempotency** — `review_claim_decision` drafts and freezes a decision; `submit_claim_decision` only accepts a `review_id` + `idempotency_key`, never mutable business parameters
- **Claims MCP OAuth POC: `docs/mcp-auth-deep-dive.md`** (EN + 中文) — protocol-level walkthrough of PKCE, `state`, discovery, scoped JWTs, and the Four-Layer Protection Model, tied line-by-line to this POC's code
- **Claims MCP OAuth POC: 33 tests** — PKCE, metadata discovery, token exchange/rotation, scope enforcement, settlement-authority policy, idempotency — plus one live end-to-end smoke test against real running servers (not just mocked auth)

### 0.2.0

- **Multi-Agent Lab: error propagation** — `_run_safe()` wrapper catches empty results and exceptions; pipeline surfaces `pipeline_errors` in response instead of silently continuing on failure
- **Multi-Agent Lab: prompts separated** — all system prompts extracted to `agents/prompts.py`; agents import from there rather than embedding strings
- **Multi-Agent Lab: topic-aware research** — `fake_research_tool` returns different fixtures for invest / meal / learn / enterprise / default topics based on user input keywords
- **Multi-Agent Lab: input validation** — `POST /demo/run` rejects inputs over 2000 characters (422)
- **Multi-Agent Lab: rate limiting** — `slowapi` limits `POST /demo/run` to 10 req/min per IP (configurable via `RATE_LIMIT_PER_MINUTE`)
- **Multi-Agent Lab: CORS restricted** — `allow_origins` now reads from `ALLOWED_ORIGINS` env var; no longer `"*"` by default
- **Multi-Agent Lab: structured logging** — Python `logging` wired throughout orchestrator, agents, LLM service, and tools
- **Multi-Agent Lab: LLM request_id** — `chat_json()` accepts `request_id` for log correlation
- **Multi-Agent Lab: configurable cache TTL** — `CACHE_TTL_HOURS` env var (default 24)
- **Multi-Agent Lab: tests** — 30+ pytest tests across cache, research tool, API, and orchestrator; 70% coverage gate
- **Multi-Agent Lab: Dockerfile + docker-compose** — `docker compose up` from `pocs/multi-agent-lab/`
- **Multi-Agent Lab: CI** — GitHub Actions: lint (ruff), test + coverage, security scan (pip-audit)
- **Multi-Agent Lab: Dependabot** — weekly pip updates for backend dependencies
- **Event Bus AI Review: status label** — README now clearly marked "Architecture Design Only"
- **Event Bus AI Review: enterprise-mapping.md** — added POC vs Platform mapping and leadership positioning
- **POC-STANDARDS.md: updated** — `enterprise-mapping.md` now required; status label required; Lessons Learned guidance added

### 0.1.4

- Position Multi-Agent Lab as **Phase 1 MVP Validation Layer** for Enterprise Agent Platform
- Add enterprise architecture docs (EN + 中文)
- Upgrade demo UI to enterprise workspace layout with agent registry and metrics

### 0.1.3

- Add runnable **Multi-Agent Lab** POC (`pocs/multi-agent-lab/`)
- FastAPI demo with Orchestrator + Research/Product/Tech/Critic agents and SQLite trace timeline

### 0.1.2

- Add contribution guidelines for new POCs
- Require contributors to update POC index, version notes, and bilingual design references

### 0.1.1

- Require every POC to reference matching `xingai-enterprise-ai-design` docs in both English and Chinese when available
- Update the Event Bus AI Review placeholder with bilingual design links

### 0.1.0

- Initial repository structure
- POC standards
- First POC placeholders for enterprise AI decision-system patterns

## Related Repositories

- [xingai-enterprise-ai-design](https://github.com/xingaiapp/xingai-enterprise-ai-design) — architecture articles, diagrams, and design patterns
- [xingai-tech-blog](https://github.com/xingaiapp/xingai-tech-blog) — engineering stories and implementation notes
- [xingai-dot-app](https://github.com/xingaiapp/xingai-dot-app) — XingAI marketing site

## Disclaimer

Content in this repository is for **informational and educational** purposes.

- POCs, code, docs, and examples are provided **“as is”** with no warranty.
- They are **not** production-ready enterprise software unless a POC explicitly says otherwise.
- You are responsible for security, privacy, legal, compliance, cost, and operational review before any reuse.
- Following XingAI guidance does **not** create a professional, legal, financial, or compliance relationship.
- Consult qualified professionals for regulated decisions.

## License

Code and docs are owned by XingAI unless a specific POC folder declares a different license.
