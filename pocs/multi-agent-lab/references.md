# References — Multi-Agent Lab

## XingAI Design Docs

- EN: [Orchestrator vs MCP Gateway](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-06-13-orchestrator-vs-mcp-gateway.md)
- 中文: [Orchestrator 与 MCP Gateway](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-06-13-orchestrator-vs-mcp-gateway.zh.md)
- EN: [From AI Demos to Enterprise AI Decision Systems](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-06-07-enterprise-ai-decision-systems.md)
- 中文: [从 AI 演示到企业 AI 决策系统](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-06-07-enterprise-ai-decision-systems.zh.md)
- [Enterprise AI architecture diagrams](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/assets/ARCHITECTURE-DIAGRAMS.md)
- UX diagram: [Orchestrator vs MCP Gateway](../../docs/assets/orchestrator-vs-mcp-gateway-ux.png)

## External References

- [OpenAI Agents SDK — Handoffs](https://openai.github.io/openai-agents-python/handoffs/)
- [OpenAI Agents SDK — Tracing](https://openai.github.io/openai-agents-python/tracing/)

## Related XingAI Products

Patterns in this POC mirror production-style orchestration in:

- `xingai-founder` — daily brief orchestrator + specialist agents
- `xingai-learn` — decision pipeline + cache-first inputs

## V1 Scope Boundaries

Intentionally excluded from this POC:

- MCP gateways
- Vector databases
- Real-time web crawling
- Async worker queues
- Enterprise auth / tenant isolation
