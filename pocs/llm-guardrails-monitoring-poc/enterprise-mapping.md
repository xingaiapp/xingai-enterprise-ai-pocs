# Enterprise Mapping — LLM Guardrails & Monitoring POC

| Enterprise concept | This POC | Platform later |
|---|---|---|
| Policy matrix | Step 2 in-memory dict | Config service + versioned policy |
| Evidence RAG | Keyword score + sufficiency flag | Azure AI Search / Agentic Retrieval |
| Input sanitization | Regex over user+RAG+tool text | Dedicated policy service + Agent Traps suite |
| MCP two-wall | Scope deny + policy note | Real OAuth RS + business-rule engine ([claims-mcp-oauth-poc](../claims-mcp-oauth-poc/)) |
| Output validation | Citation + confidence + escalate | Schema registry + moderation |
| Observability | In-response Agent Run trace | OpenTelemetry Agent Run spans |
| Eval gates | Logged flags | CI blocking eval suite (Course 06) |
| Decision Ledger | Step 12 artifact | Durable ledger store + audit API |

## Leadership positioning

> This is not “another LangChain hello world.” It is a **teachable control plane sequence**: Plan walls early, Gate before side effects, Operate with ledger proof.
