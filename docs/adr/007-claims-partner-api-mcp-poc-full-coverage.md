# ADR-007: Claims Partner API MCP POC — Full API Coverage, Auth Deferred

**Date:** 2026-07-13
**Status:** Accepted
**Author:** Xing @ XingAI
**Also available:** [中文](007-claims-partner-api-mcp-poc-full-coverage.zh.md)

## Context

[ADR-006](006-claims-mcp-oauth-poc-real-auth.md) added `claims-mcp-oauth-poc`: a real OAuth 2.1 + PKCE + JWT Authorization Server in front of a Claims MCP Server, deliberately scoped to **4 narrow tools** (`get_claim`, `get_policy_coverage`, `review_claim_decision`, `submit_claim_decision`) so the auth protocol itself — not tool breadth — was the thing under test.

That leaves a genuinely separate, unanswered design question this repo hadn't yet demonstrated: when a claims business wants **every** third-party partner integration point exposed through MCP — not just the adjudication workflow, but claim intake, status history, notes, document evidence, policy lookup, claimant management, and settlement payments — does a single MCP server holding comprehensive read/write coverage across all of that stay coherent, or does it need to be split, gated, or deferred until narrower slices are proven first?

This is a recognized tradeoff in MCP server design generally: balance comprehensive API endpoint coverage against a small set of specialized workflow tools; when the calling agents' actual usage pattern is still unknown, comprehensive coverage gives them the most flexibility to compose operations themselves. `claims-mcp-oauth-poc` took the workflow-tools side of that tradeoff (by necessity — it was proving auth, not coverage). Nothing in this repo had yet taken the other side and shown it working end to end.

## Decision

**Add `pocs/claims-partner-api-mcp-poc/` as a new POC that wraps a full claims-business OpenAPI contract (`claims-api-openapi.yaml`, 18 endpoints across 7 domains) as a single TypeScript MCP server with 18 corresponding tools — and that it deliberately ships with no third-party authentication layer in front of it, deferring that to a follow-up phase rather than blocking full API coverage on auth being solved first.**

This is a scope split, the same shape as ADR-006's relationship to ADR-003:

| This POC covers | `claims-mcp-oauth-poc` covers |
|---|---|
| Comprehensive API-to-MCP tool coverage: full CRUD across claims, status, notes, documents, policies, claimants, payments | A narrow, deliberately-scoped 4-tool workflow |
| An OpenAPI contract (`claims-api-openapi.yaml`) as the single source of truth both the MCP server and a runnable mock upstream implement against | Hand-picked tool signatures with no formal API contract behind them |
| No auth layer — single static bearer token, explicitly named as the top "Not Production Yet" item | Real OAuth 2.1 + PKCE + JWT + two-wall authorization (scope + settlement-authority policy) |
| A claim-status state machine enforced in the mock upstream, exercised by an end-to-end test | A Review→Adjudicate split + idempotency, enforced in the MCP server itself |

Neither POC is "more correct" than the other — they prove opposite halves of the same real deployment question. A production third-party claims MCP integration needs **both**: this POC's breadth of coverage, and `claims-mcp-oauth-poc`'s real per-partner authentication, combined into one system (see this POC's `enterprise-mapping.md` for the concrete combination plan: put `claims-mcp-oauth-poc`'s Authorization Server in front of this POC's `mcp-server/`, enforcing the 10 scopes already declared in `claims-api-openapi.yaml`'s `securitySchemes`).

### Why not build both at once

Building comprehensive coverage and real OAuth in the same first POC would have made either one harder to review and demo independently — a reviewer asking "does the auth actually work" would have to wade through 18 tools' worth of business logic, and a reviewer asking "is the API coverage complete and consistent" would have to first understand PKCE and JWT verification. Keeping them as two POCs, explicitly cross-referenced, lets each answer one question cleanly. This mirrors the same reasoning ADR-006 gave for keeping `claims-mcp-oauth-poc` separate from `claims-multiagent-rag-poc`.

### Why the mock upstream is a full Express service, not a placeholder

Per this repo's `POC-STANDARDS.md`, a "Runnable" status label has to be honest. Pointing the MCP server at a non-existent `https://api.claims.example.com` would leave the POC un-runnable, which `claims-mcp-oauth-poc`'s own MOCK_CLAIMS/MOCK_POLICIES precedent already established isn't acceptable — that POC ships in-memory fixtures for exactly this reason. This POC follows the same precedent one level up: since it wraps an *entire* OpenAPI contract rather than four hand-picked functions, the mock has to be a real service implementing every route, not a handful of hardcoded dicts a single Python module can hold.

## Alternatives considered

- **Add the 18 tools directly into `claims-mcp-oauth-poc`** — rejected. That POC's whole point is a narrow, auditable surface behind real auth; growing it to 18 tools would dilute the very thing it's proving and make its own demo script harder to walk.
- **Build the OAuth layer into this POC from the start** — rejected for this phase; see "Why not build both at once" above. Tracked as the natural next step in `enterprise-mapping.md`, not silently skipped.
- **Ship this POC as "Architecture Design Only" until auth is added** — rejected. The API-coverage pattern this POC proves (OpenAPI contract → MCP tool-for-tool mapping, enforced state machine, idempotent money-moving writes) is real and independently testable today; gating its "Runnable" label on an unrelated future auth phase would misrepresent what's actually being demonstrated.

## Consequences

Positive:
- First POC in this repo demonstrating full OpenAPI-contract-to-MCP coverage (18/18 endpoints) rather than a hand-picked tool subset, with a runnable mock upstream and an end-to-end test exercising the full claim lifecycle including an illegal-transition rejection and an idempotent payment retry.
- Gives `claims-mcp-oauth-poc`'s auth pattern a concrete, broader integration target for its natural next phase (see `enterprise-mapping.md`), instead of that pattern staying scoped to 4 tools indefinitely.

Tradeoffs:
- This POC is explicitly **not safe to expose to real third parties as-is** — the single static bearer token is a real gap, not a stylistic simplification, and is called out as the first "Not Production Yet" item precisely so it isn't mistaken for one.
- Two claims-domain MCP POCs (`claims-mcp-oauth-poc`, `claims-partner-api-mcp-poc`) now exist with different languages (Python vs. TypeScript) and different tool counts; a reader has to consult `enterprise-mapping.md` to understand they're complementary halves, not two competing implementations of the same idea.

## Implementation status

- [x] `claims-api-openapi.yaml` — 18-endpoint OpenAPI 3.1 contract across 7 domains
- [x] `mcp-server/` — TypeScript MCP server, Streamable HTTP transport, 18 tools, Zod validation, markdown/JSON dual output, destructive/idempotent annotations
- [x] `mock-api/` — Express mock upstream implementing every endpoint, in-memory fixtures, enforced claim-status state machine
- [x] `tests/e2e.mjs` — end-to-end happy-path test (claimant → claim → coverage check → note → status transitions → illegal-transition rejection → settlement payment with idempotency → status history), run against real live processes
- [x] `docker-compose.yml` wiring both services
- [x] Required POC-STANDARDS.md files: README (EN + 中文), architecture.md, enterprise-mapping.md, flow.mmd, references.md
- [ ] Third-party OAuth 2.1 authentication layer in front of `mcp-server/` (see `enterprise-mapping.md`'s combination plan with `claims-mcp-oauth-poc`) — not started
- [ ] Persistent storage, real audit trail, tenant isolation, rate limiting — see this POC's README "Not Production Yet"

## Related

- [ADR-003: MCP gateway placeholder policy for POCs](003-mcp-gateway-placeholder-policy.md)
- [ADR-006: Claims MCP OAuth POC — real auth, not a placeholder](006-claims-mcp-oauth-poc-real-auth.md)
- [pocs/claims-partner-api-mcp-poc/](../../pocs/claims-partner-api-mcp-poc/) — README, architecture.md, enterprise-mapping.md
- [pocs/claims-mcp-oauth-poc/](../../pocs/claims-mcp-oauth-poc/) — sibling POC this one is missing an auth layer from
- `xingai-enterprise-ai-design` [articles/2026-07-13-mcp-api-coverage-vs-workflow-tools.md](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-13-mcp-api-coverage-vs-workflow-tools.md) — this POC's direct design source
