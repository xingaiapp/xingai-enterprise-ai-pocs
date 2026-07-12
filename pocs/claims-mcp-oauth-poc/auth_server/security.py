"""PKCE verification, JWT issuance, and JWKS exposure for the demo Authorization Server.

Every function here is a place where getting the crypto wrong silently turns
into an authorization bypass, not a visible error — see docs/mcp-auth-deep-dive.md
for the worked-through "what breaks if you skip this" reasoning per function.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import math
import os
import time
from pathlib import Path
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization

# ---------------------------------------------------------------------------
# Key loading
# ---------------------------------------------------------------------------

KEYS_DIR = Path(__file__).parent.parent / "keys"
PRIVATE_KEY_PATH = KEYS_DIR / "private.pem"
PUBLIC_KEY_PATH = KEYS_DIR / "public.pem"


def _load_private_key() -> Any:
    with open(PRIVATE_KEY_PATH, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def _load_public_key() -> Any:
    with open(PUBLIC_KEY_PATH, "rb") as f:
        return serialization.load_pem_public_key(f.read())


_PRIVATE_KEY = _load_private_key()
_PUBLIC_KEY = _load_public_key()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# ISSUER/AUDIENCE double as the trust anchor a claims-system MCP server checks
# on every request (see mcp_server/auth.py) — an attacker who steals a token
# minted for a *different* audience (e.g. a different insurer's deployment of
# this same pattern) cannot replay it here, because aud won't match.
ISSUER = os.getenv("AUTH_ISSUER", "http://localhost:8000")
AUDIENCE = os.getenv("MCP_AUDIENCE", "http://localhost:8001/mcp")
ACCESS_TOKEN_TTL = int(os.getenv("ACCESS_TOKEN_TTL", "300"))   # 5 minutes — short on purpose
KID = "claims-poc-key-001"   # key id — supports multi-key JWKS rotation in production


# ---------------------------------------------------------------------------
# PKCE verification
# ---------------------------------------------------------------------------

def verify_pkce(code_verifier: str, code_challenge: str) -> bool:
    """Verify PKCE S256:
        code_challenge == BASE64URL( SHA256( ASCII(code_verifier) ) )

    hmac.compare_digest (constant-time) instead of `==` on purpose — a naive
    string compare leaks how many leading bytes matched via response timing,
    turning "guess the challenge" into a byte-at-a-time oracle attack. It's a
    slow attack, but there's no reason to leave the door open."""
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return hmac.compare_digest(expected, code_challenge)


# ---------------------------------------------------------------------------
# JWT issuance
# ---------------------------------------------------------------------------

def create_access_token(
    *,
    subject: str,
    scope: str,
    client_id: str,
    audience: str = AUDIENCE,
    ttl: int = ACCESS_TOKEN_TTL,
) -> tuple[str, int]:
    """Returns (jwt_string, expires_in_seconds). RS256 (asymmetric) so the
    claims MCP server only ever needs the *public* key to verify — it can
    never mint a token itself even if the MCP server process were fully
    compromised, because it never holds the private key."""
    now = int(time.time())
    jti = base64.urlsafe_b64encode(os.urandom(16)).decode("ascii")

    payload = {
        "iss": ISSUER,
        "sub": subject,
        "aud": audience,
        "scope": scope,
        "client_id": client_id,
        "exp": now + ttl,
        "iat": now,
        "jti": jti,
    }

    token = jwt.encode(payload, _PRIVATE_KEY, algorithm="RS256", headers={"kid": KID})
    return token, ttl


# ---------------------------------------------------------------------------
# JWKS construction
# ---------------------------------------------------------------------------

def _int_to_base64url(n: int) -> str:
    byte_length = math.ceil(n.bit_length() / 8)
    return base64.urlsafe_b64encode(n.to_bytes(byte_length, "big")).rstrip(b"=").decode("ascii")


def public_key_to_jwk() -> dict:
    pub_numbers = _PUBLIC_KEY.public_numbers()
    return {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": KID,
        "n": _int_to_base64url(pub_numbers.n),
        "e": _int_to_base64url(pub_numbers.e),
    }


def get_jwks() -> dict:
    """Supports multiple keys in the list for production key rotation —
    old + new key both listed during a rotation window so in-flight tokens
    signed with the old key still verify."""
    return {"keys": [public_key_to_jwk()]}


# ---------------------------------------------------------------------------
# Secure random token generation
# ---------------------------------------------------------------------------

def generate_secure_token(n_bytes: int = 32) -> str:
    """os.urandom, never `random` — authorization codes and refresh tokens
    are bearer secrets; a predictable one is a forged claims decision
    waiting to happen."""
    return base64.urlsafe_b64encode(os.urandom(n_bytes)).rstrip(b"=").decode("ascii")
