"""Thread-safe in-memory storage for the demo Authorization Server.

Replace with PostgreSQL (codes/clients) + Redis (short-TTL codes) before any
real deployment — see README.md "Not Production Yet".
"""
from __future__ import annotations

import threading
from typing import Optional

from auth_server.models import (
    AuthorizationCodeRecord,
    ClientRegistration,
    RefreshTokenRecord,
)


class InMemoryStorage:
    """Demo-only. Everything here is lost on process restart — fine for a
    POC, disqualifying for production (a restart would silently log every
    active adjuster-assist agent out)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._codes: dict[str, AuthorizationCodeRecord] = {}
        self._refresh_tokens: dict[str, RefreshTokenRecord] = {}
        self._clients: dict[str, ClientRegistration] = {}

    # ---- Authorization Codes -----------------------------------------------

    def save_code(self, record: AuthorizationCodeRecord) -> None:
        with self._lock:
            self._codes[record.code] = record

    def get_code(self, code: str) -> Optional[AuthorizationCodeRecord]:
        with self._lock:
            return self._codes.get(code)

    def mark_code_used(self, code: str) -> None:
        with self._lock:
            if code in self._codes:
                self._codes[code].used = True

    # ---- Refresh Tokens ------------------------------------------------------

    def save_refresh_token(self, record: RefreshTokenRecord) -> None:
        with self._lock:
            self._refresh_tokens[record.token] = record

    def get_refresh_token(self, token: str) -> Optional[RefreshTokenRecord]:
        with self._lock:
            return self._refresh_tokens.get(token)

    def revoke_refresh_token(self, token: str) -> None:
        with self._lock:
            if token in self._refresh_tokens:
                self._refresh_tokens[token].revoked = True

    # ---- Client Registrations -------------------------------------------------

    def save_client(self, client: ClientRegistration) -> None:
        with self._lock:
            self._clients[client.client_id] = client

    def get_client(self, client_id: str) -> Optional[ClientRegistration]:
        with self._lock:
            return self._clients.get(client_id)


# Process-wide singleton
storage = InMemoryStorage()

# Pre-seed the demo claims adjuster-assist client — in a real branch-office
# rollout this registration step would happen once per deployed agent, not
# be hardcoded like this.
storage.save_client(ClientRegistration(
    client_id="claims-adjuster-assist-client",
    redirect_uris=["http://127.0.0.1:54321/callback"],
    client_name="Claims Adjuster-Assist Agent (Demo)",
))
