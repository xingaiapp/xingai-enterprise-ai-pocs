# Claims Partner API MCP POC

> **Status: Runnable · Phase 1**

**Pattern:** Wrap an existing claims-business REST API comprehensively — full read/write coverage across claim intake, status, notes, documents, policy coverage, claimants, and settlement payments — as a single MCP server, so third-party AI agents (partner repair shops, claimant-facing apps, broker tools) integrate against one standard tool interface instead of a bespoke client per partner.

**中文：** [README.zh.md](./README.zh.md)

---

## What This Proves

That an existing (or newly-specified) claims-business REST API can be exposed to third-party AI agents through a **single MCP server with comprehensive endpoint coverage** — 18 tools spanning 7 domains, each with Zod-validated inputs, markdown/JSON dual output, and read/write annotations — rather than a narrow set of hand-picked workflow tools. This is the opposite design point from this repo's sibling [`claims-mcp-oauth-poc`](../claims-mcp-oauth-poc/), which proves real OAuth 2.1 + PKCE authentication in front of a deliberately narrow 4-tool surface. This POC proves the API-coverage side of that tradeoff; **it does not yet have an auth layer in front of it** — see "Not Production Yet".

## Enterprise Pattern

- **OpenAPI contract first** — [`claims-api-openapi.yaml`](./claims-api-openapi.yaml) is the source of truth; both the MCP server's tool schemas and the mock upstream's routes are written against it, not against each other
- **Full CRUD coverage, not just a workflow slice** — claim create/read/update, status transitions, notes, document upload, policy coverage checks, claimant registration, and settlement payments are all exposed, so a third-party agent isn't blocked waiting for "one more tool" to be added
- **Idempotency on money-moving writes** — `claims_create_payment` always sends an `Idempotency-Key`; a retried call returns the original payment instead of creating a second one (verified in `tests/e2e.mjs` step 8)
- **Explicit state machine** — the mock API enforces legal claim-status transitions (e.g. `approved → under_review` is rejected) so illegal writes fail loudly instead of corrupting claim state
- **Destructive-operation annotations** — `claims_transition_status` and `claims_create_payment` are the two tools annotated `destructiveHint: true`; every other tool is read-only or additive
- **Runnable without a real carrier system** — `mock-api/` is a small Express service implementing the same OpenAPI contract with in-memory fixtures, so this POC runs end-to-end with `docker compose up` and no external dependency

## Not Production Yet

- **No third-party authentication in front of this MCP server.** `mcp-server/` calls the upstream Claims API with a single static `CLAIMS_API_TOKEN` — fine for one internal caller, not safe to hand to multiple external partners who each need their own revocable credential. The fix is already built in this repo: front this server with the OAuth 2.1 + PKCE + JWT + scope pattern from [`claims-mcp-oauth-poc`](../claims-mcp-oauth-poc/), enforcing the scopes already defined in `claims-api-openapi.yaml`'s `securitySchemes` (`claims.read`, `claims.write`, `claims.adjudicate`, `documents.read`, `documents.write`, `policies.read`, `claimants.read`, `claimants.write`, `payments.read`, `payments.write`) per tool, before the handler runs.
- **`mock-api/` is in-memory, single-process.** Every claim, note, document, and payment is a JS `Map`; a restart wipes all state. Production needs a real Policy Administration / Claims Management system (Guidewire ClaimCenter, Duck Creek Claims, homegrown) behind the same OpenAPI contract.
- **No audit trail.** Nothing records which third party called which tool against which claim — required for a regulated claims business before any real deployment.
- **No rate limiting or per-partner quotas.** One noisy or compromised partner can currently exhaust the same capacity as every other partner.
- **No tenant isolation.** There is no concept of "partner A can only see claims routed to partner A" — every tool call can reach every claim in the mock store.
- **Document uploads aren't really stored.** `mock-api`'s `downloadUrl` is a fabricated signed-looking URL; no object storage backs it.
- **See [ADR-007](../../docs/adr/007-claims-partner-api-mcp-poc-full-coverage.md)** for the design tradeoff this POC deliberately makes (full API coverage now, auth layer deferred to a follow-up phase) and how it relates to [ADR-003](../../docs/adr/003-mcp-gateway-placeholder-policy.md)'s POC placeholder rules.

## Architecture

```text
Third-Party AI Agent
     │
     │ POST /mcp  (JSON-RPC 2.0: tools/list, tools/call)
     ▼
Claims MCP Server (mcp-server/, :3000)
     │  18 tools across 7 domains — Zod validation, markdown/JSON output,
     │  destructive/idempotent annotations
     │  Bearer token → Claims API (single static token, no per-partner auth yet)
     ▼
Claims Mock API (mock-api/, :4000)
     │  Implements claims-api-openapi.yaml — in-memory claims/policies/
     │  claimants/notes/documents/payments, enforces the claim-status
     │  state machine
     ▼
(Production: a real Claims/Policy Administration system, same contract)
```

Full sequence diagram: [flow.mmd](./flow.mmd). Component responsibilities: [architecture.md](./architecture.md).

## Quick Start

```bash
cd pocs/claims-partner-api-mcp-poc
docker compose up --build
```

This starts `mock-api` on `:4000` and `mcp-server` on `:3000`, wired together (`mcp-server`'s `CLAIMS_API_BASE_URL` points at `mock-api` inside the compose network).

Without Docker, run each service in its own terminal:

```bash
# Terminal 1
cd mock-api && npm install && npm run build && PORT=4000 npm start

# Terminal 2
cd mcp-server && npm install && npm run build
CLAIMS_API_BASE_URL=http://localhost:4000 CLAIMS_API_TOKEN=mock-dev-token TRANSPORT=http PORT=3000 npm start
```

Then run the end-to-end happy-path script (claimant → claim → coverage check → note → status transitions → illegal-transition rejection → settlement payment → status history):

```bash
cd tests && node e2e.mjs
```

Expected output ends with `All checks passed.`

## API

18 MCP tools wrapping the 18 endpoints in [`claims-api-openapi.yaml`](./claims-api-openapi.yaml):

| Domain | Tools |
|---|---|
| Claims | `claims_list_claims`, `claims_create_claim`, `claims_get_claim`, `claims_update_claim` |
| Status | `claims_transition_status`, `claims_list_status_history` |
| Notes | `claims_list_notes`, `claims_add_note` |
| Documents | `claims_list_documents`, `claims_upload_document`, `claims_get_document` |
| Claimants | `claims_create_claimant`, `claims_get_claimant` |
| Policies | `claims_get_policy`, `claims_check_policy_coverage` |
| Payments | `claims_list_payments`, `claims_create_payment`, `claims_get_payment` |

`claims_transition_status` and `claims_create_payment` are annotated `destructiveHint: true`; every other tool is `readOnlyHint: true` or a non-destructive additive write (create claim/claimant/note/document).

Full tool-level docs (args, return shape, error handling) live in each tool's `description` field in `mcp-server/src/tools/*.ts` — call `tools/list` against the running server to see them rendered, or read the source directly.

## Team Demo Script

1. `curl http://localhost:3000/mcp` with no body → shows the JSON-RPC endpoint is up; run `tools/list` and count 18 tools across 7 domains. *"One MCP server, the whole claims API surface — not four hand-picked tools."*
2. Run `tests/e2e.mjs` and narrate step 7 out loud: an approved claim rejects a transition back to `under_review`. *"The mock backend enforces the same state machine a real claims system would — illegal writes fail loudly, not silently."*
3. Run `tests/e2e.mjs` a second time and point at step 8 (payment issuance) if you re-use the same idempotency key manually via `curl` — a repeated call returns the same `paymentId` instead of a second payment. *"A network retry from a flaky agent can't double-pay a claim."*
4. Open `README.md`'s "Not Production Yet" and read the first bullet aloud: no third-party auth yet. Then open [`claims-mcp-oauth-poc`](../claims-mcp-oauth-poc/)'s README side-by-side. *"These two POCs are the two halves of one real deployment: broad API coverage from this one, real OAuth scope enforcement from that one."*

## Lessons Learned

- The first draft of `mock-api`'s payment endpoint moved the claim to `in_payment` without recording a `StatusEvent` — the OpenAPI spec's own description says "the claim moves to `in_payment` on success," but the implementation silently skipped logging *why*. `tests/e2e.mjs` step 10 (assert exactly 3 status events) caught this immediately: it returned 2 instead of 3 on the first real run. Fixed by emitting a `StatusEvent` from the payments route too, with a reason referencing the payment ID. Lesson: any code path that changes `claim.status` needs to go through the same audit-trail append, not just the dedicated status-transition endpoint — easy to miss when a second endpoint (payments) also happens to flip status as a side effect.
- Background service processes started with `&` inside one shell tool call do not survive into a *separate* tool call in this environment — each call is an independent shell. The `e2e.mjs` run only succeeded once both `mock-api` and `mcp-server` were started **and** the test script ran inside the *same* shell invocation. Worth calling out explicitly in Quick Start (three separate persistent terminals, or one `docker compose up` process) rather than assuming "start it in the background and come back later" works in every environment.
- Deriving the MCP server's Zod schemas and the mock API's Express routes from the *same* `claims-api-openapi.yaml` file by hand (not via codegen) meant a couple of near-misses — e.g. `claims_check_policy_coverage`'s `claimType` needed loose substring matching against the mock's `coverages` keys (`"glass"` vs `"auto_glass"`) since the OpenAPI spec never pins down exactly how claim types map to coverage bucket names. A real Phase 2 should either codegen both sides from the OpenAPI file or add an explicit claim-type-to-coverage-bucket mapping table instead of string-matching.

## Related Design Docs

- EN: [MCP API Coverage vs. Workflow Tools: A Claims Partner Integration Case Study](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-13-mcp-api-coverage-vs-workflow-tools.md)
- 中文: [MCP 全量 API 覆盖 vs 工作流工具：一个理赔第三方对接案例](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-13-mcp-api-coverage-vs-workflow-tools.zh.md)
- EN: [How MCP Works in Production: A Deep Dive from Robinhood Trading MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-11-mcp-in-production-robinhood-case.md)
- 中文: [生产环境里 MCP 如何真正运转](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-11-mcp-in-production-robinhood-case.zh.md)
- Sibling POC: [`claims-mcp-oauth-poc`](../claims-mcp-oauth-poc/) — real OAuth 2.1 + PKCE + JWT auth this POC is missing; see this POC's [enterprise-mapping.md](./enterprise-mapping.md) for how the two combine

## Disclaimer

This POC is for **informational and educational** purposes. It is **not** production-ready insurance or claims software.

- Code, docs, and examples are provided **"as is"** with no warranty.
- You are responsible for security, compliance, deployment, and outcomes if you reuse any of this.
- Following this POC does **not** create a professional, legal, or compliance relationship with XingAI.
- Consult qualified professionals for regulated decisions.
