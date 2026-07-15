# References — Claims Workflow v2 POC

## XingAI Design Docs

- EN: [Redesigning the Agentic Claims Workflow: Fraud Sequencing, Escalation Routing, and Compliance Audit](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-14-claims-workflow-redesign-fraud-routing-audit.md) — this POC's direct design source; every fix implemented here maps to a section there
- 中文: [重新设计理赔工作流](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-14-claims-workflow-redesign-fraud-routing-audit.zh.md)
- [Claims Settlement Workflow v2 diagram](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/assets/ARCHITECTURE-DIAGRAMS.md#claims-settlement-workflow-v2-xingai-corrected-design)
- `xingai-engineering-system/patterns/decision-ledger-schema.md` — the shared schema `ledger.py` implements

## XingAI ADRs & Platform

- [ADR-008: Claims Workflow v2 POC](../../docs/adr/008-claims-workflow-v2-poc.md) · [中文](../../docs/adr/008-claims-workflow-v2-poc.zh.md)
- [ADR-006: Claims MCP OAuth POC — real auth, not a placeholder](../../docs/adr/006-claims-mcp-oauth-poc-real-auth.md)
- [ADR-007: Claims Partner API MCP POC — full API coverage, auth deferred](../../docs/adr/007-claims-partner-api-mcp-poc-full-coverage.md)
- [POC Standards](../../docs/POC-STANDARDS.md)
- `xingai-learn` ADR-003: Decision Ledger Adoption — the same ledger shape reused here

## Related POCs in this repo

- [claims-partner-api-mcp-poc](../claims-partner-api-mcp-poc/) — idempotent payments, claim-status state machine
- [claims-mcp-oauth-poc](../claims-mcp-oauth-poc/) — the auth layer this POC's API doesn't yet have
- [claims-multiagent-rag-poc](../claims-multiagent-rag-poc/) — the earlier single-fraud-check pipeline this POC's design supersedes for the fraud/escalation/audit stages

## External

- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [Idempotency keys — Stripe API docs](https://stripe.com/docs/api/idempotent_requests) — the pattern `agents/payment.py` follows

## Production path (not built in POC)

- Persistent storage for claims, the Decision Ledger, and settlements (all in-memory today)
- Authentication / authorization in front of the API — see `claims-mcp-oauth-poc` for a runnable reference
- Real ML models for Fraud Triage / Fraud Scoring (heuristic rules only today)
- Real policy administration system integration (`MOCK_POLICIES` is a fixture)
- Multi-tenant isolation, rate limiting, observability
