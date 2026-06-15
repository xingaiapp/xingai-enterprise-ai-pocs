# XingAI Enterprise AI POCs

**Version:** 0.2.0

Runnable proof-of-concept projects for enterprise AI decision systems and architecture patterns.

This repository pairs with [xingai-enterprise-ai-design](https://github.com/xingaiapp/xingai-enterprise-ai-design), which explains the architecture patterns. This repo keeps the runnable POCs, reference implementations, experiments, and deployment notes.

## What This Repository Is

- A home for runnable enterprise AI POCs
- A place to test architecture patterns before productizing them
- A reference implementation library for articles in `xingai-enterprise-ai-design`
- A record of tradeoffs, failures, and lessons learned

## What This Repository Is Not

- Not a product repo
- Not a marketing demo collection
- Not production-ready enterprise software
- Not a replacement for product-specific XingAI apps

## POC Index

| POC | Pattern | Status | Related Design Topic |
|---|---|---|---|
| [Multi-Agent Lab](pocs/multi-agent-lab/) | Orchestrator + specialist handoffs | Runnable · Phase 1 MVP | [Enterprise Agent Platform](docs/ENTERPRISE-AGENT-PLATFORM.md) |
| [Event Bus AI Review](pocs/event-bus-ai-review/) | Event-driven AI decisions | Architecture Design Only | Enterprise AI decision systems |
| Human-in-the-Loop Decision | Approval workflow | Planned | Human approval layers |
| Memory Layer Demo | User + organization memory | Planned | Memory architectures |
| MCP Tool Gateway | Tool routing and governance | Planned | MCP in enterprise AI |

## Repository Structure

```text
pocs/
  multi-agent-lab/
  event-bus-ai-review/
  human-in-the-loop-decision/
  memory-layer-demo/
  mcp-tool-gateway/
shared/
  schemas/
  docker/
docs/
  ENTERPRISE-AGENT-PLATFORM.md
  ENTERPRISE-AGENT-PLATFORM.zh.md
  CONTRIBUTING.md
  POC-STANDARDS.md
```

## POC Standard

Every POC should answer four questions:

1. What architecture pattern does this prove?
2. What is intentionally missing because this is not production?
3. What did we learn from building it?
4. Which English and Chinese design docs does it support?

See [`docs/POC-STANDARDS.md`](docs/POC-STANDARDS.md).

## Contributing

See [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) for contribution guidelines.

## Version Notes

### 0.2.0

- **Multi-Agent Lab: error propagation** — `_run_safe()` wrapper catches empty results and exceptions; pipeline surfaces `pipeline_errors` in response instead of silently continuing on failure
- **Multi-Agent Lab: prompts separated** — all system prompts extracted to `agents/prompts.py`; agents import from there rather than embedding strings
- **Multi-Agent Lab: topic-aware research** — `fake_research_tool` returns different fixtures for invest / meal / learn / enterprise / default topics based on user input keywords
- **Multi-Agent Lab: input validation** — `POST /demo/run` rejects inputs over 2000 characters (422)
- **Multi-Agent Lab: rate limiting** — `slowapi` limits `POST /demo/run` to 10 req/min per IP (configurable via `RATE_LIMIT_PER_MINUTE`)
- **Multi-Agent Lab: CORS restricted** — `allow_origins` now reads from `ALLOWED_ORIGINS` env var; no longer `"*"` by default
- **Multi-Agent Lab: structured logging** — Python `logging` wired throughout orchestrator, agents, LLM service, and tools
- **Multi-Agent Lab: LLM request_id** — `chat_json()` accepts `request_id` for log correlation
- **Multi-Agent Lab: configurable cache TTL** — `CACHE_TTL_HOURS` env var (default 24)
- **Multi-Agent Lab: tests** — 30+ pytest tests across cache, research tool, API, and orchestrator; 70% coverage gate
- **Multi-Agent Lab: Dockerfile + docker-compose** — `docker compose up` from `pocs/multi-agent-lab/`
- **Multi-Agent Lab: CI** — GitHub Actions: lint (ruff), test + coverage, security scan (pip-audit)
- **Multi-Agent Lab: Dependabot** — weekly pip updates for backend dependencies
- **Event Bus AI Review: status label** — README now clearly marked "Architecture Design Only"
- **Event Bus AI Review: enterprise-mapping.md** — added POC vs Platform mapping and leadership positioning
- **POC-STANDARDS.md: updated** — `enterprise-mapping.md` now required; status label required; Lessons Learned guidance added

### 0.1.4

- Position Multi-Agent Lab as **Phase 1 MVP Validation Layer** for Enterprise Agent Platform
- Add enterprise architecture docs (EN + 中文)
- Upgrade demo UI to enterprise workspace layout with agent registry and metrics

### 0.1.3

- Add runnable **Multi-Agent Lab** POC (`pocs/multi-agent-lab/`)
- FastAPI demo with Orchestrator + Research/Product/Tech/Critic agents and SQLite trace timeline

### 0.1.2

- Add contribution guidelines for new POCs
- Require contributors to update POC index, version notes, and bilingual design references

### 0.1.1

- Require every POC to reference matching `xingai-enterprise-ai-design` docs in both English and Chinese when available
- Update the Event Bus AI Review placeholder with bilingual design links

### 0.1.0

- Initial repository structure
- POC standards
- First POC placeholders for enterprise AI decision-system patterns

## Related Repositories

- [xingai-enterprise-ai-design](https://github.com/xingaiapp/xingai-enterprise-ai-design) — architecture articles, diagrams, and design patterns
- [xingai-tech-blog](https://github.com/xingaiapp/xingai-tech-blog) — engineering stories and implementation notes
- [xingai-dot-app](https://github.com/xingaiapp/xingai-dot-app) — XingAI marketing site

## License

Code and docs are owned by XingAI unless a specific POC folder declares a different license.
