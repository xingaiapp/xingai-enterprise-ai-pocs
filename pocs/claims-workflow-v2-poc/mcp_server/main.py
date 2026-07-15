"""Claims Workflow MCP Server — JSON-RPC /mcp endpoint, gated by
auth.authenticate_request. Same request/response shape as
claims-mcp-oauth-poc/mcp_server/main.py.

Plays the role a real carrier's policy administration + audit-trail system
would play in production — see the POC README "Not Production Yet" for
what's simulated here vs. real.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from mcp_server.auth import authenticate_request
from mcp_server.tools import (
    tool_create_payment,
    tool_get_audit_trail,
    tool_get_policy_coverage,
    tool_record_ledger_decision,
)

app = FastAPI(title="Claims Workflow MCP Server")

TOOLS = [
    {
        "name": "get_policy_coverage",
        "description": "Check whether a loss_type is covered under a policy, and return its limit + the policy clause to cite",
        "inputSchema": {
            "type": "object",
            "properties": {
                "policy_id": {"type": "string"},
                "loss_type": {"type": "string"},
            },
            "required": ["policy_id", "loss_type"],
        },
        "scope_required": "policy.read",
    },
    {
        "name": "record_ledger_decision",
        "description": "Append one row to the Decision Ledger (Compliance & Audit Trail)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string"},
                "question": {"type": "string"},
                "recommendation": {"type": "string"},
                "reasoning": {"type": "array", "items": {"type": "string"}},
                "confidence": {"type": "number"},
                "claim_id": {"type": "string"},
                "alternatives": {"type": "array", "items": {"type": "string"}},
                "risks": {"type": "array", "items": {"type": "string"}},
                "model_version": {"type": "string"},
                "source_ref": {"type": "string"},
                "adverse_action": {"type": "boolean"},
                "policy_clause": {"type": "string"},
            },
            "required": ["domain", "question", "recommendation", "reasoning", "confidence"],
        },
        "scope_required": "audit.write",
    },
    {
        "name": "get_audit_trail",
        "description": "Return Decision Ledger rows, optionally filtered to one claim_id",
        "inputSchema": {
            "type": "object",
            "properties": {"claim_id": {"type": "string"}},
            "required": [],
        },
        "scope_required": "audit.read",
    },
    {
        "name": "create_payment",
        "description": "Settle a claim payment, idempotent on idempotency_key",
        "inputSchema": {
            "type": "object",
            "properties": {
                "claim_id": {"type": "string"},
                "amount": {"type": "number"},
                "idempotency_key": {"type": "string"},
            },
            "required": ["claim_id", "amount", "idempotency_key"],
        },
        "scope_required": "payments.write",
    },
]

_TOOL_IMPLS = {
    "get_policy_coverage": tool_get_policy_coverage,
    "record_ledger_decision": tool_record_ledger_decision,
    "get_audit_trail": tool_get_audit_trail,
    "create_payment": tool_create_payment,
}


def _jsonrpc_error(id_: object, code: int, message: str, status: int = 200) -> JSONResponse:
    return JSONResponse(content={"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}, status_code=status)


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    body = await request.json()
    method = body.get("method")
    params = body.get("params", {})
    req_id = body.get("id")

    try:
        if method == "initialize":
            return _handle_initialize(req_id)
        elif method == "tools/list":
            authenticate_request(request, set())  # any valid token, no specific scope
            tool_list = [{k: v for k, v in t.items() if k != "scope_required"} for t in TOOLS]
            return JSONResponse(content={"jsonrpc": "2.0", "id": req_id, "result": {"tools": tool_list}})
        elif method == "tools/call":
            return await _handle_tool_call(request, req_id, params)
        else:
            return _jsonrpc_error(req_id, -32601, f"Unknown method: {method}")
    except HTTPException as exc:
        return _jsonrpc_error(req_id, exc.status_code, str(exc.detail), exc.status_code)
    except Exception:
        return _jsonrpc_error(req_id, -32603, "Internal error", 500)


def _handle_initialize(req_id: object) -> JSONResponse:
    return JSONResponse(content={
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": "XingAI Claims Workflow MCP Server",
                "version": "0.1.0",
                "description": "Data-access boundary for claims_workflow — policy coverage, Decision Ledger, payments",
            },
        },
    })


async def _handle_tool_call(request: Request, req_id: object, params: dict) -> JSONResponse:
    tool_name = params.get("name")
    arguments = params.get("arguments", {})

    tool_def = next((t for t in TOOLS if t["name"] == tool_name), None)
    if not tool_def:
        return _jsonrpc_error(req_id, -32602, f"Unknown tool: {tool_name}")

    try:
        authenticate_request(request, {tool_def["scope_required"]})
    except HTTPException as exc:
        return _jsonrpc_error(req_id, exc.status_code, str(exc.detail), exc.status_code)

    impl = _TOOL_IMPLS[tool_name]
    try:
        result = impl(**arguments)
    except TypeError as exc:
        return _jsonrpc_error(req_id, -32602, f"Invalid arguments for {tool_name}: {exc}")

    return JSONResponse(content={
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {"content": [{"type": "text", "text": str(result)}], "_data": result},
    })
