# Enterprise Platform Mapping

| POC component | Enterprise Agent Platform (future) |
|----------------|-------------------------------------|
| `auth_server/` (demo Authorization Server) | Real carrier IdP — Okta / Auth0 / Azure AD B2C, or a hardened homegrown Authorization Server |
| `mcp_server/` (Claims MCP Server) | MCP wrapper in front of a real Policy Administration / Claims Management system (Guidewire ClaimCenter, Duck Creek Claims, homegrown) |
| `client/` (adjuster-assist agent) | Real agent runtime (the thing that actually reasons about a claim and decides what to call) — this POC's `client/main.py` is a scripted stand-in, not a reasoning agent |
| `mcp_server/policies.py` wall #2 | Central Agent Policy service, one profile per agent deployment / branch office, sourced from a real authority matrix instead of two hardcoded constants |
| Idempotency store (`mcp_server/tools.py`) | Distributed idempotency store (Redis) shared across MCP Server replicas — an in-process dict breaks the moment there's more than one instance |
| (not built) | Append-only audit trail meeting state insurance-regulator retention requirements |
| (not built) | Consent record store — queryable, revocable, per (user, client, scope) |

## Relationship to ADR-003 (MCP Gateway Placeholder Policy)

[ADR-003](../../docs/adr/003-mcp-gateway-placeholder-policy.md) governs every other POC in this repo: until `mcp-tool-gateway/` ships, POCs use **read** MCP stubs or mocked responses, and **write** tools only log `WOULD_CALL` — a simulated governance preview, not real MCP auth.

This POC is different on purpose. It doesn't implement the cross-domain *routing and policy* gateway ADR-003 describes (that's still Phase 2, still not built, still correctly out of scope here) — it implements the *authentication protocol* underneath any future gateway: OAuth 2.1 + PKCE + JWT + scope + a two-wall policy model, all real, all tested against live servers. When `mcp-tool-gateway/` is eventually built, it should sit *in front of* an MCP server shaped like this one's `mcp_server/`, not reinvent token verification itself — this POC is the reference for what that verification layer should look like, ported into a domain (claims) that has real regulatory and settlement-authority stakes rather than a generic tool-routing demo.

**Positioning:** first runnable proof that XingAI's Robinhood-derived MCP auth pattern (`xingai-robinhood-mcp` ADR-001) is domain-general — the same crypto and the same two-wall model, applied to claims adjudication instead of equity trading, with zero changes to the underlying protocol code.
