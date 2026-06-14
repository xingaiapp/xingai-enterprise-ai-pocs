# XingAI Enterprise Agent Platform Architecture

## From AI Chatbot to Enterprise Digital Workforce

| Field | Value |
|---|---|
| Version | 0.1 |
| Status | Draft |
| Owner | XingAI |
| Audience | Architects, Engineering Managers, CTO, Product Leaders |

---

## Executive Summary

Most organizations are experimenting with AI assistants. A single AI assistant cannot scale across complex enterprise workflows.

XingAI Enterprise introduces an **Agent-Oriented Architecture (AOA)** where specialized AI agents collaborate like human teams.

The platform enables:

- Specialized Agents
- Agent Collaboration
- Tool Integration
- MCP Integration
- Event-Driven Processing
- Enterprise Governance
- Auditability
- Observability

The **Multi-Agent Lab POC** (`pocs/multi-agent-lab/`) is the **MVP Validation Layer** — the first runnable milestone of this architecture.

```text
Today:   Multi-Agent POC  (Phase 1)
Tomorrow: XingAI Enterprise Agent Platform
```

---

## Vision

Transform AI from:

```text
Question → Answer
```

into:

```text
Goal → Planning → Agent Collaboration → Tool Execution → Decision → Action
```

---

## Enterprise Reference Architecture

```text
┌─────────────────────────────┐
│        User Interface       │
│ Web │ Mobile │ Teams │ Slack│
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│     Orchestrator Agent      │
│     Enterprise Brain        │
└──────────────┬──────────────┘
               │
 ┌─────────────┼───────────────┐
 ▼             ▼               ▼
Research     Product       Support
Agent        Agent         Agent
 ▼             ▼               ▼
Tech         Data         Security
Agent        Agent        Agent
 └─────────────┼───────────────┘
               ▼
┌─────────────────────────────┐
│         MCP Layer           │
│ Internal / External Tools   │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│     Enterprise Systems      │
│ APIM · CRM · SharePoint     │
│ ServiceNow · Jira · GitHub  │
│ SAP · Databases             │
└─────────────────────────────┘
```

---

## Core Concepts

### Agent

An agent is an AI worker with: **Role**, **Goal**, **Instructions**, **Tools**, **Memory**.

### Orchestrator

The orchestrator is the team lead. It understands intent, plans execution, selects agents, routes work, combines outputs, and returns the final response.

Without an orchestrator → chaos. With an orchestrator → coordinated AI workforce.

### Agent Lifecycle

```text
Request → Intent Detection → Planning → Agent Selection
      → Tool Calls → Result Validation → Aggregation → Response
```

---

## Orchestrator vs MCP Gateway

![Orchestrator vs MCP Gateway — Enterprise Agent Platform UX](../assets/orchestrator-vs-mcp-gateway-ux.png)

Teams often ask: *Do we need an **Orchestration MCP** to work with GitHub, Jira, and SharePoint MCPs?*

**No.** At enterprise level you need **two internal systems**, not a third MCP called "Orchestration MCP":

| System | Orchestrates | Is it MCP? | Phase |
|--------|--------------|------------|-------|
| **Orchestrator Agent** | Other **agents** (Research → Product → Tech) | No | Phase 1 — [Multi-Agent Lab](../pocs/multi-agent-lab/) |
| **MCP Gateway** | **Tools** across domain MCP servers | Gateway may expose one MCP API inward | Phase 2 — `mcp-tool-gateway` (planned) |
| **Domain MCPs** | One enterprise system each (GitHub, Jira, SharePoint…) | Yes | Phase 2+ |

```text
Workflow orchestration  →  Orchestrator Agent
Tool orchestration      →  MCP Gateway
System integration      →  Domain MCP servers
```

**Security path:**

```text
User → Auth → Orchestrator Agent → Specialist Agent → MCP Gateway → Domain MCP → Enterprise System
```

**Do not:** let agents call many MCPs directly, or build an "Orchestration MCP" that runs the whole workflow.

**Example trace (gateway deny teaches governance):**

```text
[1] Orchestrator Agent     · plan handoffs
[2] Research Agent         · sharepoint.search_documents
[3] MCP Gateway            · ALLOW  · sharepoint.*
[4] SharePoint MCP         · result
[5] Tech Agent             · jira.create_issue
[6] MCP Gateway            · DENIED · Tech Agent may not use jira:*
[7] Tech Agent             · github.search_code
[8] MCP Gateway            · ALLOW  · github.*
[9] GitHub MCP             · result
[10] Orchestrator Agent    · final answer
```

Full 5W write-up, examples, and anti-patterns:

- EN: [Orchestrator vs MCP Gateway](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-06-13-orchestrator-vs-mcp-gateway.md)
- 中文: [Orchestrator 与 MCP Gateway](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-06-13-orchestrator-vs-mcp-gateway.zh.md)

---

## POC → Platform Mapping

| Phase 1 (Current POC) | Phase 2+ (Enterprise Platform) |
|---|---|
| 4 specialist agents | Agent Registry (Research, Product, Security, Compliance, Data, DevOps, Support, Finance, HR…) |
| SQLite trace logs | Audit store + observability pipeline |
| fake_research_tool | MCP Layer → SharePoint, Jira, GitHub, ServiceNow |
| Synchronous pipeline | Event Bus + async agent workers |
| Single-tenant demo | Multi-tenant RBAC |
| Session-only | Session + User + Enterprise memory layers |

See [`pocs/multi-agent-lab/enterprise-mapping.md`](../pocs/multi-agent-lab/enterprise-mapping.md).

---

## MCP Layer

Agents should not directly access enterprise systems. Route all tool calls through the **MCP Gateway** (see [Orchestrator vs MCP Gateway](#orchestrator-vs-mcp-gateway) above).

```text
Agent → MCP Gateway → Domain MCP → Enterprise Resource
```

Benefits: security, standardization, auditability, replaceability.

---

## Event-Driven Architecture (Phase 3)

```text
New Incident → Event Bus → Support Agent
                        → Root Cause Agent
                        → Reporting Agent
                        → Notification Agent
```

Each agent reacts independently.

---

## Enterprise Memory (Phase 2–3)

| Layer | Scope |
|---|---|
| Session Memory | Current conversation |
| User Memory | Preferences, roles, projects |
| Enterprise Memory | Knowledge base, policies, SOPs, lessons learned |

---

## Governance

Every action must be traceable:

```text
Request ID · Agent · Input · Output · Tool Used · Duration · Timestamp
```

The POC demonstrates this via the **Agent Trace Timeline**.

---

## Security Model

```text
User → Enterprise Auth → Orchestrator → App Identity → MCP
```

Prefer service principals + policy enforcement over agents using user credentials.

---

## Roadmap

| Phase | Scope |
|---|---|
| **Phase 1** | Multi-Agent POC — 4 agents, SQLite, OpenAI, Trace UI |
| **Phase 2** | Agent Platform — Agent Registry, MCP Registry, Memory, Prompt Registry |
| **Phase 3** | Enterprise Platform — Multi-tenant, RBAC, Event Bus, Observability, Agent Marketplace |
| **Phase 4** | Digital Workforce — Autonomous agents, cross-agent collaboration, human approval, continuous learning |

---

## Multi-Agent Lab System Design

![Multi-Agent Lab — Phase 1 System Design UX](../assets/multi-agent-lab-system-design-ux.png)

Phase 1 layered architecture: Demo Client → FastAPI → **Orchestrator Agent** → Research / Product / Tech / Critic → simulated tools (`fake_research_tool`, `cache_tool`, OpenAI) → SQLite (`trace_logs`, governance). Trace timeline on the right shows one full request. See [Multi-Agent Lab POC](../pocs/multi-agent-lab/).

---

## Relationship Diagram

```text
XingAI Enterprise
        │
        ▼
Enterprise Agent Platform
        │
        ▼
   Orchestrator
   ┌────┼────┐
Research Product Tech Critic
        │
        ▼
   Current POC (Phase 1 MVP Validation)
```

---

## Demo Narrative for Leadership

> Today's POC is not a toy project. It is the minimum runnable validation of the XingAI Enterprise Agent Platform. Future enterprise agents, MCP gateways, event buses, memory layers, and governance will all build on the same Orchestrator + Specialized Agents architecture.

---

## Related Documents

- [Multi-Agent Lab POC](../pocs/multi-agent-lab/README.md)
- [POC Standards](./POC-STANDARDS.md)
- EN: [Orchestrator vs MCP Gateway](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-06-13-orchestrator-vs-mcp-gateway.md)
- 中文: [Orchestrator 与 MCP Gateway](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-06-13-orchestrator-vs-mcp-gateway.zh.md)
- EN: [Enterprise AI Decision Systems](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-06-07-enterprise-ai-decision-systems.md)
- 中文: [从 AI 演示到企业 AI 决策系统](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-06-07-enterprise-ai-decision-systems.zh.md)
