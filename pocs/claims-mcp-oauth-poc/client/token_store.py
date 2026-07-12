"""Token persistence for the claims adjuster-assist agent client.

File-based for the demo; a real agent deployment should use the OS
keychain (`keyring` package) or a secrets manager, never a plaintext file —
this token, unlike a browser cookie, is a bearer credential that can read
claim files and finalize settlements up to the agent's authority limit.
"""
from __future__ import annotations

import json
import os
import stat
import time
from pathlib import Path
from typing import Optional

TOKEN_FILE = Path(os.getenv("MCP_TOKEN_FILE", ".claims_mcp_tokens.json"))

# Proactively refresh when less than this many seconds remain — avoids a
# request failing mid-flight with an expired token.
REFRESH_BUFFER_SECONDS = 60


def save_tokens(token_response: dict) -> None:
    data = {
        "access_token": token_response.get("access_token"),
        "refresh_token": token_response.get("refresh_token"),
        "scope": token_response.get("scope"),
        "expires_at": time.time() + int(token_response.get("expires_in", 300)),
        "saved_at": time.time(),
    }
    if not data["access_token"]:
        raise ValueError("Refusing to store an empty access_token")

    TOKEN_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.chmod(TOKEN_FILE, stat.S_IRUSR | stat.S_IWUSR)   # chmod 600


def load_tokens() -> Optional[dict]:
    if not TOKEN_FILE.exists():
        return None
    try:
        return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def get_valid_access_token() -> Optional[str]:
    tokens = load_tokens()
    if not tokens:
        return None
    access_token = tokens.get("access_token")
    expires_at = tokens.get("expires_at", 0)
    if not access_token:
        return None
    if time.time() + REFRESH_BUFFER_SECONDS >= expires_at:
        return None
    return access_token


def get_refresh_token() -> Optional[str]:
    tokens = load_tokens()
    return tokens.get("refresh_token") if tokens else None


def clear_tokens() -> None:
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
