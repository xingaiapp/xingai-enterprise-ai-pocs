# Enterprise Platform Mapping

| POC component | Enterprise Agent Platform (future) |
|---|---|
| `claims_workflow/graph/supervisor_graph.py` | Orchestrator service + workflow registry, with real checkpointed human-in-the-loop pause/resume (this POC's graph rebuilds per call instead — see ADR-009) |
| Fraud Triage Agent (LLM + heuristic fallback) | Real-time risk-signal service (identity, velocity graph), model-version-pinned per decision |
| Fraud Scoring Agent (LLM + heuristic fallback) | Cost-anomaly / photo-forensics ML model, versioned and pinned per decision |
| Policy Coverage Agent (RAG + heuristic fallback) | Policy administration system integration with real document retrieval, not a 3-entry fixture |
| `mcp_server/rag.py` + `policy_documents.py` | Managed vector search over the real policy document corpus (Pinecone/Weaviate — see `claims-multiagent-rag-poc`'s production path for the same tradeoff) |
| Case Resolution Router | Human-in-the-loop approval queue + routing policy engine |
| `mcp_server/` (JSON-RPC `/mcp`, static service token) | MCP Gateway with real OAuth 2.1 — see [claims-mcp-oauth-poc](../claims-mcp-oauth-poc/) and the [API-key-vs-OAuth2 design article](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-15-third-party-mcp-auth-api-key-vs-oauth2.md) |
| `DecisionLedger` | Immutable audit trail / compliance store (see `xingai-engineering-system/patterns/decision-ledger-schema.md`) |
| `adverse_action_letter.draft_letter()` | Regulatory notice generation service, templated per jurisdiction |
| `mcp_server/store.py` settlements | Payments ledger with real idempotency-key enforcement — see [claims-partner-api-mcp-poc](../claims-partner-api-mcp-poc/) |
| FastAPI `_CLAIMS` dict | Claim state store — see [claims-partner-api-mcp-poc](../claims-partner-api-mcp-poc/)'s claim-status state machine for the production shape |

**Positioning:** this POC is the runnable counterpart to the
`xingai-enterprise-ai-design` article that first proposed these three
fixes on paper. It exists to prove the fixes are actually implementable as
described, not just diagrammable — every claim in the article's "Fix 1/2/3"
sections has a corresponding test in `tests/`.

**Related POCs:**

- [claims-partner-api-mcp-poc](../claims-partner-api-mcp-poc/) — the idempotent-payment and claim-status-state-machine patterns this POC's Payment Agent follows
- [claims-mcp-oauth-poc](../claims-mcp-oauth-poc/) — the auth layer a production version of this API would sit behind (this POC ships with no auth, same "Not Production Yet" precedent)
- [claims-multiagent-rag-poc](../claims-multiagent-rag-poc/) — the earlier single-fraud-check, single-audit-step version of a claims pipeline; this POC is what that pipeline's fraud/escalation/audit stages look like once the three gaps are fixed
