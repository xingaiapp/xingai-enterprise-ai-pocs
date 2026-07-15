# ADR-008: Claims Workflow v2 POC — Runnable Implementation of the Fraud-Sequencing, Escalation-Routing, and Compliance-Audit Fixes

**Date:** 2026-07-14
**Status:** Accepted
**Author:** Xing @ XingAI
**Also available:** [中文](008-claims-workflow-v2-poc.zh.md)

## Context

`xingai-enterprise-ai-design`'s article [Redesigning the Agentic Claims Workflow](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-14-claims-workflow-redesign-fraud-routing-audit.md) identified three structural gaps in a widely-shared claims-automation infographic and proposed fixes for each: splitting fraud detection into a pre-damage-assessment Triage agent and a post-damage-assessment Scoring agent, replacing a single generic "Human Review & Escalation" box with a Case Resolution Router that resumes at a specific stage, and adding a cross-cutting Compliance & Audit Trail Agent using the same Decision Ledger shape already adopted elsewhere in XingAI.

That article is a design doc, not a proof. This repo already draws a line between the two — `claims-multiagent-rag-poc` is this repo's existing runnable claims pipeline, and it has the *un*-fixed shape: one `Fraud-Check Agent` that runs before damage/cost data exists, and one `Audit Logger` step rather than a cross-cutting ledger every stage writes to. Nothing in this repo had yet shown the three fixes actually working in code — in particular, whether the router's reason-to-re-entry-point mapping holds up once fraud detection is genuinely split into two stages with different data availability.

## Decision

**Add `pocs/claims-workflow-v2-poc/` as a new, dependency-light Python POC that implements all three fixes end to end, with one test module per fix plus end-to-end and API tests (26 tests total, all passing).**

Key implementation choices:

- **Two pipeline entry points, not one loop.** `pipeline.py` exposes `submit_claim()` (runs to settlement/denial/first escalation) and `resume_claim()` (Router-directed re-entry). This models the real pause-for-human boundary explicitly rather than threading an optional `human_decision` parameter through a single function.
- **The router's key had to grow.** The article's routing table is keyed on `(reason, outcome)`. Implementing it against a genuinely two-stage fraud pipeline surfaced a case the article's table doesn't disambiguate: a `fraud_investigation` escalation cleared by a human needs to resume at *different* stages depending on whether Triage or Scoring raised it (Triage-stage clearance still needs Damage Assessment + Fraud Scoring to run; Scoring-stage clearance can skip straight to Policy Coverage). `agents/router.py` keys on `(reason, stage, outcome)` instead. This is a refinement the design doc didn't anticipate, found by building it — see the POC README's "Lessons Learned".
- **No LLM calls, no external services.** Fraud Triage and Fraud Scoring are deterministic heuristic rules (velocity/tenure thresholds; cost-anomaly ratio + a photo-forensics boolean), and `MOCK_POLICIES` is a 3-entry in-memory fixture — same "runnable but not production" precedent as `claims-mcp-oauth-poc`'s `MOCK_CLAIMS`. This keeps the POC runnable with zero API keys and its test suite deterministic, and keeps the demonstration focused on the *sequencing/routing/audit* architecture rather than model quality.
- **The ledger doubles as the adverse-action-letter and fairness-audit source**, not just a log. `DecisionLedger.adverse_action_letter()` reads the specific denying row's `policy_clause`; Fraud Triage and Fraud Scoring pin distinct `model_version` strings specifically so a flagged decision traces back to the model that produced it.

## Alternatives considered

- **Retrofit `claims-multiagent-rag-poc` in place** instead of adding a new POC — rejected. That POC's whole value is being Phase-1-complete evidence for the supervisor/RAG/citation pattern; splitting its one `Fraud-Check Agent` into two and replacing its `Audit Logger` step would change what that POC is proving, not just add to it. Per `POC-STANDARDS.md`'s "each POC should prove one architecture pattern" rule, this belongs in its own POC.
- **Ship this as "Architecture Design Only"** (extend the design article with a more detailed routing table, no code) — rejected once the stage-aware router requirement surfaced; that finding is itself evidence the fixes needed to be built, not just further diagrammed, to be trusted.
- **Reuse `claims-partner-api-mcp-poc`'s TypeScript/OpenAPI approach** instead of a plain Python package — rejected; this POC's subject is agent sequencing and routing logic, not API-surface coverage, and a small in-process Python pipeline is easier to unit-test stage-by-stage (see `tests/`) than a service wrapping an external contract.

## Consequences

Positive:

- First runnable proof that the three fixes from the design article are implementable as described, with the router's stage-aware requirement caught by writing the code and tests rather than staying a latent gap in the design doc.
- `tests/test_fraud_sequencing.py`, `test_router.py`, and `test_audit_trail.py` are effectively executable specifications of the three fixes — a future claims POC (or a real implementation) can be checked against the same assertions.
- Establishes a concrete "Fraud Triage vs. Fraud Scoring" model-versioning pattern (`fraud-triage-heuristic-v1` / `fraud-scoring-heuristic-v1`) other risk-scoring POCs in this repo can follow for fairness-audit traceability.

Tradeoffs:

- Two claims-domain pipeline POCs now exist in this repo (`claims-multiagent-rag-poc`, `claims-workflow-v2-poc`) with overlapping but not identical shapes; `enterprise-mapping.md` in the new POC explicitly cross-references this to avoid the two being read as competing rather than sequential (v2 supersedes v1's fraud/escalation/audit stages specifically, not the RAG/citation pattern v1 also demonstrates).
- The router's fraud-detection-stage-awareness adds a dimension of state (`escalation.stage`) the original design article's table didn't have — anyone reading the article next to the code needs the POC README's "Lessons Learned" note to understand why they differ.
- Still no authentication layer, same gap as `claims-partner-api-mcp-poc` before ADR-007 combined it with `claims-mcp-oauth-poc`'s auth model; tracked in this POC's README "Not Production Yet", not silently skipped.

## Implementation status

- [x] `claims_workflow/` package — 9 agents, `DecisionLedger`, two-entry-point `pipeline.py`
- [x] `claims_workflow/api/main.py` — FastAPI wrapper, 6 endpoints
- [x] `tests/` — 26 tests: `test_fraud_sequencing.py` (Fix 1), `test_router.py` (Fix 2), `test_audit_trail.py` (Fix 3), `test_pipeline_e2e.py` (end-to-end + API), all passing
- [x] `docker-compose.yml` + `Dockerfile`
- [x] Required POC-STANDARDS.md files: README (EN + 中文), architecture.md, enterprise-mapping.md, flow.mmd, references.md
- [ ] Authentication/authorization layer — not started, see `claims-mcp-oauth-poc` for the reference pattern
- [ ] Persistent storage for claims/ledger/settlements — not started
- [ ] Real ML models for Fraud Triage / Fraud Scoring — not started, heuristics only

## Related

- [ADR-006: Claims MCP OAuth POC — real auth, not a placeholder](006-claims-mcp-oauth-poc-real-auth.md)
- [ADR-007: Claims Partner API MCP POC — full API coverage, auth deferred](007-claims-partner-api-mcp-poc-full-coverage.md)
- [pocs/claims-workflow-v2-poc/](../../pocs/claims-workflow-v2-poc/) — README, architecture.md, enterprise-mapping.md
- [pocs/claims-multiagent-rag-poc/](../../pocs/claims-multiagent-rag-poc/) — the earlier single-fraud-check pipeline this POC's design supersedes for fraud/escalation/audit
- `xingai-enterprise-ai-design` [articles/2026-07-14-claims-workflow-redesign-fraud-routing-audit.md](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-14-claims-workflow-redesign-fraud-routing-audit.md) — this POC's direct design source
- `xingai-learn` ADR-003: Decision Ledger Adoption — the same ledger shape reused here
