# Architecture — LLM Guardrails & Monitoring POC

## Components

| Component | Role |
|---|---|
| `backend/static/index.html` | Mobile-first demo UI; sample probes |
| `backend/main.py` | FastAPI: `/`, `/demo/run`, `/demo/steps`, `/health` |
| `backend/pipeline.py` | Deterministic 12-step runner + fail-closed skips |
| In-memory `KNOWLEDGE` | Two policy docs for RAG demo |
| Decision ledger artifact | Step 12 JSON action (`ship_answer` / `escalate_human`) |

## Phase mapping

| Phase | Steps | Responsibility |
|---|---|---|
| Plan | 1–2 | Use case, risk/policy matrix |
| Build | 3–7 | Model class, evidence RAG, prompt contract, input walls, MCP tool walls |
| Validate | 8–10 | Output gates, Agent Run metrics/trace, eval/red-team flags |
| Operate | 11–12 | Continuous deploy posture, iterate + ledger |

## Fail-closed behavior

If step 6 or 7 **blocks**, remaining steps are marked `skipped` with reason — the pipeline does not pretend later gates still ran.

## Intentional non-goals

Real LLM providers, vector DBs, OAuth AS, Durable Functions, and multi-tenant APIM are **out of scope** for Phase 1. This POC proves the **control sequence**, not production infra.
