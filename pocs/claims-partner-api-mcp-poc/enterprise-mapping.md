# Enterprise Platform Mapping

| POC component | Enterprise Agent Platform (future) |
|----------------|-------------------------------------|
| `claims-api-openapi.yaml` | The carrier's real, published partner API contract — this file is a plausible-but-illustrative stand-in, not a real carrier's spec |
| `mock-api/` | A real Policy Administration / Claims Management system (Guidewire ClaimCenter, Duck Creek Claims, homegrown) exposing the same contract |
| `mcp-server/` | The same MCP server, unchanged in shape, pointed at a real `CLAIMS_API_BASE_URL` instead of `mock-api` |
| `mcp-server`'s single static `CLAIMS_API_TOKEN` | A real OAuth 2.1 + PKCE + JWT authentication layer, one scoped credential per third-party partner — see "Relationship to `claims-mcp-oauth-poc`" below |
| (not built) | Per-partner rate limiting and usage quotas |
| (not built) | Tenant isolation — which partner may see/act on which subset of claims |
| (not built) | Append-only audit trail: which partner, which tool, which claim, what outcome |
| (not built) | Real object storage behind `claims_upload_document` / `claims_get_document`'s `downloadUrl` |

## Relationship to ADR-003 (MCP Gateway Placeholder Policy)

[ADR-003](../../docs/adr/003-mcp-gateway-placeholder-policy.md) governs *cross-domain* tool routing and policy inside multi-agent orchestration POCs (`multi-agent-lab`, `claims-multiagent-rag-poc`) — until `mcp-tool-gateway/` ships, those POCs use read stubs or `WOULD_CALL`-only writes.

This POC is a different kind of thing, the same way `claims-mcp-oauth-poc` is: it **builds a real, single-domain MCP server**, not a multi-agent orchestration demo that calls one. ADR-003's placeholder rules don't apply to it directly. What it *doesn't* have — unlike `claims-mcp-oauth-poc` — is any authentication layer at all in front of that MCP server. See [ADR-007](../../docs/adr/007-claims-partner-api-mcp-poc-full-coverage.md) for why this POC ships broad API coverage first and defers auth to a follow-up phase, rather than building both at once.

## Relationship to `claims-mcp-oauth-poc`

These two POCs are complementary halves of one real third-party deployment, not competing demos of the same thing:

| | This POC (`claims-partner-api-mcp-poc`) | [`claims-mcp-oauth-poc`](../claims-mcp-oauth-poc/) |
|---|---|---|
| Language | TypeScript | Python |
| Tool count | 18, full CRUD across 7 domains | 4, one narrow adjudication workflow |
| Authentication | None yet (single static bearer token) | Real OAuth 2.1 + PKCE + JWT, two-wall authorization |
| Authorization granularity | None (any caller can call any tool) | Per-scope (wall #1) + per-claim settlement-authority policy (wall #2) |
| What it proves | An existing claims API can be wrapped with comprehensive MCP tool coverage | The auth protocol underneath any such MCP server generalizes to a regulated domain |

**A real Phase 2** would take this POC's `mcp-server/` and put `claims-mcp-oauth-poc`'s `auth_server/` in front of it, enforcing the 10 scopes already declared in `claims-api-openapi.yaml`'s `securitySchemes` (`claims.read`, `claims.write`, `claims.adjudicate`, `documents.read`, `documents.write`, `policies.read`, `claimants.read`, `claimants.write`, `payments.read`, `payments.write`) per tool before the handler calls `mock-api` (or a real backend). That phase is *not built* — it's the natural next step, not a claim this POC is making about itself.

**Positioning:** the API-coverage half of a two-POC pair. `claims-mcp-oauth-poc` answers "is the auth protocol real and does it generalize"; this POC answers "can a typical claims business's whole partner-facing API surface be wrapped as MCP tools without the coverage lagging behind the auth work." Together they sketch what a production third-party claims MCP integration needs from both directions.
