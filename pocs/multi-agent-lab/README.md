# Multi-Agent Lab — XingAI Enterprise Agent Platform

## Phase 1 · MVP Validation Layer

This POC is **not an isolated demo**. It is the minimum runnable validation of the **XingAI Enterprise Agent Platform** architecture.

```text
Today:   Multi-Agent POC (Phase 1)
Tomorrow: XingAI Enterprise Agent Platform
```

> 今天的 POC 不是玩具项目，而是 XingAI Enterprise Agent Platform 的最小可运行验证。

See:

- [Enterprise Agent Platform Architecture](../../docs/ENTERPRISE-AGENT-PLATFORM.md)
- [Enterprise Mapping (POC → Platform)](enterprise-mapping.md)
- [中文架构说明](../../docs/ENTERPRISE-AGENT-PLATFORM.zh.md)

---

## What This Proves

| Enterprise Concept | Phase 1 POC |
|---|---|
| Orchestrator Agent | Plans handoffs, aggregates final answer |
| Specialist Agents | Research, Product, Tech, Critic |
| Tool / MCP pattern | `fake_research_tool` + `cache_tool` (MCP simulated) |
| Governance | SQLite trace: request_id, agent, input, output, tool, duration |
| Observability | Execution Timeline + `/demo/metrics` |
| Agent Registry | `/demo/agents` — Phase 1 active, Phase 2+ planned |

---

## Quick Start

```bash
cd pocs/multi-agent-lab/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Optional: OPENAI_API_KEY=sk-...
uvicorn main:app --reload --port 8010
```

Open **http://localhost:8010**

---

## System Design

![Multi-Agent Lab — Phase 1 System Design UX](assets/multi-agent-lab-system-design-ux.png)

Layered architecture mockup (not the web UI): Demo Client → FastAPI → Orchestrator → specialist agents → simulated tools → SQLite trace/governance, with execution trace timeline on the right.

Runnable demo UI: `backend/static/index.html` at **http://localhost:8010** · See [architecture.md](architecture.md) and [enterprise-mapping.md](enterprise-mapping.md).

---

## Demo UI (Enterprise Workspace)

| Panel | Purpose |
|---|---|
| New Request | Goal + prompt + Run |
| Execution Timeline | Orchestrator handoffs with duration + trace detail |
| Final Output | Result / Summary / Artifacts tabs |
| Agent Ecosystem | Phase 1 active + future agents |
| MCP Layer | Phase 2+ planned integrations |
| Observability | Live request metrics from SQLite |

---

## API

| Endpoint | Description |
|---|---|
| `GET /` | Enterprise workspace UI |
| `POST /demo/run` | Run orchestrator pipeline |
| `GET /demo/trace/{request_id}` | Trace timeline |
| `GET /demo/metrics` | Observability metrics |
| `GET /demo/agents` | Agent + MCP registry |
| `GET /health` | Health check |

---

## Team Demo Script (5 min)

1. **Frame it:** “This is Phase 1 of the Enterprise Agent Platform — same architecture, fewer agents.”
2. **Run** the sample Product Ideation goal.
3. **Execution Timeline:** Orchestrator → specialists → synthesis.
4. **Trace Detail:** click a step — input, output, tool, duration.
5. **Bottom panels:** Agent Ecosystem (today vs tomorrow), MCP (Phase 2), Observability.
6. **Close:** “We extend agents and add MCP — we don’t rebuild the architecture.”

---

## Roadmap Alignment

| Phase | Scope |
|---|---|
| **Phase 1 (this POC)** | 4 agents, SQLite trace, enterprise UI shell |
| Phase 2 | Agent Registry, MCP Registry, Memory Layer |
| Phase 3 | Multi-tenant, RBAC, Event Bus, full observability |
| Phase 4 | Digital Workforce — autonomous cross-agent collaboration |

---

## Not Production Yet

No auth, tenant isolation, real MCP, event bus, or enterprise memory layers.

---

## Related Design Docs

- EN: [Enterprise AI Decision Systems](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-06-07-enterprise-ai-decision-systems.md)
- 中文: [从 AI 演示到企业 AI 决策系统](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-06-07-enterprise-ai-decision-systems.zh.md)
