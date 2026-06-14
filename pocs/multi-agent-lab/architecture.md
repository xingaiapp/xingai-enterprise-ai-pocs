# Architecture — Multi-Agent Lab

## System Design UX

![Multi-Agent Lab — Phase 1 System Design UX](assets/multi-agent-lab-system-design-ux.png)

Polished system design mockup (same style as [Orchestrator vs MCP Gateway](../../docs/assets/orchestrator-vs-mcp-gateway-ux.png)): six layers from Demo Client through FastAPI, Orchestrator, specialist agents, simulated MCP tools, and SQLite governance store — plus a trace timeline for one request.

## Components

| Layer | Responsibility |
|---|---|
| Demo UI | Input box, final answer panel, trace timeline |
| FastAPI | `POST /demo/run`, `GET /demo/trace/{id}`, `GET /` |
| Orchestrator | Plans handoffs, runs specialists, synthesizes final answer |
| Specialist agents | Research, Product, Tech, Critic |
| Tools | `fake_research_tool`, `cache_tool` |
| SQLite | `demo_runs`, `trace_logs`, `cache_entries` |
| OpenAI API | Live generation when `OPENAI_API_KEY` is set |

## Agent Responsibilities

### Orchestrator Agent

- Reads user request
- Logs routing decision
- Invokes specialist agents in order
- Combines outputs into 6-section final answer

### Research Agent

- Uses `fake_research_tool` for deterministic demo seed data
- Optionally enhances with OpenAI
- Returns trend, opportunity, evidence, why_it_matters

### Product Agent

- Converts research into product concept
- Returns target user, pain point, MVP features, value proposition

### Tech Agent

- Proposes MVP architecture
- Returns frontend, backend, database, API, agent flow, deployment

### Critic Agent

- Reviews product + tech plans
- Returns product/tech/data/demo risks and mitigations

## Trace Model

Each step stores:

- `request_id`
- `step`
- `agent_name`
- `input`
- `output`
- `tool_used`
- `timestamp`

The UI renders this as a timeline — enough transparency for demos without exposing hidden chain-of-thought.

## Cache Strategy

`fake_research_tool` caches by topic hash in SQLite. Second identical demo run shows faster research step and `cache_tool` in trace.

## OpenAI Fallback

If `OPENAI_API_KEY` is missing, agents return structured fallback JSON so the demo still runs end-to-end.
