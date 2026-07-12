# Enterprise Platform Mapping

| POC component | Enterprise Agent Platform (future) |
|---------------|-----------------------------------|
| Supervisor (LangGraph) | Orchestrator service + workflow registry |
| Intake Agent | Document extraction specialist |
| Retrieval Agent | RAG / knowledge retrieval layer |
| Fraud-Check Agent | Risk scoring specialist |
| Adjudication Agent | Decision specialist with citation policy |
| Audit Logger | Immutable audit trail / compliance store |
| ChromaDB (local) | Managed vector DB (Pinecone, enterprise search) |
| FastAPI (Phase 5) | API gateway + auth — see [Claims MCP OAuth POC](../claims-mcp-oauth-poc/) for a runnable reference of the "+ auth" half (real OAuth 2.1 + PKCE + JWT, not yet wired into this POC's API) |
| Human Review node | Human-in-the-loop approval queue |

**Positioning:** Phase 1 validation of multi-agent RAG + governance patterns before productizing for insurance clients.

**Related POC:** [Claims MCP OAuth POC](../claims-mcp-oauth-poc/) demonstrates real OAuth 2.1 + PKCE authentication and a two-wall (scope + settlement-authority) authorization model for claims adjudication, using this POC's `POL-1001`/`POL-2002`/`POL-3003` synthetic policy numbers for narrative continuity. A Phase 2 direction: route this POC's Adjudication Agent through that POC's MCP layer instead of writing directly to claim/decision data — see [ADR-006](../../docs/adr/006-claims-mcp-oauth-poc-real-auth.md).
