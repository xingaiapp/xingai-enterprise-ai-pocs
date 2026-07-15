"""Thin MCP client claims_workflow uses to reach mcp_server's tools.

Two transports, same JSON-RPC /mcp protocol either way:

- In-process (default): httpx.ASGITransport wired directly to the
  mcp_server FastAPI app — no separate process, no open socket, but every
  call still goes through the real JSON-RPC handler (auth, scope checks,
  tool dispatch), the same code path that would run over the network. This
  is what lets this POC's own pytest suite and `uvicorn ... --reload` dev
  server run with zero extra setup.
- Real HTTP: set MCP_SERVER_URL (e.g. in docker-compose, where mcp_server
  runs as its own container) and this client talks to it over the network
  like any other MCP client would.
"""
from __future__ import annotations

import os
from typing import Any, Optional

import httpx


class MCPToolError(RuntimeError):
    def __init__(self, code: int, message: str):
        super().__init__(f"MCP tool error {code}: {message}")
        self.code = code
        self.message = message


class MCPClient:
    def __init__(self, http_client: httpx.Client, token: str):
        self._http = http_client
        self._token = token
        self._next_id = 0

    def call_tool(self, name: str, arguments: dict) -> Any:
        self._next_id += 1
        resp = self._http.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": self._next_id, "method": "tools/call", "params": {"name": name, "arguments": arguments}},
            headers={"Authorization": f"Bearer {self._token}"},
        )
        resp.raise_for_status()
        body = resp.json()
        if "error" in body:
            raise MCPToolError(body["error"]["code"], body["error"]["message"])
        return body["result"]["_data"]


_client: Optional[MCPClient] = None


def get_client() -> MCPClient:
    """Module-level singleton — matches how a real service would hold one
    connection pool for the process lifetime rather than reconnect per call."""
    global _client
    if _client is not None:
        return _client

    token = os.getenv("MCP_SERVICE_TOKEN", "dev-internal-service-token")
    server_url = os.getenv("MCP_SERVER_URL")

    if server_url:
        http_client: httpx.Client = httpx.Client(base_url=server_url, timeout=10.0, trust_env=False)
    else:
        # In-process: TestClient bridges the sync call into the async ASGI
        # app for us (same mechanism FastAPI's own test suite uses) — the
        # request still goes through the real JSON-RPC handler in
        # mcp_server.main, just without an actual TCP socket.
        from starlette.testclient import TestClient

        from mcp_server.main import app as mcp_app  # local import: avoid importing the app at module load if unused

        http_client = TestClient(mcp_app, base_url="http://claims-workflow-mcp-server")

    _client = MCPClient(http_client, token)
    return _client


def reset_client_for_tests() -> None:
    """Drop the cached client so the next get_client() call re-reads env
    vars — used when a test wants to point at a different transport."""
    global _client
    _client = None
