"""Claims MCP Server (demo) — JSON-RPC /mcp endpoint, Protected Resource
Metadata, and the four claims tools, all gated by auth.authenticate_request.

Plays the role a real carrier's Policy Administration / Claims Management
System MCP wrapper would play in production (e.g. a thin MCP layer in front
of Guidewire ClaimCenter, Duck Creek Claims, or a homegrown claims system) —
see README.md "Not Production Yet" for what's simulated vs. real here.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException

from mcp_server.auth import EXPECTED_AUDIENCE, authenticate_request
from mcp_server.tools import (
    tool_get_claim,
    tool_get_policy_coverage,
    tool_review_claim_decision,
    tool_submit_claim_decision,
)

app = FastAPI(title="Claims MCP Server (Demo)")

# ---------------------------------------------------------------------------
# Tool definitions (returned by tools/list)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "get_claim",
        "description": "Return a claim file: claimant, loss description, filed amount, status",
        "inputSchema": {
            "type": "object",
            "properties": {"claim_id": {"type": "string", "description": "e.g. CLM-8841"}},
            "required": ["claim_id"],
        },
        "scope_required": "claims.read",
    },
    {
        "name": "get_policy_coverage",
        "description": "Return coverage limits and deductibles for a policy number",
        "inputSchema": {
            "type": "object",
            "properties": {"policy_number": {"type": "string", "description": "e.g. POL-1001"}},
            "required": ["policy_number"],
        },
        "scope_required": "policy.read",
    },
    {
        "name": "review_claim_decision",
        "description": (
            "Draft a claim decision (approve/deny/partial + settlement amount) and return a "
            "review_id. Does not finalize anything — human confirmation required before "
            "calling submit_claim_decision."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "claim_id": {"type": "string"},
                "decision": {"type": "string", "enum": ["approve", "deny", "partial"]},
                "settlement_amount": {"type": "number", "minimum": 0},
                "rationale": {"type": "string"},
            },
            "required": ["claim_id", "decision", "settlement_amount", "rationale"],
        },
        "scope_required": "claims.review",
    },
    {
        "name": "submit_claim_decision",
        "description": "Finalize a previously-reviewed claim decision using review_id (idempotent)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "review_id": {"type": "string"},
                "idempotency_key": {"type": "string"},
            },
            "required": ["review_id", "idempotency_key"],
        },
        "scope_required": "claims.adjudicate",
    },
]


# ---------------------------------------------------------------------------
# Protected Resource Metadata (RFC 9728)
# ---------------------------------------------------------------------------

@app.get("/.well-known/oauth-protected-resource/mcp")
async def protected_resource_metadata():
    """A client that gets a 401 from /mcp fetches this to learn which
    Authorization Server(s) it should authenticate against — see
    client/discovery.py for the consuming side of this chain."""
    return {
        "resource": EXPECTED_AUDIENCE,
        "authorization_servers": ["http://localhost:8000"],
        "scopes_supported": ["claims.read", "policy.read", "claims.review", "claims.adjudicate", "offline_access"],
        "bearer_methods_supported": ["header"],
        "resource_documentation": "https://github.com/xingaiapp/xingai-enterprise-ai-pocs/tree/main/pocs/claims-mcp-oauth-poc",
    }


# ---------------------------------------------------------------------------
# JSON-RPC /mcp endpoint
# ---------------------------------------------------------------------------

def _jsonrpc_error(id_: object, code: int, message: str, status: int = 200) -> JSONResponse:
    return JSONResponse(content={"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}, status_code=status)


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    token = request.headers.get("Authorization", "")
    if not token.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="missing_token",
            headers={
                "WWW-Authenticate": (
                    'Bearer resource_metadata='
                    '"http://localhost:8001/.well-known/oauth-protected-resource/mcp"'
                ),
            },
        )

    body = await request.json()
    method = body.get("method")
    params = body.get("params", {})
    req_id = body.get("id")

    try:
        if method == "initialize":
            return _handle_initialize(req_id)
        elif method == "tools/list":
            authenticate_request(request, set())   # any valid token, no specific scope
            tool_list = [{k: v for k, v in t.items() if k != "scope_required"} for t in TOOLS]
            return JSONResponse(content={"jsonrpc": "2.0", "id": req_id, "result": {"tools": tool_list}})
        elif method == "tools/call":
            return await _handle_tool_call(request, req_id, params)
        else:
            return _jsonrpc_error(req_id, -32601, f"Unknown method: {method}")
    except HTTPException as exc:
        return _jsonrpc_error(req_id, exc.status_code, exc.detail, exc.status_code)
    except Exception:
        # Never leak internal stack traces into a claims-adjacent API response.
        return _jsonrpc_error(req_id, -32603, "Internal error", 500)


def _handle_initialize(req_id: object) -> JSONResponse:
    return JSONResponse(content={
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": "XingAI Claims MCP Server (Demo)",
                "version": "0.1.0",
                "description": "Simulated claims system MCP — no real policy admin or claims backend connected",
            },
        },
    })


async def _handle_tool_call(request: Request, req_id: object, params: dict) -> JSONResponse:
    tool_name = params.get("name")
    arguments = params.get("arguments", {})

    tool_def = next((t for t in TOOLS if t["name"] == tool_name), None)
    if not tool_def:
        return _jsonrpc_error(req_id, -32602, f"Unknown tool: {tool_name}")

    required_scope = tool_def["scope_required"]
    try:
        claims = authenticate_request(request, {required_scope})
    except HTTPException as exc:
        return _jsonrpc_error(req_id, exc.status_code, exc.detail, exc.status_code)

    user_id = claims.get("sub", "unknown")

    try:
        if tool_name == "get_claim":
            result = tool_get_claim(claim_id=arguments.get("claim_id", ""))
        elif tool_name == "get_policy_coverage":
            result = tool_get_policy_coverage(policy_number=arguments.get("policy_number", ""))
        elif tool_name == "review_claim_decision":
            result = tool_review_claim_decision(
                claim_id=arguments.get("claim_id", ""),
                decision=arguments.get("decision", ""),
                settlement_amount=float(arguments.get("settlement_amount", 0)),
                rationale=arguments.get("rationale", ""),
                user_id=user_id,
            )
        elif tool_name == "submit_claim_decision":
            result = tool_submit_claim_decision(
                review_id=arguments.get("review_id", ""),
                idempotency_key=arguments.get("idempotency_key", ""),
                user_id=user_id,
            )
        else:
            return _jsonrpc_error(req_id, -32601, f"Tool not implemented: {tool_name}")
    except HTTPException as exc:
        return _jsonrpc_error(req_id, exc.status_code, exc.detail, exc.status_code)

    return JSONResponse(content={
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {"content": [{"type": "text", "text": str(result)}], "_data": result},
    })
