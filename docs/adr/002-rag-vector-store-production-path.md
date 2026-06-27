# ADR-002: RAG Vector Store — POC Chroma to Production Path

**Date:** 2026-06-27  
**Status:** Accepted  
**Author:** Xing @ XingAI  
**Supersedes:** —  
**Superseded by:** —  
**Also available:** [中文](002-rag-vector-store-production-path.zh.md)

## Context

[Claims Multi-Agent RAG POC](../../pocs/claims-multiagent-rag-poc/) uses **local ChromaDB** with file-based persistence and optional OpenAI embeddings (offline hash fallback for CI). This is correct for demos — zero infra, readable code.

Enterprise reviewers ask: *what changes for production insurance or compliance RAG?* We need a repo-level ADR so POCs do not silently assume Chroma in prod.

## Decision

### 1. POC default (unchanged)

| Layer | POC choice |
|-------|------------|
| Vector store | Chroma `PersistentClient`, `.cache/chroma` |
| Embeddings | OpenAI `text-embedding-3-small` when key set; hash fallback offline |
| Collections | Separate per domain (policy / history / regulations — never mixed) |
| Citations | Every chunk: `document_id`, `chunk_id`, similarity |

### 2. Production path (documented, not built in POC)

| Requirement | Production target |
|-------------|-------------------|
| HA / multi-instance | Managed vector DB (Pinecone, Weaviate, pgvector on RDS) |
| Encryption | At-rest + TLS in transit; customer-managed keys for regulated tenants |
| PII | Field-level redaction before embed; separate collections per data class |
| Retention | TTL + legal hold flags on source documents |
| Audit | Log every query: trace_id, collection, top-k ids, no raw PII in logs |
| Embeddings | Hosted model with contract; no third-party embed of raw PII without DPA |

**Interface rule:** Retrieval agent accepts an abstract `VectorStoreClient` — POC implements Chroma; production swaps implementation without changing agent prompts or citation schema.

### 3. When to migrate off Chroma

Trigger **any** of:

- Multi-tenant isolation required
- >500k chunks or >50 concurrent query QPS
- Compliance review requires managed SOC2 vector host
- Cross-region replication needed

Until then, Chroma on a single worker volume is acceptable for **internal** staging only — not customer production.

### 4. MCP / ingestion (production extension)

POC uses synthetic markdown. Production adds:

- PDF/email intake → chunk pipeline (not in POC)
- MCP **read** tools for policy admin systems before any write MCP
- Human review queue for documents entering the vector store

## Alternatives considered

- **Pinecone in POC** — rejected (infra friction for demos).
- **Single mixed collection** — rejected (cross-domain retrieval noise; violates ADR-001 citation discipline).
- **Embed without citation metadata** — rejected.

## Consequences

Positive: POC stays simple; sales/engineering share one production checklist.  
Tradeoff: abstraction layer deferred until second POC needs it — acceptable while Claims POC is the only RAG demo.

## Implementation status

- [x] ADR-002 documented
- [x] Claims POC Chroma + hash fallback
- [ ] `VectorStoreClient` interface extraction
- [ ] Pinecone adapter stub in docs only

## Related

- [ADR-001: Supervisor, audit, human-in-the-loop](./001-supervisor-audit-human-in-the-loop.md)
- [Claims POC architecture](../../pocs/claims-multiagent-rag-poc/architecture.md)
