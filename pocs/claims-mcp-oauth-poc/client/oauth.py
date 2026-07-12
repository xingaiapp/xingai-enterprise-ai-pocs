"""PKCE generation, loopback callback server, and token exchange for the
claims adjuster-assist agent client.
"""
from __future__ import annotations

import base64
import hashlib
import http.server
import os
import threading
import time
import urllib.parse
from typing import Optional

import requests


# ---------------------------------------------------------------------------
# PKCE generation
# ---------------------------------------------------------------------------

def generate_pkce_pair() -> tuple[str, str]:
    """Generate a PKCE code_verifier + code_challenge (S256).

    verifier: a 43-character random URL-safe string — the *secret* half,
    never sent until the token exchange, and never sent over a redirect
    (browser history, proxy logs, referrer headers) the way the
    authorization code itself is.
    challenge = BASE64URL( SHA256(verifier) ) — the *public* half, sent in
    the initial authorize redirect. An attacker who intercepts the
    authorization code (e.g. from browser history or a malicious app
    registered for the same custom URI scheme) still cannot redeem it
    without also having the verifier, which never left this process — see
    docs/mcp-auth-deep-dive.md for the worked example."""
    verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode("ascii")
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


# ---------------------------------------------------------------------------
# Loopback callback server
# ---------------------------------------------------------------------------

class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    """Temporary local HTTP server that receives the Authorization Server's
    redirect after the adjuster clicks Allow/Deny in the browser."""

    result: Optional[dict] = None
    _server_ref: Optional[http.server.HTTPServer] = None

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        params = dict(urllib.parse.parse_qsl(parsed.query))
        self.__class__.result = params

        body = b"""
        <html><body>
        <h2>&#10003; Authorization received</h2>
        <p>You can close this window and return to the terminal.</p>
        </body></html>
        """
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

        threading.Thread(target=self._server_ref.shutdown, daemon=True).start()

    def log_message(self, format_, *args) -> None:
        pass


def run_local_callback_server(port: int = 54321, timeout: int = 180) -> dict:
    _CallbackHandler.result = None
    server = http.server.HTTPServer(("127.0.0.1", port), _CallbackHandler)
    _CallbackHandler._server_ref = server

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    deadline = time.time() + timeout
    while _CallbackHandler.result is None:
        if time.time() > deadline:
            server.shutdown()
            raise TimeoutError(f"Timed out after {timeout}s waiting for authorization callback")
        time.sleep(0.2)

    return _CallbackHandler.result


# ---------------------------------------------------------------------------
# Authorization URL
# ---------------------------------------------------------------------------

def build_authorization_url(
    as_metadata: dict, client_id: str, redirect_uri: str, scope: str, state: str, code_challenge: str,
) -> str:
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    base = as_metadata["authorization_endpoint"]
    return f"{base}?{urllib.parse.urlencode(params)}"


# ---------------------------------------------------------------------------
# Token exchange
# ---------------------------------------------------------------------------

def exchange_code_for_token(as_metadata: dict, code: str, code_verifier: str, client_id: str, redirect_uri: str) -> dict:
    """Exchange an authorization code + PKCE verifier for tokens.

    The explicit empty-access_token check below exists because of a real,
    previously-reported failure mode in a community Robinhood MCP client:
    a token endpoint returning HTTP 200 with an empty access_token got
    treated as a successful login. Never assume '200 OK' means 'got a
    usable token' — check the payload."""
    token_url = as_metadata["token_endpoint"]
    resp = requests.post(
        token_url,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "code_verifier": code_verifier,
        },
        timeout=15,
    )

    if not resp.ok:
        raise ValueError(f"Token exchange failed ({resp.status_code}): {resp.text}")

    token_data = resp.json()
    access_token = token_data.get("access_token", "")
    if not access_token:
        raise ValueError("Token response contains no access_token — refusing to treat this as a successful login")

    return token_data


def refresh_access_token(as_metadata: dict, refresh_token: str, client_id: str) -> dict:
    token_url = as_metadata["token_endpoint"]
    resp = requests.post(
        token_url,
        data={"grant_type": "refresh_token", "refresh_token": refresh_token, "client_id": client_id},
        timeout=15,
    )
    if not resp.ok:
        raise ValueError(f"Refresh failed ({resp.status_code}): {resp.text}")
    return resp.json()
