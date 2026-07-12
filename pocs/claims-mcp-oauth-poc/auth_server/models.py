"""Data models for the demo Authorization Server.

Domain note: scopes below are claims-industry shaped (claims.read,
policy.read, claims.review, claims.adjudicate) instead of a generic
resource — see docs/mcp-auth-deep-dive.md for why scope granularity matters
for a claims adjuster-assist agent specifically (an agent that can *read* a
claim file should not automatically be able to *finalize* a settlement).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Authorization Code
# ---------------------------------------------------------------------------

@dataclass
class AuthorizationCodeRecord:
    """Single-use, short-lived authorization code, exchanged for tokens.
    120s TTL is deliberately tight — this code is only ever supposed to
    survive the redirect round-trip, not sit around."""
    code: str
    client_id: str
    redirect_uri: str
    user_id: str
    scope: str                     # space-separated scope list
    code_challenge: str            # PKCE S256 challenge
    created_at: float = field(default_factory=time.time)
    expires_in: int = 120
    used: bool = False             # one-shot: set True immediately after exchange

    @property
    def expires_at(self) -> float:
        return self.created_at + self.expires_in

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    @property
    def is_valid(self) -> bool:
        return not self.used and not self.is_expired


# ---------------------------------------------------------------------------
# Refresh Token
# ---------------------------------------------------------------------------

@dataclass
class RefreshTokenRecord:
    """Refresh token with rotation support — the old token is invalidated
    the instant a new one is issued, so a stolen-and-replayed old refresh
    token fails immediately instead of silently working forever."""
    token: str
    client_id: str
    user_id: str
    scope: str
    revoked: bool = False
    created_at: float = field(default_factory=time.time)
    expires_in: int = 86400 * 30   # 30 days

    @property
    def expires_at(self) -> float:
        return self.created_at + self.expires_in

    @property
    def is_valid(self) -> bool:
        return not self.revoked and time.time() < self.expires_at


# ---------------------------------------------------------------------------
# Client registration
# ---------------------------------------------------------------------------

@dataclass
class ClientRegistration:
    """OAuth client registration record — one row per adjuster-assist agent
    deployment (e.g. one per claims branch office in a real rollout)."""
    client_id: str
    redirect_uris: list[str]
    client_name: str = ""
    token_endpoint_auth_method: str = "none"   # public client (no secret)


# ---------------------------------------------------------------------------
# Pydantic request/response schemas
# ---------------------------------------------------------------------------

class TokenRequest(BaseModel):
    grant_type: str
    code: Optional[str] = None
    redirect_uri: Optional[str] = None
    client_id: Optional[str] = None
    code_verifier: Optional[str] = None
    refresh_token: Optional[str] = None
    scope: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    scope: str


class RegistrationRequest(BaseModel):
    client_name: str
    redirect_uris: list[str]
    token_endpoint_auth_method: str = "none"


class RegistrationResponse(BaseModel):
    client_id: str
    client_name: str
    redirect_uris: list[str]
    token_endpoint_auth_method: str


# ---------------------------------------------------------------------------
# Supported scopes — claims-industry shaped, deliberately split
# ---------------------------------------------------------------------------

SCOPE_CLAIMS_READ = "claims.read"           # read a claim file (claimant, loss description, filed amount, status)
SCOPE_POLICY_READ = "policy.read"           # read policy coverage limits / deductible for a policy number
SCOPE_CLAIMS_REVIEW = "claims.review"       # draft a decision (approve/deny/settle) — never binding on its own
SCOPE_CLAIMS_ADJUDICATE = "claims.adjudicate"  # finalize a previously-reviewed decision — binding, writes claim status
SCOPE_OFFLINE_ACCESS = "offline_access"     # required to receive a refresh token

SUPPORTED_SCOPES = {
    SCOPE_CLAIMS_READ,
    SCOPE_POLICY_READ,
    SCOPE_CLAIMS_REVIEW,
    SCOPE_CLAIMS_ADJUDICATE,
    SCOPE_OFFLINE_ACCESS,
}
