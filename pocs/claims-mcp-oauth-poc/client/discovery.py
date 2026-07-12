"""OAuth discovery chain: 401 → Protected Resource Metadata → Authorization
Server Metadata (RFC 9728 + RFC 8414). This is the mechanism that lets the
same claims adjuster-assist agent binary work against any carrier's claims
MCP server without a hardcoded per-carrier auth config — see
docs/mcp-auth-deep-dive.md §"Why discovery matters for MCP specifically".
"""
from __future__ import annotations

import re
import urllib.parse

import requests

# SSRF guard: demo only allows localhost-type Authorization Server URLs.
# A real deployment would allowlist the carrier's known IdP hosts instead of
# blindly trusting whatever authorization_servers URL a resource happens to
# advertise — otherwise a compromised/malicious claims MCP server could
# point the agent at an attacker-controlled "Authorization Server" and
# harvest whatever the agent sends it next.
ALLOWED_AS_HOSTS = {"localhost", "127.0.0.1"}


def discover_from_401(www_authenticate: str) -> dict:
    resource_metadata_url = _extract_resource_metadata_url(www_authenticate)
    resource_metadata = _fetch_resource_metadata(resource_metadata_url)
    as_metadata = _fetch_as_metadata(resource_metadata)
    _validate_as_metadata(as_metadata)
    return as_metadata


def _extract_resource_metadata_url(www_authenticate: str) -> str:
    match = re.search(r'resource_metadata="([^"]+)"', www_authenticate)
    if not match:
        raise ValueError(f"No resource_metadata in WWW-Authenticate header: {www_authenticate}")
    url = match.group(1)
    _check_ssrf(url)
    return url


def _fetch_resource_metadata(url: str) -> dict:
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if "authorization_servers" not in data or not data["authorization_servers"]:
        raise ValueError("Resource Metadata missing authorization_servers")
    return data


def _fetch_as_metadata(resource_metadata: dict) -> dict:
    as_base = resource_metadata["authorization_servers"][0]
    _check_ssrf(as_base)
    metadata_url = f"{as_base.rstrip('/')}/.well-known/oauth-authorization-server"
    resp = requests.get(metadata_url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _validate_as_metadata(metadata: dict) -> None:
    for field in ("issuer", "authorization_endpoint", "token_endpoint", "jwks_uri"):
        if field not in metadata:
            raise ValueError(f"AS Metadata missing required field: {field}")

    pkce_methods = metadata.get("code_challenge_methods_supported", [])
    if "S256" not in pkce_methods:
        # A claims agent must refuse to talk to an Authorization Server that
        # can't do PKCE — see docs/mcp-auth-deep-dive.md for what breaks
        # without it (authorization code interception).
        raise ValueError("AS does not support S256 PKCE — refusing to connect")


def _check_ssrf(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    hostname = parsed.hostname or ""
    if hostname not in ALLOWED_AS_HOSTS:
        raise ValueError(f"SSRF guard: non-localhost AS not allowed ({hostname})")
