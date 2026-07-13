# Architecture

## Components

| Component | Responsibility | Port |
|-----------|-----------------|------|
| `mcp-server/` | Claims MCP Server: JSON-RPC 2.0 `/mcp` endpoint (Streamable HTTP), 18 tools across 7 domains, Zod input validation, markdown/JSON dual output | 3000 |
| `mock-api/` | Stand-in claims/policy administration system: implements every endpoint in `claims-api-openapi.yaml` against in-memory fixtures, enforces the claim status state machine | 4000 |
| `tests/e2e.mjs` | Plain-Node smoke test driving the full happy path through `mcp-server`'s `/mcp` endpoint | n/a |

## Why two separate services, not one

`mcp-server` and `mock-api` are separate processes on purpose, mirroring the real trust boundary: in production, the MCP server is a thin wrapper a platform/integrations team owns, while the claims system behind it is owned by a different team (or is a vendor product like Guidewire ClaimCenter) with its own release cadence, auth, and data store. Collapsing them into one process would hide exactly the seam a third-party integration has to cross — `CLAIMS_API_BASE_URL` is the only thing that changes to point `mcp-server` at a real backend instead of `mock-api`.

## Request flow (happy path)

```text
1. Third-party agent → POST /mcp {method: "tools/call", params: {name: "claims_create_claim", ...}}  → mcp-server
2. mcp-server validates input against the tool's Zod schema
3. mcp-server → POST /claims (Bearer <CLAIMS_API_TOKEN>)                                              → mock-api
4. mock-api validates the Authorization header is present (mock: any non-empty Bearer token), creates
   the claim in-memory, returns 201 + Claim JSON
5. mcp-server renders markdown or returns structuredContent per response_format                       → agent
```

Every one of the 18 tools follows this same three-step shape: validate → call `claimsApiRequest()` (or the direct HTTP call) → render.

## Claim status state machine (enforced in `mock-api/src/statemachine.ts`)

```text
submitted ──────► under_review ──────► approved ──────► in_payment ──────► closed
    │                   │                  │                                  ▲
    └───────► closed ◄──┴──────► denied ───┴──────► closed ◄───── reopened ───┘
                                     │
                                     └──────► reopened ──────► under_review
```

`claims_transition_status` (and `claims_create_payment`, which drives `approved → in_payment` as a side effect) reject any transition not in this map with a 409, naming the claim's current status. This is what `tests/e2e.mjs` step 7 demonstrates (`approved → under_review` refused).

## Data flow — what's real vs. simulated

| Layer | Real in this POC | Simulated |
|-------|-------------------|-----------|
| MCP protocol (JSON-RPC 2.0, tool schemas, Streamable HTTP) | ✅ real `@modelcontextprotocol/sdk` server | — |
| HTTP call from `mcp-server` to `mock-api` (auth header, error mapping, idempotency key) | ✅ real HTTP round-trip | — |
| Claim status state machine | ✅ real enforcement, real 409s | — |
| Claims, policies, claimants, notes, documents, payments data | — | ✅ in-memory fixtures (`mock-api/src/data.ts`) |
| Third-party authentication (OAuth scopes, per-partner tokens) | — | ✅ not implemented — single static bearer token, see README "Not Production Yet" |
| Document storage | — | ✅ `downloadUrl` is a fabricated signed-looking URL, no object storage behind it |
| Audit trail | — | ✅ not implemented at all |

## Related

- [README.md](./README.md) — Quick Start, API, demo script
- [flow.mmd](./flow.mmd) — Mermaid sequence diagram
- [enterprise-mapping.md](./enterprise-mapping.md) — POC component vs. future platform mapping
- [claims-api-openapi.yaml](./claims-api-openapi.yaml) — the OpenAPI contract both services implement against
