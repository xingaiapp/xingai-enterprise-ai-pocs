"""OAuth 2.1 + PKCE Authorization Server (demo) for the Claims MCP OAuth POC.

Plays the role a carrier's real Identity Provider would play in production
(Okta / Auth0 / Azure AD B2C / a homegrown IdP) — see README.md "Not
Production Yet" for exactly what's simulated here vs. what a real IdP gives
you for free (MFA, session management, breach-detection, admin console).
"""
from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from auth_server.models import (
    AuthorizationCodeRecord,
    ClientRegistration,
    RefreshTokenRecord,
    RegistrationRequest,
    RegistrationResponse,
    SUPPORTED_SCOPES,
    TokenResponse,
)
from auth_server.security import (
    AUDIENCE,
    ISSUER,
    create_access_token,
    generate_secure_token,
    get_jwks,
    verify_pkce,
)
from auth_server.storage import storage

app = FastAPI(title="Claims MCP OAuth 2.1 Authorization Server (Demo)")

SCOPE_LABELS = {
    "claims.read": "Read claim files (claimant, loss description, filed amount, status)",
    "policy.read": "Read policy coverage limits and deductibles",
    "claims.review": "Draft a claim decision (not binding — proposal only)",
    "claims.adjudicate": "Finalize a previously-reviewed claim decision (binding)",
    "offline_access": "Stay signed in (issue a refresh token)",
}

# ---------------------------------------------------------------------------
# AS Metadata (RFC 8414)
# ---------------------------------------------------------------------------

@app.get("/.well-known/oauth-authorization-server")
async def oauth_metadata():
    """Authorization Server Metadata — the MCP client discovers every
    endpoint from this one URL instead of hardcoding per-deployment values.
    This is what lets the same adjuster-assist agent point at a different
    carrier's Authorization Server without a code change — see
    docs/mcp-auth-deep-dive.md §"Why discovery matters for MCP specifically"."""
    return {
        "issuer": ISSUER,
        "authorization_endpoint": f"{ISSUER}/authorize",
        "token_endpoint": f"{ISSUER}/token",
        "jwks_uri": f"{ISSUER}/jwks.json",
        "registration_endpoint": f"{ISSUER}/register",
        "revocation_endpoint": f"{ISSUER}/revoke",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
        "scopes_supported": sorted(SUPPORTED_SCOPES),
        "subject_types_supported": ["public"],
    }


@app.get("/jwks.json")
async def jwks():
    """Public signing key(s) — the claims MCP server fetches this to verify
    token signatures. Publishing this is safe by design: it's the *public*
    half of an asymmetric keypair, useless for forging tokens."""
    return get_jwks()


# ---------------------------------------------------------------------------
# Dynamic client registration (RFC 7591 — demo: loopback redirects only)
# ---------------------------------------------------------------------------

@app.post("/register", response_model=RegistrationResponse)
async def register_client(req: RegistrationRequest):
    """Demo restricts redirect_uri to loopback addresses — a real deployment
    would restrict to the carrier's own registered agent-runtime callback
    URLs, never an open registration surface an attacker could self-serve."""
    for uri in req.redirect_uris:
        if not (uri.startswith("http://127.0.0.1") or uri.startswith("http://localhost")):
            raise HTTPException(status_code=400, detail="Demo mode only allows loopback redirect URIs")

    client_id = f"dyn-{generate_secure_token(12)}"
    client = ClientRegistration(
        client_id=client_id,
        redirect_uris=req.redirect_uris,
        client_name=req.client_name,
        token_endpoint_auth_method=req.token_endpoint_auth_method,
    )
    storage.save_client(client)

    return RegistrationResponse(
        client_id=client_id,
        client_name=client.client_name,
        redirect_uris=client.redirect_uris,
        token_endpoint_auth_method=client.token_endpoint_auth_method,
    )


# ---------------------------------------------------------------------------
# Authorization endpoint
# ---------------------------------------------------------------------------

@app.get("/authorize", response_class=HTMLResponse)
async def authorize_get(
    response_type: str = Query(...),
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    scope: str = Query(...),
    state: str = Query(...),
    code_challenge: str = Query(...),
    code_challenge_method: str = Query(...),
):
    """Consent page — a human (the adjuster, or a claims-ops admin during
    onboarding) sees exactly what the agent is asking to be able to do
    before anything is granted. Demo uses a fixed user; production requires
    a real login + session here."""
    _validate_authorize_params(response_type, client_id, redirect_uri, scope, code_challenge_method)

    scope_rows = "".join(
        f'<div class="scope">&#10003; <strong>{s}</strong> — {SCOPE_LABELS.get(s, "")}</div>'
        for s in scope.split()
    )
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Claims MCP — Authorization Request</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 520px; margin: 60px auto; padding: 20px; }}
    .scope {{ background: #f0f4f8; padding: 8px 12px; border-radius: 6px; margin: 6px 0; }}
    button {{ background: #2563eb; color: white; border: none; padding: 10px 20px;
              border-radius: 6px; cursor: pointer; font-size: 16px; margin-right: 10px; }}
    button.deny {{ background: #dc2626; }}
  </style>
</head>
<body>
  <h2>Authorization Request</h2>
  <p><strong>Application:</strong> {client_id}</p>
  <p><strong>Requesting the following permissions on your claims system:</strong></p>
  {scope_rows}
  <p style="color:#6b7280;font-size:13px;">This grant does not by itself authorize any specific
  claim amount — see the claims MCP server's per-claim settlement authority check.</p>
  <br>
  <form method="POST" action="/authorize">
    <input type="hidden" name="response_type" value="{response_type}">
    <input type="hidden" name="client_id" value="{client_id}">
    <input type="hidden" name="redirect_uri" value="{redirect_uri}">
    <input type="hidden" name="scope" value="{scope}">
    <input type="hidden" name="state" value="{state}">
    <input type="hidden" name="code_challenge" value="{code_challenge}">
    <input type="hidden" name="code_challenge_method" value="{code_challenge_method}">
    <button type="submit" name="decision" value="allow">Allow</button>
    <button type="submit" name="decision" value="deny" class="deny">Deny</button>
  </form>
</body>
</html>
"""
    return HTMLResponse(content=html)


@app.post("/authorize")
async def authorize_post(
    response_type: str = Form(...),
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    scope: str = Form(...),
    state: str = Form(...),
    code_challenge: str = Form(...),
    code_challenge_method: str = Form(...),
    decision: str = Form(...),
):
    """Handles the human's consent decision, issues the single-use
    authorization code on Allow. `state` is echoed back unchanged so the
    client can detect a forged/replayed redirect (CSRF) — see
    client/main.py's state check on the receiving end."""
    _validate_authorize_params(response_type, client_id, redirect_uri, scope, code_challenge_method)

    if decision != "allow":
        return RedirectResponse(f"{redirect_uri}?error=access_denied&state={state}", status_code=302)

    code = generate_secure_token(24)
    record = AuthorizationCodeRecord(
        code=code,
        client_id=client_id,
        redirect_uri=redirect_uri,
        user_id="demo-adjuster-001",   # fixed demo user; a real session lives here
        scope=scope,
        code_challenge=code_challenge,
    )
    storage.save_code(record)

    return RedirectResponse(f"{redirect_uri}?code={code}&state={state}", status_code=302)


def _validate_authorize_params(
    response_type: str, client_id: str, redirect_uri: str, scope: str, code_challenge_method: str,
) -> None:
    if response_type != "code":
        raise HTTPException(status_code=400, detail="Only response_type=code is supported")

    client = storage.get_client(client_id)
    if not client:
        raise HTTPException(status_code=400, detail="Unknown client_id")

    if redirect_uri not in client.redirect_uris:
        raise HTTPException(status_code=400, detail="redirect_uri does not match registration")

    if code_challenge_method != "S256":
        raise HTTPException(status_code=400, detail="Must use code_challenge_method=S256")

    requested = set(scope.split())
    unknown = requested - SUPPORTED_SCOPES
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unsupported scope(s): {unknown}")


# ---------------------------------------------------------------------------
# Token endpoint
# ---------------------------------------------------------------------------

@app.post("/token", response_model=TokenResponse)
async def token_endpoint(
    grant_type: str = Form(...),
    code: Optional[str] = Form(None),
    redirect_uri: Optional[str] = Form(None),
    client_id: Optional[str] = Form(None),
    code_verifier: Optional[str] = Form(None),
    refresh_token: Optional[str] = Form(None),
    scope: Optional[str] = Form(None),
):
    if grant_type == "authorization_code":
        return await _handle_authorization_code(code, redirect_uri, client_id, code_verifier)
    elif grant_type == "refresh_token":
        return await _handle_refresh_token(refresh_token, client_id, scope)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported grant_type: {grant_type}")


async def _handle_authorization_code(
    code: Optional[str], redirect_uri: Optional[str], client_id: Optional[str], code_verifier: Optional[str],
) -> TokenResponse:
    if not all([code, redirect_uri, client_id, code_verifier]):
        raise HTTPException(status_code=400, detail="authorization_code grant is missing required parameters")

    record = storage.get_code(code)  # type: ignore[arg-type]

    # Validation order matters for clear error messages: exists → still
    # valid (unused + unexpired) → client matches → redirect matches → PKCE.
    if not record:
        raise HTTPException(status_code=400, detail="Invalid authorization code")
    if not record.is_valid:
        detail = "Authorization code already used" if record.used else "Authorization code expired"
        raise HTTPException(status_code=400, detail=detail)
    if record.client_id != client_id:
        raise HTTPException(status_code=400, detail="client_id mismatch")
    if record.redirect_uri != redirect_uri:
        raise HTTPException(status_code=400, detail="redirect_uri mismatch")
    if not verify_pkce(code_verifier, record.code_challenge):  # type: ignore[arg-type]
        raise HTTPException(
            status_code=400,
            detail="PKCE verification failed: code_verifier does not match code_challenge",
        )

    storage.mark_code_used(code)  # type: ignore[arg-type]  # prevents replay of a stolen code

    access_token, expires_in = create_access_token(
        subject=record.user_id, scope=record.scope, client_id=record.client_id,
    )

    refresh = None
    if "offline_access" in record.scope.split():
        refresh = generate_secure_token(32)
        storage.save_refresh_token(RefreshTokenRecord(
            token=refresh, client_id=record.client_id, user_id=record.user_id, scope=record.scope,
        ))

    return TokenResponse(access_token=access_token, expires_in=expires_in, refresh_token=refresh, scope=record.scope)


async def _handle_refresh_token(
    refresh_token: Optional[str], client_id: Optional[str], scope: Optional[str],
) -> TokenResponse:
    """Rotation: validate → immediately revoke the old token → issue new
    access + refresh. If someone (attacker or a race between two agent
    processes) replays an already-rotated refresh token, this fails —
    which is itself a signal worth alerting on in production."""
    if not refresh_token or not client_id:
        raise HTTPException(status_code=400, detail="refresh_token grant is missing parameters")

    record = storage.get_refresh_token(refresh_token)
    if not record:
        raise HTTPException(status_code=400, detail="Invalid refresh_token")
    if not record.is_valid:
        detail = "refresh_token has been revoked" if record.revoked else "refresh_token has expired"
        raise HTTPException(status_code=400, detail=detail)
    if record.client_id != client_id:
        raise HTTPException(status_code=400, detail="client_id mismatch")

    storage.revoke_refresh_token(refresh_token)

    access_token, expires_in = create_access_token(subject=record.user_id, scope=record.scope, client_id=record.client_id)

    new_refresh = generate_secure_token(32)
    storage.save_refresh_token(RefreshTokenRecord(
        token=new_refresh, client_id=record.client_id, user_id=record.user_id, scope=record.scope,
    ))

    return TokenResponse(access_token=access_token, expires_in=expires_in, refresh_token=new_refresh, scope=record.scope)


# ---------------------------------------------------------------------------
# Revocation endpoint (RFC 7009)
# ---------------------------------------------------------------------------

@app.post("/revoke")
async def revoke(token: str = Form(...), client_id: Optional[str] = Form(None)):
    """RFC 7009: returns 200 even for an unknown token — telling a caller
    'that token doesn't exist' vs 'that token was revoked' would let someone
    enumerate valid tokens by trying revoke calls."""
    record = storage.get_refresh_token(token)
    if record and (client_id is None or record.client_id == client_id):
        storage.revoke_refresh_token(token)
    return JSONResponse(content={}, status_code=200)
