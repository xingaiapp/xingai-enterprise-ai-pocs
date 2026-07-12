# References

## XingAI Design Docs

- EN: [How MCP Works in Production: A Deep Dive from Robinhood Trading MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-11-mcp-in-production-robinhood-case.md)
- 中文: [生产环境里 MCP 如何真正运转：以 Robinhood Trading MCP 为实战深潜](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-11-mcp-in-production-robinhood-case.zh.md)
- EN: [MCP Auth — The Robinhood Deep Dive](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- 中文: [从 Robinhood MCP 看懂 MCP 认证：新手也能读懂的行业最佳实践](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.zh.md)
- EN: [Build an OAuth 2.1 + PKCE MCP Project from Scratch — Complete Runnable Lab](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md) — this POC's direct code source
- 中文: [从零搭建 OAuth 2.1 + PKCE MCP 项目：完整可跑通实验](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.zh.md)
- EN: [Orchestrator vs MCP Gateway](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-06-13-orchestrator-vs-mcp-gateway.md)
- 中文: [Orchestrator vs MCP Gateway](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-06-13-orchestrator-vs-mcp-gateway.zh.md)
- EN: [Agent Governance Reference Architecture](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-05-agent-governance-reference-architecture.md)
- 中文: [Agent 治理参考架构](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-05-agent-governance-reference-architecture.zh.md)

## Real-World Implementation This Pattern Is Drawn From

- [xingai-robinhood-mcp](https://github.com/xingaiapp/xingai-robinhood-mcp) — [ADR-001: MCP Gateway Proxy](https://github.com/xingaiapp/xingai-robinhood-mcp/blob/main/docs/adr/001-mcp-gateway-proxy.md) (G1–G7 execution gates), [ADR-002](https://github.com/xingaiapp/xingai-robinhood-mcp/blob/main/docs/adr/002-g3-data-freshness-wired.md), [ADR-003](https://github.com/xingaiapp/xingai-robinhood-mcp/blob/main/docs/adr/003-g2-step-up-wired-single-user.md), [ADR-004](https://github.com/xingaiapp/xingai-robinhood-mcp/blob/main/docs/adr/004-signal-watcher-draft-not-autotrade.md)

## This Repo

- [docs/adr/003-mcp-gateway-placeholder-policy.md](../../docs/adr/003-mcp-gateway-placeholder-policy.md) — see this POC's [enterprise-mapping.md](./enterprise-mapping.md) for how it relates to (and differs from) that ADR's placeholder rules
- [pocs/claims-multiagent-rag-poc/](../claims-multiagent-rag-poc/) — sibling POC; shares synthetic policy numbers `POL-1001`/`POL-2002`/`POL-3003`

## Standards and Specifications

- [RFC 6749 — The OAuth 2.0 Authorization Framework](https://www.rfc-editor.org/rfc/rfc6749)
- [RFC 7636 — Proof Key for Code Exchange (PKCE)](https://www.rfc-editor.org/rfc/rfc7636)
- [RFC 7519 — JSON Web Token (JWT)](https://www.rfc-editor.org/rfc/rfc7519)
- [RFC 7517 — JSON Web Key (JWK)](https://www.rfc-editor.org/rfc/rfc7517)
- [RFC 7591 — Dynamic Client Registration Protocol](https://www.rfc-editor.org/rfc/rfc7591)
- [RFC 7009 — OAuth 2.0 Token Revocation](https://www.rfc-editor.org/rfc/rfc7009)
- [RFC 8414 — OAuth 2.0 Authorization Server Metadata](https://www.rfc-editor.org/rfc/rfc8414)
- [RFC 9728 — OAuth 2.0 Protected Resource Metadata](https://www.rfc-editor.org/rfc/rfc9728)
- [OAuth 2.1 (draft)](https://oauth.net/2.1/) — folds PKCE-mandatory and implicit-grant-removed into the base spec
- [Model Context Protocol specification](https://modelcontextprotocol.io/)
- Robinhood [Agentic Trading overview](https://robinhood.com/us/en/support/articles/agentic-trading-overview/) — the real-world system this POC's source case study documents

## Insurance Domain Context (informational only, not legal/compliance advice)

- Settlement authority tiers and straight-through-processing limits are a standard adjuster-authority concept in P&C claims handling; this POC's `MAX_SETTLEMENT_USD` and `ALLOWED_CLAIM_TYPES` are illustrative constants, not calibrated to any real carrier's actual authority matrix or any state's regulatory requirements.
- Audit-retention and consent-record requirements vary by state insurance regulator; consult your compliance team before using any part of this pattern against real claims data.
