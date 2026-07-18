# ADR-010: LLM Guardrails & Monitoring 12-Step Demo POC

**Date:** 2026-07-17  
**Status:** Accepted  
**Also available:** [中文](010-llm-guardrails-monitoring-poc.zh.md)

## Context

Public teaching diagrams list 10–12 steps for “LLM apps with guardrails and monitoring,” often as tool-shopping checklists. XingAI needs a **runnable** POC that demos every step while applying known corrections: risk before model, evidence sufficiency, untrusted observations, MCP two-wall tool control, Agent Run traces, and Decision Ledger iterate/govern.

## Decision

Add `pocs/llm-guardrails-monitoring-poc/` as a FastAPI Phase-1 demo:

- Deterministic mock model (no API key required)
- Explicit 12-step pipeline with fail-closed skips
- UI sample probes: happy path, injection, risky tool, weak evidence
- Document XingAI corrections on each step result

## Consequences

- Complements claims-mcp-oauth and multi-agent-lab without duplicating real OAuth
- Easy classroom / leadership demo on port 8020
- Not a substitute for production identity, durable workflows, or live eval suites

## Follow-ups

- Tech blog: [Twelve Steps Are Not Twelve Tool Logos](https://github.com/xingaiapp/xingai-tech-blog/blob/main/posts/2026-07-17-llm-guardrails-twelve-steps-not-tool-stickers.md)
- Enterprise design: [Plan → Build → Validate → Operate Is Not a Tool Catalog](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-17-llm-app-guardrails-plan-build-validate-operate.md)
- Wiki: [product page](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/products/llm-guardrails-monitoring-poc.md) · [ladder critique](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/syntheses/llm-guardrails-monitoring-vs-xingai.md)
