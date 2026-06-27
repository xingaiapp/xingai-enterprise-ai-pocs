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
| FastAPI (Phase 5) | API gateway + auth |
| Human Review node | Human-in-the-loop approval queue |

**Positioning:** Phase 1 validation of multi-agent RAG + governance patterns before productizing for insurance clients.
