"""Claims MCP Server authentication and scope tests."""
from fastapi.testclient import TestClient

from mcp_server.main import app

client = TestClient(app)


def _make_rpc(method: str, params: dict = None, token: str = None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
        headers=headers,
    )


class TestMcpRequiresAuthentication:
    def test_tools_list_without_token_returns_401(self):
        resp = _make_rpc("tools/list")
        assert resp.status_code == 401

    def test_401_includes_resource_metadata_header(self):
        resp = _make_rpc("tools/list")
        assert resp.status_code == 401
        www_auth = resp.headers.get("www-authenticate", "")
        assert "resource_metadata" in www_auth
        assert "localhost:8001" in www_auth

    def test_tools_call_without_token_returns_401(self):
        resp = _make_rpc("tools/call", {"name": "get_claim", "arguments": {"claim_id": "CLM-8841"}})
        assert resp.status_code == 401

    def test_invalid_jwt_returns_401(self):
        resp = _make_rpc("tools/list", token="eyJhbGciOiJIUzI1NiJ9.fake.payload")
        assert resp.status_code in (401, 200)
        if resp.status_code == 200:
            assert "error" in resp.json()

    def test_initialize_without_any_token_returns_401_to_trigger_discovery(self):
        """A token-less call is the deliberate discovery trigger a fresh
        client uses (see client/main.py's _trigger_401_for_discovery) — even
        `initialize` requires *a* Bearer-shaped header to be present (its
        validity isn't checked at this layer, only its presence), so that a
        client with zero prior state gets a 401 + WWW-Authenticate to bootstrap
        from, rather than a misleadingly successful handshake with no way to
        then call any real tool."""
        resp = _make_rpc("initialize")
        assert resp.status_code == 401
        assert "resource_metadata" in resp.headers.get("www-authenticate", "")


class TestProtectedResourceMetadata:
    def test_resource_metadata_endpoint(self):
        resp = client.get("/.well-known/oauth-protected-resource/mcp")
        assert resp.status_code == 200
        data = resp.json()
        assert "authorization_servers" in data
        assert "localhost:8000" in data["authorization_servers"][0]
        assert "claims.adjudicate" in data["scopes_supported"]
