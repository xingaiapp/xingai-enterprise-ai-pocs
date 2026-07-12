"""Claims adjuster-assist agent client — full flow: discovery → PKCE →
token → tool calls → review → human confirmation → submit → idempotency demo.

Run this after starting auth_server (port 8000) and mcp_server (port 8001) —
see README.md Quick Start.
"""
from __future__ import annotations

import base64
import os

import requests

from client.discovery import discover_from_401
from client.oauth import (
    build_authorization_url,
    exchange_code_for_token,
    generate_pkce_pair,
    refresh_access_token,
    run_local_callback_server,
)
from client.token_store import clear_tokens, get_refresh_token, get_valid_access_token, save_tokens

MCP_URL = os.getenv("MCP_URL", "http://localhost:8001/mcp")
CLIENT_ID = "claims-adjuster-assist-client"
REDIRECT_URI = "http://127.0.0.1:54321/callback"
SCOPE = "claims.read policy.read claims.review claims.adjudicate offline_access"
CALLBACK_PORT = 54321

_as_metadata: dict = {}


# ---------------------------------------------------------------------------
# Token management
# ---------------------------------------------------------------------------

def ensure_valid_token() -> str:
    """Priority: cached non-expired token → silent refresh → full PKCE flow."""
    global _as_metadata

    token = get_valid_access_token()
    if token:
        return token

    refresh = get_refresh_token()
    if refresh and _as_metadata:
        try:
            print("→ Access token expiring soon — refreshing silently...")
            token_data = refresh_access_token(_as_metadata, refresh, CLIENT_ID)
            save_tokens(token_data)
            print("✓ Token refreshed")
            return token_data["access_token"]
        except Exception as e:
            print(f"⚠ Refresh failed ({e}) — re-authorizing...")
            clear_tokens()

    return _full_oauth_flow()


def _full_oauth_flow() -> str:
    global _as_metadata

    print("\n=== OAuth 2.1 + PKCE authorization flow ===")

    if not _as_metadata:
        print("→ Discovering Authorization Server...")
        www_auth = _trigger_401_for_discovery()
        _as_metadata = discover_from_401(www_auth)
        print(f"✓ AS issuer: {_as_metadata['issuer']}")

    verifier, challenge = generate_pkce_pair()
    state = base64.urlsafe_b64encode(os.urandom(16)).rstrip(b"=").decode("ascii")

    auth_url = build_authorization_url(_as_metadata, CLIENT_ID, REDIRECT_URI, SCOPE, state, challenge)
    print("\n→ Opening browser for authorization...")
    print(f"  URL: {auth_url[:80]}...")

    import webbrowser
    webbrowser.open(auth_url)

    print("→ Waiting for the adjuster to click 'Allow' in the browser...")
    callback = run_local_callback_server(port=CALLBACK_PORT, timeout=180)

    if callback.get("state") != state:
        raise ValueError("state mismatch — possible CSRF attack!")
    if "error" in callback:
        raise ValueError(f"Authorization denied: {callback['error']}")

    code = callback.get("code")
    if not code:
        raise ValueError("No authorization code in callback")

    print("✓ Received authorization code — exchanging for tokens...")
    token_data = exchange_code_for_token(_as_metadata, code, verifier, CLIENT_ID, REDIRECT_URI)
    save_tokens(token_data)
    print("✓ Tokens obtained and stored (chmod 600)")
    return token_data["access_token"]


def _trigger_401_for_discovery() -> str:
    resp = requests.post(MCP_URL, json={"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}}, timeout=10)
    if resp.status_code != 401:
        raise ValueError(f"Expected 401, got {resp.status_code}")
    www_auth = resp.headers.get("WWW-Authenticate", "")
    if not www_auth:
        raise ValueError("401 response missing WWW-Authenticate header")
    return www_auth


# ---------------------------------------------------------------------------
# MCP RPC calls
# ---------------------------------------------------------------------------

_request_counter = 0


def call_mcp(method: str, params: dict = None, *, retry_on_401: bool = True) -> dict:
    global _request_counter
    _request_counter += 1

    token = ensure_valid_token()
    body = {"jsonrpc": "2.0", "id": _request_counter, "method": method, "params": params or {}}

    resp = requests.post(MCP_URL, json=body, headers={"Authorization": f"Bearer {token}"}, timeout=30)

    if resp.status_code == 401 and retry_on_401:
        print("→ Got 401 — refreshing token and retrying once...")
        clear_tokens()
        return call_mcp(method, params, retry_on_401=False)

    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"MCP error [{data['error'].get('code')}]: {data['error'].get('message')}")
    return data.get("result", {})


# ---------------------------------------------------------------------------
# Main demo flow
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 62)
    print("  XingAI Claims MCP OAuth POC — Adjuster-Assist Agent Client")
    print("  Simulated claims system — no real carrier backend connected")
    print("=" * 62)

    print("\n[1/7] Initialize MCP connection...")
    init_result = call_mcp("initialize")
    server_info = init_result.get("serverInfo", {})
    print(f"✓ Connected: {server_info.get('name')} v{server_info.get('version')}")

    print("\n[2/7] Fetch available tools...")
    tools_result = call_mcp("tools/list")
    tools = tools_result.get("tools", [])
    print(f"✓ Available tools ({len(tools)}):")
    for t in tools:
        print(f"   • {t['name']}: {t.get('description', '')}")

    claim_id = "CLM-8841"
    print(f"\n[3/7] Fetch claim {claim_id}...")
    claim_result = call_mcp("tools/call", {"name": "get_claim", "arguments": {"claim_id": claim_id}})
    claim = claim_result.get("_data", {})
    print(f"✓ {claim.get('claimant_name')} — {claim.get('loss_description')}")
    print(f"  Filed amount: ${claim.get('filed_amount', 0):,.2f}  Status: {claim.get('status')}")

    policy_number = claim.get("policy_number", "")
    print(f"\n[4/7] Fetch policy coverage for {policy_number}...")
    policy_result = call_mcp("tools/call", {"name": "get_policy_coverage", "arguments": {"policy_number": policy_number}})
    policy = policy_result.get("_data", {})
    print(f"✓ {policy.get('policy_type')} ({policy.get('state')})")
    for coverage, terms in policy.get("coverages", {}).items():
        print(f"    {coverage}: limit ${terms['limit']:,} / deductible ${terms['deductible']:,}")

    print(f"\n[5/7] Draft a claim decision (no execution)...")
    review_result = call_mcp("tools/call", {
        "name": "review_claim_decision",
        "arguments": {
            "claim_id": claim_id,
            "decision": "approve",
            "settlement_amount": 640.00,
            "rationale": "Windshield damage confirmed by photo evidence; within glass coverage and agent authority.",
        },
    })
    review = review_result.get("_data", {})

    print(f"\n{'=' * 52}")
    print("  Claim Decision Review")
    print(f"{'=' * 52}")
    print(f"  {review.get('summary', '')}")
    print(f"  Rationale: {review.get('rationale', '')}")
    print(f"  Review ID: {review.get('review_id', '')}")
    print(f"  Valid for: {review.get('expires_in_seconds', 0)} seconds")
    print(f"{'=' * 52}")

    confirm = input("\nType YES to finalize this decision (any other input cancels): ").strip()
    if confirm != "YES":
        print("✗ Cancelled — no claim status changed.")
        return

    print(f"\n[6/7] Submit claim decision (idempotent)...")
    idempotency_key = f"idem_{os.urandom(8).hex()}"

    submit_result = call_mcp("tools/call", {
        "name": "submit_claim_decision",
        "arguments": {"review_id": review["review_id"], "idempotency_key": idempotency_key},
    })
    decision = submit_result.get("_data", {})

    print(f"\n{'=' * 52}")
    print("  Finalized Decision")
    print(f"{'=' * 52}")
    print(f"  Decision ID: {decision.get('decision_id')}")
    print(f"  Claim:       {decision.get('claim_id')}  →  {decision.get('status')}")
    print(f"  {decision.get('decision', '').upper()}  settlement ${decision.get('settlement_amount', 0):,.2f}")
    print(f"  Finalized:   {decision.get('finalized_at')} by {decision.get('finalized_by')}")
    print(f"{'=' * 52}")

    print("\n[7/7] Demonstrating idempotency: retrying with the same idempotency_key...")
    retry_result = call_mcp("tools/call", {
        "name": "submit_claim_decision",
        "arguments": {"review_id": review["review_id"], "idempotency_key": idempotency_key},
    })
    retry_decision = retry_result.get("_data", {})
    print(f"✓ Retry is idempotent: {retry_decision.get('idempotent', False)}, decision_id: {retry_decision.get('decision_id')}")
    assert retry_decision.get("decision_id") == decision.get("decision_id"), "Idempotency broken!"

    print("\n✓ Full flow complete.")


if __name__ == "__main__":
    main()
