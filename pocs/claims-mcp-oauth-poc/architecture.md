# Architecture

## Components

| Component | Responsibility | Port |
|-----------|-----------------|------|
| `auth_server/` | OAuth 2.1 Authorization Server: metadata discovery, PKCE verification, JWT issuance, refresh rotation, revocation | 8000 |
| `mcp_server/` | Claims MCP Server: JSON-RPC 2.0 `/mcp` endpoint, token verification, two-wall authorization, the four claims tools | 8001 |
| `client/` | Claims adjuster-assist agent: discovery, PKCE flow, token storage/refresh, tool calls | runs on operator's machine, no fixed port |

## Why three separate processes, not one

Mirrors the real trust boundary a production deployment has: the carrier's Identity Provider (`auth_server`) is a different system, run by a different team, with different security requirements (holds the signing key) than the claims system's MCP wrapper (`mcp_server`, holds only the *public* key, never issues tokens itself). Collapsing them into one process for the demo would hide exactly the boundary this POC exists to demonstrate.

## Request flow (happy path)

```text
1. client → POST /mcp (no token)               →  mcp_server
2. mcp_server → 401 + WWW-Authenticate           →  client
3. client → GET .well-known/oauth-protected-resource/mcp  →  mcp_server
4. client → GET .well-known/oauth-authorization-server     →  auth_server
5. client generates PKCE verifier + challenge (local, no network)
6. client → GET /authorize?...&code_challenge=... (opens browser)  →  auth_server
7. human clicks Allow                                        →  auth_server
8. auth_server → 302 redirect w/ authorization code           →  client (loopback callback server)
9. client → POST /token (code + verifier)                     →  auth_server
10. auth_server verifies PKCE, issues JWT access + refresh token
11. client → POST /mcp tools/call (Bearer JWT)                →  mcp_server
12. mcp_server verifies signature (via JWKS) + scope (wall #1) + policy (wall #2)
13. mcp_server → tool result                                   →  client
```

Steps 1–10 happen once per session (or once per token expiry + refresh). Steps 11–13 repeat per tool call.

## The two-wall authorization model

```text
                    ┌─────────────────────────────┐
Request             │  Wall #1: OAuth Scope        │
"call submit_       │  mcp_server/auth.py          │
 claim_decision"  →  │  Does the JWT carry          │  → 403 if missing
                    │  claims.adjudicate?           │
                    └──────────────┬────────────────┘
                                   │ passed
                    ┌──────────────▼────────────────┐
                    │  Wall #2: Agent Policy         │
                    │  mcp_server/policies.py        │
                    │  - Is this claim in the        │  → 403 if any fail
                    │    AI-assist queue?            │
                    │  - Is the claim type allowed?  │
                    │  - Is the amount ≤ authority?  │
                    └──────────────┬────────────────┘
                                   │ passed
                    ┌──────────────▼────────────────┐
                    │  Review → Adjudicate            │
                    │  mcp_server/tools.py            │
                    │  - review_id single-use         │
                    │  - idempotency_key dedup         │
                    │  - no mutable args at submit     │
                    └─────────────────────────────────┘
```

Wall #1 answers *"is this agent allowed to call this tool at all"* — a property of the OAuth grant, checked once per request against the token. Wall #2 answers *"should this specific claim, this specific amount, go through"* — a property of the claim itself and the agent's settlement authority, re-evaluated on every call regardless of what the token says. A token with `claims.adjudicate` scope proves the agent passed wall #1; it says nothing about wall #2.

## Data flow — what's real vs. simulated

| Layer | Real in this POC | Simulated |
|-------|-------------------|-----------|
| OAuth 2.1 protocol (PKCE, JWT, JWKS, discovery) | ✅ real crypto, real HTTP round-trips | — |
| Claim files, policy coverage | — | ✅ in-memory fixtures (`mcp_server/policies.py`) |
| Settlement authority policy | ✅ real check, real refusal | uses a made-up dollar figure, not a calibrated one |
| Audit trail | — | ✅ not implemented at all yet — see README "Not Production Yet" |
| Persistence | — | ✅ everything is an in-memory `dict`, lost on restart |

## Related

- [README.md](./README.md) — Quick Start, API, demo script
- [flow.mmd](./flow.mmd) — Mermaid sequence diagram
- [docs/mcp-auth-deep-dive.md](./docs/mcp-auth-deep-dive.md) — protocol-level explanation of every step above
