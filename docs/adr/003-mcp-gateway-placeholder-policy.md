# ADR-003: MCP Gateway Placeholder Policy for POCs

**Date:** 2026-06-27  
**Status:** Accepted  
**Author:** Xing @ XingAI  
**Supersedes:** —  
**Superseded by:** —  
**Also available:** [中文](003-mcp-gateway-placeholder-policy.zh.md)

## Context

The [Enterprise Agent Platform](../ENTERPRISE-AGENT-PLATFORM.md) separates **Orchestrator Agent** (workflow between specialists) from **MCP Gateway** (tool routing and ALLOW/DENY governance). Phase 1 POCs (`multi-agent-lab`, `claims-multiagent-rag-poc`) run without a real gateway — agents may call tools directly or use registry stubs.

Reviewers ask whether POCs should ship a third **"Orchestration MCP"** or connect agents straight to GitHub/Jira/SharePoint MCP servers. We need a repo-level rule so demos stay honest and Phase 2 `mcp-tool-gateway/` does not fork per POC.

## Decision

### 1. Two internal systems — not a third Orchestration MCP

| System | Orchestrates | MCP? | POC today |
|--------|--------------|------|-----------|
| **Supervisor / Orchestrator** | Specialist **agents** | No | LangGraph in Claims POC; lab orchestrator |
| **MCP Gateway** | Cross-domain **tools** | Gateway may expose MCP internally | **Placeholder** — registry + trace DENY lines only |
| **Domain MCP servers** | One enterprise system each | Yes | Stubs in `MCP_REGISTRY` until real servers |

**Anti-pattern (forbidden in docs and demos):** a monolithic "Orchestration MCP" that runs full multi-agent workflows.

### 2. POC placeholder rules

Until `mcp-tool-gateway/` ships:

| Rule | Requirement |
|------|-------------|
| **P1 Registry** | `MCP_REGISTRY` (or equivalent) lists tool name, domain, `read`/`write`, stub vs live |
| **P2 No silent writes** | POCs use **read** MCP stubs or mocked responses; **write** tools log `WOULD_CALL` only |
| **P3 Trace shape** | Demo traces include a **Gateway** step with `ALLOW` or `DENIED` + agent role — even if simulated |
| **P4 Agent isolation** | Document which agent roles may call which domain prefix (e.g. Research → `sharepoint.*`, Tech → not `jira.create_*`) |
| **P5 Human gate** | High-stakes writes route through [ADR-001](./001-supervisor-audit-human-in-the-loop.md) human review — never gateway auto-approve |

Claims RAG POC: retrieval uses local vector store ([ADR-002](./002-rag-vector-store-production-path.md)); production path adds MCP **read** for policy admin before any write MCP.

### 3. Phase 2 gateway (planned, not in POC code yet)

When implemented under `mcp-tool-gateway/`:

- Central policy engine: agent role × tool pattern × environment
- Append-only audit: trace_id, agent, tool, decision, latency
- Deny by default; explicit allowlists per POC profile (`claims`, `lab`, `hr-stub`)

POCs **must not** embed duplicate gateway logic — migrate stubs to the shared service.

### 4. Security path (target)

```text
User → Auth → Orchestrator → Specialist Agent → MCP Gateway → Domain MCP → Enterprise system
```

POC shortcut (documented in README): Orchestrator → Agent → **stub Gateway trace** → local tool/mock.

## Alternatives considered

- **Agents connect directly to many MCP servers** — rejected for enterprise narrative; no central DENY demo.
- **Build full gateway before any POC** — rejected; blocks Claims demo velocity.
- **Orchestration MCP wrapping LangGraph** — rejected; confuses agent vs tool boundaries.

## Consequences

Positive: sales/engineering tell one story; Phase 2 has a clear migration target; ADR-001 human-in-the-loop stays enforceable.

Tradeoff: gateway behavior is **simulated** in Phase 1 — label demos "governance preview", not production MCP.

## Implementation status

- [x] ADR-003 documented
- [x] `MCP_REGISTRY` in multi-agent-lab
- [ ] Shared `mcp-tool-gateway/` service
- [ ] Claims POC policy-admin MCP read stub

## Related

- [ADR-001: Supervisor, audit, human-in-the-loop](./001-supervisor-audit-human-in-the-loop.md)
- [ADR-002: RAG vector store production path](./002-rag-vector-store-production-path.md)
- [Enterprise Agent Platform](../ENTERPRISE-AGENT-PLATFORM.md)
