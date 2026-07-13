# References

## XingAI Design Docs

- EN: [MCP API Coverage vs. Workflow Tools: A Claims Partner Integration Case Study](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-13-mcp-api-coverage-vs-workflow-tools.md) — this POC's direct design source
- 中文: [MCP 全量 API 覆盖 vs 工作流工具：一个理赔第三方对接案例](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-13-mcp-api-coverage-vs-workflow-tools.zh.md)
- EN: [How MCP Works in Production: A Deep Dive from Robinhood Trading MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-11-mcp-in-production-robinhood-case.md)
- 中文: [生产环境里 MCP 如何真正运转](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-11-mcp-in-production-robinhood-case.zh.md)
- EN: [Build an OAuth 2.1 + PKCE MCP Project from Scratch — Complete Runnable Lab](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md) — the auth layer this POC is missing, built for the sibling POC
- 中文: [从零搭建 OAuth 2.1 + PKCE MCP 项目](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.zh.md)

## Tech Blog

- EN: [Full API Coverage First: A Claims Partner MCP POC](https://github.com/xingaiapp/xingai-tech-blog/blob/main/posts/2026-07-13-claims-partner-api-mcp-poc-full-coverage-first.md)
- 中文: [先做全量覆盖：一个理赔第三方 MCP POC](https://github.com/xingaiapp/xingai-tech-blog/blob/main/posts/2026-07-13-claims-partner-api-mcp-poc-full-coverage-first.zh.md)

## This Repo

- [docs/adr/007-claims-partner-api-mcp-poc-full-coverage.md](../../docs/adr/007-claims-partner-api-mcp-poc-full-coverage.md) — the design tradeoff this POC makes and its relationship to ADR-003
- [pocs/claims-mcp-oauth-poc/](../claims-mcp-oauth-poc/) — sibling POC; see this POC's [enterprise-mapping.md](./enterprise-mapping.md) for how the two combine
- [pocs/claims-multiagent-rag-poc/](../claims-multiagent-rag-poc/) — another sibling POC; this POC's seed data reuses the same `POL-1001`/`POL-2002`/`POL-3003` policy numbers and claimant names as `claims-mcp-oauth-poc`'s fixtures, for narrative continuity across the three claims-domain POCs in this repo

## Standards and Specifications

- [OpenAPI Specification 3.1](https://spec.openapis.org/oas/v3.1.0) — the contract format `claims-api-openapi.yaml` is written against
- [Model Context Protocol specification](https://modelcontextprotocol.io/) — tool definitions, JSON-RPC 2.0 message shape, Streamable HTTP transport
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification) — the wire protocol under every `/mcp` request in this POC

## Insurance Domain Context (informational only, not legal/compliance advice)

- `claims-api-openapi.yaml`'s claim types, coverage structures, and settlement flow are illustrative, generic P&C claims concepts, not calibrated to any real carrier's actual product line, state filing, or regulatory requirements.
- Document retention, consent, and audit requirements for a real third-party claims integration vary by state insurance regulator; consult your compliance team before using any part of this pattern against real claims data.
