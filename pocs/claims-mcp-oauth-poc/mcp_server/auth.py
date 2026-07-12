"""Token verification for the Claims MCP Server.

This is "wall #1" of the two-wall model this POC demonstrates: OAuth scope
answers "is this agent allowed to call claims.adjudicate *at all*?" It does
NOT answer "should this specific $18,000 settlement go through?" — that's
wall #2, policies.py's settlement-authority check. Conflating the two is a
common enterprise MCP mistake: a broad scope grant is not the same claim as
"any amount, any claim type, no limit."
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import jwt
from jwt import PyJWKClient
from fastapi import HTTPException, Request

EXPECTED_ISSUER = os.getenv("EXPECTED_ISSUER", "http://localhost:8000")
EXPECTED_AUDIENCE = os.getenv("EXPECTED_AUDIENCE", "http://localhost:8001/mcp")
JWKS_URL = os.getenv("JWKS_URL", "http://localhost:8000/jwks.json")

# Included in the 401 WWW-Authenticate so any MCP client (not just this
# POC's own client/) can discover the Authorization Server without a
# hardcoded config — see client/discovery.py for the consuming side.
RESOURCE_METADATA_URL = "http://localhost:8001/.well-known/oauth-protected-resource/mcp"


@lru_cache(maxsize=1)
def _get_jwks_client() -> PyJWKClient:
    return PyJWKClient(JWKS_URL, cache_keys=True)


def extract_bearer_token(request: Request) -> str:
    """Missing/malformed Authorization header → 401 with a WWW-Authenticate
    that names where to go discover the Authorization Server. This is the
    401 a claims agent should see on its very first call, before it has
    ever authenticated."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="missing_token",
            headers={"WWW-Authenticate": f'Bearer resource_metadata="{RESOURCE_METADATA_URL}"'},
        )
    return auth_header[len("Bearer "):]


def verify_token(token: str) -> dict[str, Any]:
    """Signature (via JWKS, matched by kid) + iss + aud + exp, all checked.
    Any single failure → 401, deliberately without leaking which check
    failed beyond a broad category (expired vs invalid) — a claims system is
    not the place to hand an attacker a token-forging oracle via detailed
    error messages."""
    try:
        jwks_client = _get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=EXPECTED_AUDIENCE,
            issuer=EXPECTED_ISSUER,
            options={"require": ["exp", "iss", "aud", "sub", "scope"]},
        )
        return claims
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token_expired")
    except jwt.InvalidAudienceError:
        raise HTTPException(status_code=401, detail="invalid_audience")
    except jwt.InvalidIssuerError:
        raise HTTPException(status_code=401, detail="invalid_issuer")
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"invalid_token: {exc}")


def require_scopes(claims: dict[str, Any], required: set[str]) -> None:
    token_scopes = set(claims.get("scope", "").split())
    missing = required - token_scopes
    if missing:
        raise HTTPException(status_code=403, detail=f"insufficient_scope: missing {missing}")


def authenticate_request(request: Request, required_scopes: set[str]) -> dict[str, Any]:
    """Combined entry point every tool handler calls: extract → verify →
    scope-check → return claims (which carries `sub`, the adjuster/agent
    identity every audit row below is written against)."""
    token = extract_bearer_token(request)
    claims = verify_token(token)
    require_scopes(claims, required_scopes)
    return claims
