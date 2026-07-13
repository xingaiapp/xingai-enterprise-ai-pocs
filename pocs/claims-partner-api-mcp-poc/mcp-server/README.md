# Claims MCP Server

An MCP (Model Context Protocol) server that lets third-party AI agents call
the claims business's REST API — claim intake, status, documents, policy
coverage, claimants, and settlement payments — through a standard tool
interface instead of a bespoke integration per partner.

The API contract this server wraps is documented in
[`../claims-api-openapi.yaml`](../claims-api-openapi.yaml) (OpenAPI 3.1). If
your real backend differs, update that spec first, then adjust
`src/types.ts` and the request paths in `src/tools/*.ts` to match.

## What's Exposed

18 tools across 7 domains, covering the full claim lifecycle end-to-end
(read AND write):

| Domain | Tools |
|---|---|
| Claims | `claims_list_claims`, `claims_create_claim`, `claims_get_claim`, `claims_update_claim` |
| Status | `claims_transition_status`, `claims_list_status_history` |
| Notes | `claims_list_notes`, `claims_add_note` |
| Documents | `claims_list_documents`, `claims_upload_document`, `claims_get_document` |
| Claimants | `claims_create_claimant`, `claims_get_claimant` |
| Policies | `claims_get_policy`, `claims_check_policy_coverage` |
| Payments | `claims_list_payments`, `claims_create_payment`, `claims_get_payment` |

Every tool has a Zod-validated input schema, an explicit description with
usage examples, and annotations (`readOnlyHint`/`destructiveHint`/
`idempotentHint`/`openWorldHint`) so a calling agent (or its host app) can
reason about risk before invoking it — e.g. `claims_transition_status` and
`claims_create_payment` are marked `destructiveHint: true` because they
carry real business/financial effect.

## Quick Start

```bash
npm install
cp .env.example .env   # then fill in CLAIMS_API_BASE_URL / CLAIMS_API_TOKEN
npm run build
npm start               # TRANSPORT=http by default per .env.example
```

Verify it's up:

```bash
curl http://localhost:3000/healthz
curl -X POST http://localhost:3000/mcp \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

For local/desktop MCP clients instead of remote access, set `TRANSPORT=stdio`.

## Third-Party Access Model

This server itself does not implement OAuth — it authenticates to the
**upstream** Claims API using a single `CLAIMS_API_TOKEN`. That's fine for a
first internal deployment, but for real third-party access you almost
certainly want an auth layer **in front of this MCP server** so each partner
authenticates with their own scoped credential rather than sharing one
upstream token. Two ways to get there:

1. **Put this server behind an API gateway / reverse proxy** that terminates
   OAuth2 client-credentials or mTLS per partner, and forwards to `/mcp`.
2. **Add OAuth2.1 + PKCE directly to this MCP server**, following the same
   pattern already built and tested in this workspace at
   `xingai-enterprise-ai-pocs/pocs/claims-mcp-oauth-poc` (Authorization Server
   with `.well-known` metadata discovery, RS256 JWTs, scope-per-tool
   enforcement, and a settlement-authority policy wall independent of OAuth
   scope). That POC is for a different claims business's tech stack, but the
   OAuth/JWT/scope machinery is directly reusable — the main change needed
   here is enforcing per-tool scopes (`claims.read`, `claims.write`,
   `claims.adjudicate`, `documents.read`, `documents.write`, `policies.read`,
   `claimants.read`, `claimants.write`, `payments.read`, `payments.write` —
   already defined in `claims-api-openapi.yaml`'s `securitySchemes`) before
   each tool handler runs.

Either way, **do not ship this to real third parties with a single shared
`CLAIMS_API_TOKEN` and no per-partner auth in front of it** — that gives
every partner the same access level with no ability to revoke one partner
without cutting off all of them.

## Project Structure

```
claims-mcp-server/
├── package.json / tsconfig.json / .env.example
├── src/
│   ├── index.ts          # McpServer setup, stdio + streamable HTTP transports
│   ├── types.ts          # TypeScript interfaces mirroring the OpenAPI schemas
│   ├── constants.ts      # API base URL, timeouts, pagination/char limits
│   ├── schemas/
│   │   └── common.ts     # Shared Zod fields (pagination, response_format, claimId)
│   ├── services/
│   │   ├── api-client.ts # Auth'd HTTP client + error → tool-message mapping
│   │   └── format.ts     # Markdown/JSON rendering, truncation, date/money helpers
│   └── tools/
│       ├── claims.ts
│       ├── status.ts
│       ├── notes.ts
│       ├── documents.ts
│       ├── claimants.ts
│       ├── policies.ts
│       └── payments.ts
└── dist/                 # npm run build output (entry point: dist/index.js)
```

## Design Notes

- **Response formats**: every tool accepts `response_format: 'markdown'|'json'`
  (default markdown) so a human-facing agent gets readable prose while a
  programmatic caller can request the full structured payload.
- **Pagination**: `claims_list_claims` respects `page`/`pageSize` and reports
  `hasMore`/`nextPage` so an agent doesn't have to guess when to stop paging.
- **Character limit**: responses are capped at 25,000 characters
  (`CHARACTER_LIMIT` in `constants.ts`) with a truncation notice telling the
  agent how to narrow the request instead of just cutting output silently.
- **Idempotency**: `claims_create_payment` always sends an `Idempotency-Key`
  header (client-supplied or auto-generated) so a network retry can't
  double-pay a claim; `claims_create_claim` supports an optional
  `idempotencyKey` for the same reason.
- **Destructive vs. safe operations**: `claims_transition_status` and
  `claims_create_payment` are annotated `destructiveHint: true` — the two
  places in this API where a tool call has binding business/financial effect.

## Not Production-Ready Yet

- No auth in front of this MCP server (see "Third-Party Access Model" above) — required before any real third party gets access.
- `src/services/api-client.ts` reads a single static `CLAIMS_API_TOKEN`; production should refresh a real OAuth2 access token instead of a long-lived static one.
- No rate limiting or per-partner usage quotas.
- No structured audit log of who-called-what — needed for a regulated claims business.
- The upstream base URL, error shapes, and field names in `src/types.ts` are placeholders matching `claims-api-openapi.yaml`; confirm against your real backend before pointing `CLAIMS_API_BASE_URL` at it.
