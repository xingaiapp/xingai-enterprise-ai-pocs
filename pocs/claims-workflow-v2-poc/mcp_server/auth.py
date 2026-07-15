"""Token verification for the Claims Workflow MCP Server.

Phase 1 (ADR-009): a single static internal service token — this server's
only caller right now is our own process, no external trust boundary is
crossed yet. `require_scopes()` is written the same way
claims-mcp-oauth-poc/mcp_server/auth.py's is, on purpose: when a real
Authorization Server is wired in front of this server (Phase 4), only
`verify_token()` needs to change from "look up a static token" to "verify
a JWT" — the scope-checking code path this module exposes to main.py stays
identical.
"""
from __future__ import annotations

import os
from typing import Any

from fastapi import HTTPException, Request

# Single internal service account, granted every scope this server defines
# — appropriate for "our own Supervisor process is the only caller" (Phase
# 1/2/3). A real third-party integration (Phase 4) would issue narrower,
# per-partner JWTs instead of reusing this token.
_SERVICE_TOKEN = os.getenv("MCP_SERVICE_TOKEN", "dev-internal-service-token")
_SERVICE_SCOPES = {"policy.read", "audit.write", "audit.read", "payments.write"}


def extract_bearer_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing_token")
    return auth_header[len("Bearer "):]


def verify_token(token: str) -> dict[str, Any]:
    """Phase 1: constant-time-ish string compare against the one service
    token. Phase 4 replaces this function's body with real JWT
    verification (see claims-mcp-oauth-poc/mcp_server/auth.py) without
    touching require_scopes() or callers."""
    if token != _SERVICE_TOKEN:
        raise HTTPException(status_code=401, detail="invalid_token")
    return {"sub": "claims-workflow-v2-supervisor", "scope": " ".join(sorted(_SERVICE_SCOPES))}


def require_scopes(claims: dict[str, Any], required: set[str]) -> None:
    token_scopes = set(claims.get("scope", "").split())
    missing = required - token_scopes
    if missing:
        raise HTTPException(status_code=403, detail=f"insufficient_scope: missing {missing}")


def authenticate_request(request: Request, required_scopes: set[str]) -> dict[str, Any]:
    token = extract_bearer_token(request)
    claims = verify_token(token)
    require_scopes(claims, required_scopes)
    return claims
