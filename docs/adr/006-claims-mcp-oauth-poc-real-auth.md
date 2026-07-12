# ADR-006: Claims MCP OAuth POC — Real Auth, Not a Placeholder

**Date:** 2026-07-12
**Status:** Accepted
**Author:** Xing @ XingAI
**Also available:** [中文](006-claims-mcp-oauth-poc-real-auth.zh.md)

## Context

[ADR-003](003-mcp-gateway-placeholder-policy.md) set the rule every POC in this repo has followed since: until `mcp-tool-gateway/` ships, POCs use **read** MCP stubs or mocked responses, and **write** tools only log `WOULD_CALL` — a simulated governance preview, not real MCP auth (P1–P5 rules).

That rule is correct for what it governs: cross-domain tool *routing and policy* (which agent role may call which domain prefix — `sharepoint.*`, `jira.create_*`, etc.), which genuinely doesn't exist yet and shouldn't be faked per-POC.

It does not cover a narrower, separately real question: **what does the *authentication protocol* underneath any future gateway actually look like, end to end, with real cryptography, against a real regulated domain?** `xingai-robinhood-mcp` (a sibling XingAI repo, not part of this POC collection) already answered that question for equity trading — a shipped, tested, production-shaped MCP gateway with OAuth-adjacent execution gates (G1–G7). A companion educational lab (`xingai-enterprise-ai-design/guides/2026-07-12-mcp-oauth-pkce-lab.md`) wrote the full OAuth 2.1 + PKCE + JWT protocol implementation as a teaching artifact, for the same brokerage domain.

The gap: nothing in `xingai-enterprise-ai-pocs` demonstrated that pattern **runnable**, and nothing showed it generalizing past brokerage to this repo's actual flagship domain — insurance claims, per `claims-multiagent-rag-poc`.

## Decision

**Add `pocs/claims-mcp-oauth-poc/` as a new POC that ports the OAuth 2.1 + PKCE + JWT lab verbatim in mechanism, re-domained from brokerage to claims adjudication — and that it implements *real* authentication, deliberately outside ADR-003's placeholder scope.**

This is not a contradiction of ADR-003; it's a scope clarification:

| ADR-003 governs | This POC covers |
|---|---|
| Cross-domain tool routing/policy (which agent may call which domain's tools) | The auth protocol underneath any one domain's MCP server |
| Correctly still a placeholder — `mcp-tool-gateway/` doesn't exist | Not a placeholder — real OAuth Server + real MCP Server + real client, tested end to end including one live-server smoke test |
| P1–P5 rules (registry, no silent writes, trace shape, agent isolation, human gate) | A two-wall model (OAuth scope + agent settlement-authority policy) plus Review→Adjudicate — a different, complementary shape for a different layer of the problem |

Domain mapping from the source lab:

| Brokerage (source lab) | Claims (this POC) |
|---|---|
| `portfolio.read` / `quotes.read` / `orders.review` / `orders.place` | `claims.read` / `policy.read` / `claims.review` / `claims.adjudicate` |
| Symbol allowlist + per-order notional cap | Claim-type allowlist + settlement-authority cap (`MAX_SETTLEMENT_USD`) |
| Isolated, separately-funded Agentic brokerage account | Claims explicitly routed into an "AI-assist queue" (`AI_ASSIST_QUEUE_STATUS`) |
| `review_equity_order` → `place_equity_order` | `review_claim_decision` → `submit_claim_decision` |

Same crypto, same protocol flow, same Four-Layer Protection Model — see `docs/mcp-auth-deep-dive.md` in the POC for the full mapping and a from-scratch explanation of every OAuth/PKCE mechanism, written specifically so a reader unfamiliar with OAuth internals can follow the reasoning, not just the code.

## Alternatives considered

- **Fold this into `claims-multiagent-rag-poc` directly** — rejected. That POC's pattern (Supervisor + RAG + citations) is a different architectural concern from MCP authentication; conflating them would make both harder to reason about independently. They're linked via `enterprise-mapping.md` and shared synthetic policy numbers instead.
- **Wait for `mcp-tool-gateway/` and build auth as part of it** — rejected. The gateway's job (per ADR-003) is cross-domain routing/policy; it should sit *in front of* an MCP server shaped like this POC's `mcp_server/`, consuming this auth pattern, not reinventing token verification as part of its own scope. Building the auth layer first gives the future gateway a real target to integrate against.
- **Keep this as a design-doc-only guide (no runnable POC)** — rejected; the source lab already exists as a guide in `xingai-enterprise-ai-design`. This repo's whole purpose (per its own README: "A place to test architecture patterns before productizing them") is the runnable, domain-ported version — the guide proves the pattern once; this POC proves it generalizes.

## Consequences

Positive:
- First POC in this repo with real, tested OAuth 2.1 + PKCE + JWT — a concrete reference for what the auth layer under any future domain MCP server (claims, HR, procurement) should look like, not just the brokerage-specific version.
- Closes ADR-003's own noted gap: "Claims RAG POC: retrieval uses local vector store; production path adds MCP read for policy admin before any write MCP" — this POC is exactly that missing MCP read/write layer, now demonstrated (not yet wired into the RAG POC itself — see Implementation status).

Tradeoffs:
- Two POCs (`claims-multiagent-rag-poc`, `claims-mcp-oauth-poc`) now both touch "claims" without being integrated with each other yet — a reader has to consult `enterprise-mapping.md` in the new POC to understand they're complementary, not competing demos of the same thing.
- This POC's `MAX_SETTLEMENT_USD` / `ALLOWED_CLAIM_TYPES` are illustrative constants, not calibrated to any real carrier's authority matrix — same disclosed-limitation pattern the source lab already used for its notional cap, carried forward honestly rather than presented as domain expertise this repo doesn't have.

## Implementation status

- [x] `auth_server/`, `mcp_server/`, `client/` — full OAuth 2.1 + PKCE + JWT + JWKS + Review→Adjudicate + idempotency, ported from the source lab
- [x] `mcp_server/policies.py` — claims-domain two-wall model (settlement authority, claim-type allowlist, AI-assist-queue isolation)
- [x] 33 tests (auth server, MCP auth/scope, claim flow) — all passing
- [x] One live end-to-end smoke test against real running servers (full PKCE exchange + tool calls), not just mocked-auth tests
- [x] `docs/mcp-auth-deep-dive.md` (EN + 中文) — protocol-level explanation tied to this POC's code
- [x] Required POC-STANDARDS.md files: README (EN + 中文), architecture.md, enterprise-mapping.md, flow.mmd, references.md
- [ ] Wiring `claims-multiagent-rag-poc`'s Adjudication Agent through this POC's MCP layer instead of calling into claims data directly (noted as a Phase 2 direction in `enterprise-mapping.md`, not started)
- [ ] Persistent storage, real audit trail, real IdP — see the POC's own README "Not Production Yet"

## Related

- [ADR-003: MCP gateway placeholder policy for POCs](003-mcp-gateway-placeholder-policy.md)
- [pocs/claims-mcp-oauth-poc/](../../pocs/claims-mcp-oauth-poc/) — README, architecture.md, enterprise-mapping.md
- [pocs/claims-multiagent-rag-poc/](../../pocs/claims-multiagent-rag-poc/) — sibling claims POC
- `xingai-robinhood-mcp` [ADR-001: MCP Gateway Proxy](https://github.com/xingaiapp/xingai-robinhood-mcp/blob/main/docs/adr/001-mcp-gateway-proxy.md) — the real-world implementation this pattern is drawn from
- `xingai-enterprise-ai-design` [guides/2026-07-12-mcp-oauth-pkce-lab.md](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md) — this POC's direct code source
