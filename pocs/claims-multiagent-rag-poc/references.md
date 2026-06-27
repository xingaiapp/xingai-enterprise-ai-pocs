# References — Claims Multi-Agent RAG POC

## XingAI ADRs & Platform

- [Enterprise POC ADR-001: Supervisor, audit, human-in-the-loop](../../docs/adr/001-supervisor-audit-human-in-the-loop.md) · [中文](../../docs/adr/001-supervisor-audit-human-in-the-loop.zh.md)
- [Enterprise Agent Platform](../../docs/ENTERPRISE-AGENT-PLATFORM.md) · [中文](../../docs/ENTERPRISE-AGENT-PLATFORM.zh.md)
- [POC Standards](../../docs/POC-STANDARDS.md)
- Invest AI [ADR-028: Robinhood MCP execution gates](https://github.com/xingaiapp/xingai-invest-ai/blob/main/docs/adr/028-robinhood-mcp-execution-gates.md) — parallel human-in-the-loop pattern for finance

## Tech blog

- [Claims Multi-Agent RAG POC](https://github.com/xingaiapp/xingai-tech-blog/blob/main/posts/2026-06-25-claims-multiagent-rag-supervisor-poc.md) · [中文](https://github.com/xingaiapp/xingai-tech-blog/blob/main/posts/2026-06-25-claims-multiagent-rag-supervisor-poc.zh.md)
- [MCP architecture best practices](https://github.com/xingaiapp/xingai-tech-blog/blob/main/posts/2026-06-03-mcp-architecture-best-practices.md)

## External

- [LangGraph documentation](https://langchain-ai.github.io/langgraph/)
- [ChromaDB](https://docs.trychroma.com/) — local vector store for POC; production path: Pinecone / Weaviate
- [Anthropic structured outputs](https://docs.anthropic.com/en/docs/build-with-claude/structured-outputs)

## Production path (not built in POC)

- PDF/email intake parsers
- Field-level encryption and retention policies
- Real claims admin system (CTABS-class) integration via MCP read tools first
