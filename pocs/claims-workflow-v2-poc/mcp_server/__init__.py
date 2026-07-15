"""Claims Workflow MCP Server — the data-access boundary for claims_workflow.

Hand-rolled JSON-RPC /mcp endpoint over FastAPI, same pattern as
claims-mcp-oauth-poc/mcp_server/main.py (no official MCP SDK dependency —
consistent with existing precedent in this repo). See ADR-009 for why this
exists and what's deliberately deferred to later phases.
"""
