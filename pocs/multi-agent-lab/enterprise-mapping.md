# POC → Enterprise Platform Mapping

This document maps **Phase 1 Multi-Agent Lab** components to the **XingAI Enterprise Agent Platform** roadmap.

## Positioning

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
   Current POC ← you are here (MVP Validation Layer)
```

## Component Mapping

| Enterprise Platform Concept | Phase 1 POC Implementation | Phase 2+ Target |
|---|---|---|
| User Interface | HTML workspace at `GET /` | Web, Mobile, Teams, Slack |
| Orchestrator Agent | `agents/orchestrator.py` | Enterprise Brain with intent + planning |
| Specialist Agents | Research, Product, Tech, Critic | + Security, Compliance, Data, DevOps, Support, Finance, HR |
| MCP Layer | `fake_research_tool` (simulated) | MCP Registry → Jira, GitHub, ServiceNow, SharePoint |
| Tool Gateway | `tools/cache_tool.py` | Policy-enforced MCP gateway |
| Governance / Audit | SQLite `trace_logs` | Long-retention audit store |
| Observability | Trace timeline + `/demo/metrics` | Metrics, alerts, dashboards |
| Memory | Research cache (SQLite) | Session + User + Enterprise vector/SQL stores |
| Event Bus | Not in V1 (sync pipeline) | `pocs/event-bus-ai-review/` |
| Auth / RBAC | Not in V1 | Enterprise Auth → Orchestrator → App Identity |
| Multi-tenant | Not in V1 | Tenant isolation + policy per tenant |

## Agent Lifecycle (Implemented in POC)

```text
Request
   ↓
Intent Detection        ← Orchestrator reads user goal
   ↓
Planning                ← Orchestrator logs handoff plan
   ↓
Agent Selection         ← Research → Product → Tech → Critic
   ↓
Tool Calls              ← fake_research_tool, cache_tool, OpenAI
   ↓
Result Validation       ← Critic Agent
   ↓
Aggregation             ← Orchestrator synthesis
   ↓
Response                ← Final Answer + Trace
```

## UI Mapping (Mockup → POC)

| Mockup Panel | POC Status |
|---|---|
| New Request + Goal | ✅ Product Ideation goal + Run |
| Execution Timeline | ✅ Agent Trace Timeline |
| Final Output (Result / Summary / Artifacts) | ✅ Result + Summary tabs |
| Sidebar: Agents | ✅ Registry view (Phase 1 agents active) |
| Sidebar: Tools (MCP) | 🔜 Phase 2 placeholder |
| Sidebar: Knowledge | 🔜 Phase 2 (cache = minimal memory) |
| Sidebar: Events | 🔜 Phase 3 (event-bus-ai-review POC) |
| Observability Metrics | ✅ `/demo/metrics` |
| Governance / Audit | ✅ Trace = audit log for demo |

## What to Tell the Team

1. **Same architecture, more agents later** — we are not rebuilding; we are extending.
2. **Trace is governance** — what leadership needs for trust starts here.
3. **MCP comes next** — agents never touch systems directly in production.
4. **POC validates orchestration** — the hardest conceptual leap for non-agent audiences.
