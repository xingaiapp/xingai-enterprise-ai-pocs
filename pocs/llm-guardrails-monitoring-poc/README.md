# LLM Guardrails & Monitoring POC

> **Status: Runnable · Phase 1**

Demo of the **12-step** LLM app ladder (**Plan → Build → Validate → Operate**) with **XingAI corrections** on each wall — not a restyle of a viral tool-shopping poster.

```text
Plan:    1 Use case → 2 Risks & policy
Build:   3 Model → 4 Evidence RAG → 5 Prompt → 6 Input guards → 7 MCP two-wall tools
Validate: 8 Output guards → 9 Agent Run trace → 10 Eval / red-team
Operate: 11 Continuous deploy controls → 12 Iterate & Decision Ledger
```

## What This Proves

| Step theme | POC behavior |
|---|---|
| Use case + risk before model | Steps 1–2 always run first |
| Evidence RAG | Step 4 scores sufficiency; weak retrieval → escalate |
| Untrusted observations | Step 6 scans user **and** RAG/tool text |
| MCP two-wall | Step 7 blocks `transfer_funds` via scope wall |
| Output gates | Step 8 requires citations / escalate on uncertainty |
| Agent Run monitoring | Step 9 emits goal→step→model→outcome trace |
| Eval gates | Step 10 logs red-team flags; fail-closed earlier |
| Iterate & govern | Step 12 writes a ledger action |

## Quick Start

```bash
cd pocs/llm-guardrails-monitoring-poc/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn main:app --reload --port 8020
```

Open **http://localhost:8020**

```bash
pytest -q
```

Docker:

```bash
cd pocs/llm-guardrails-monitoring-poc
docker compose up --build
```

## Demo Script (5 min)

1. **Happy path** — “What is the premium refund policy?” → `answered` + citation.
2. **Injection** — “Ignore previous instructions…” → blocked at step 6; later steps `skipped`.
3. **Risky tool** — “transfer_funds…” → blocked at step 7 (MCP scope wall).
4. **Weak evidence** — nonsense query → `escalated` at Operate (ledger `escalate_human`).
5. Point at each card’s **XingAI** correction line (walls ≠ tool logos).

## API

| Endpoint | Description |
|---|---|
| `GET /` | Demo UI |
| `POST /demo/run` | Run all 12 steps (`{"user_input":"..."}`) |
| `GET /demo/steps` | Step catalog |
| `GET /health` | Health |

## Not Production Yet

- Mock model only (no live LLM)
- No real OAuth/Entra/APIM
- No durable workflow runtime
- No multi-tenant isolation
- In-memory knowledge corpus (2 docs)

## Related Design Docs

- EN: [LLM App Guardrails: Plan → Build → Validate → Operate Is Not a Tool Catalog](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-17-llm-app-guardrails-plan-build-validate-operate.md)
- 中文: [LLM 应用护栏：Plan → Build → Validate → Operate 不是工具目录](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-17-llm-app-guardrails-plan-build-validate-operate.zh.md)
- EN: [Enterprise AI Decision Systems](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-06-07-enterprise-ai-decision-systems.md)
- 中文: [从 AI 演示到企业 AI 决策系统](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-06-07-enterprise-ai-decision-systems.zh.md)
- EN: [Beyond Prompt Engineering: Loop Engineering](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-03-beyond-prompt-engineering-loop-engineering.md)
- 中文: [超越提示工程：循环工程](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-03-beyond-prompt-engineering-loop-engineering.zh.md)
- EN: [Agent Governance Reference Architecture](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-05-agent-governance-reference-architecture.md)
- 中文: [Agent 治理参考架构](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-05-agent-governance-reference-architecture.zh.md)
- EN: [Third-Party MCP Auth: API Key vs OAuth2](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-15-third-party-mcp-auth-api-key-vs-oauth2.md)
- 中文: [第三方 MCP 认证：API Key vs OAuth2](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-15-third-party-mcp-auth-api-key-vs-oauth2.zh.md)

Tech blog: [Twelve Steps Are Not Twelve Tool Logos](https://github.com/xingaiapp/xingai-tech-blog/blob/main/posts/2026-07-17-llm-guardrails-twelve-steps-not-tool-stickers.md) · [中文](https://github.com/xingaiapp/xingai-tech-blog/blob/main/posts/2026-07-17-llm-guardrails-twelve-steps-not-tool-stickers.zh.md)

Wiki critique of the public ladder: [llm-guardrails-monitoring-vs-xingai](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/syntheses/llm-guardrails-monitoring-vs-xingai.md)

## Disclaimer

See [DISCLAIMER.md](DISCLAIMER.md). Educational POC only — not production software.
