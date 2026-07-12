"""Authorization Server unit tests: PKCE, metadata discovery, client
registration, token exchange."""
from fastapi.testclient import TestClient

from auth_server.main import app
from auth_server.security import verify_pkce
from client.oauth import generate_pkce_pair

client = TestClient(app)


class TestPKCE:
    def test_pkce_valid(self):
        verifier, challenge = generate_pkce_pair()
        assert verify_pkce(verifier, challenge) is True

    def test_pkce_invalid_verifier(self):
        _, challenge = generate_pkce_pair()
        assert verify_pkce("wrong_verifier_abc123", challenge) is False

    def test_pkce_tampered_challenge(self):
        verifier, _ = generate_pkce_pair()
        assert verify_pkce(verifier, "tampered_challenge_xyz") is False


class TestMetadataEndpoints:
    def test_as_metadata_returns_required_fields(self):
        resp = client.get("/.well-known/oauth-authorization-server")
        assert resp.status_code == 200
        data = resp.json()
        assert "issuer" in data
        assert "authorization_endpoint" in data
        assert "token_endpoint" in data
        assert "jwks_uri" in data
        assert "S256" in data.get("code_challenge_methods_supported", [])
        assert "claims.adjudicate" in data["scopes_supported"]

    def test_jwks_returns_rsa_key(self):
        resp = client.get("/jwks.json")
        assert resp.status_code == 200
        data = resp.json()
        assert "keys" in data and len(data["keys"]) > 0
        key = data["keys"][0]
        assert key["kty"] == "RSA"
        assert key["alg"] == "RS256"
        assert "n" in key and "e" in key


class TestClientRegistration:
    def test_register_loopback_client(self):
        resp = client.post("/register", json={
            "client_name": "Test Adjuster-Assist Client",
            "redirect_uris": ["http://127.0.0.1:9999/callback"],
            "token_endpoint_auth_method": "none",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "client_id" in data
        assert data["redirect_uris"] == ["http://127.0.0.1:9999/callback"]

    def test_register_non_loopback_rejected(self):
        resp = client.post("/register", json={
            "client_name": "Evil Client",
            "redirect_uris": ["https://evil.example.com/steal"],
            "token_endpoint_auth_method": "none",
        })
        assert resp.status_code == 400


class TestTokenExchange:
    def _get_authorization_code(self, scope: str = "claims.read offline_access") -> tuple[str, str]:
        from auth_server.storage import storage
        from auth_server.models import AuthorizationCodeRecord
        from auth_server.security import generate_secure_token

        verifier, challenge = generate_pkce_pair()
        code = generate_secure_token(24)

        storage.save_code(AuthorizationCodeRecord(
            code=code,
            client_id="claims-adjuster-assist-client",
            redirect_uri="http://127.0.0.1:54321/callback",
            user_id="demo-adjuster-001",
            scope=scope,
            code_challenge=challenge,
        ))
        return code, verifier

    def test_token_exchange_valid_pkce(self):
        code, verifier = self._get_authorization_code()
        resp = client.post("/token", data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "http://127.0.0.1:54321/callback",
            "client_id": "claims-adjuster-assist-client",
            "code_verifier": verifier,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["access_token"]
        assert "refresh_token" in data   # offline_access scope → expect a refresh token

    def test_token_exchange_omits_refresh_without_offline_access(self):
        code, verifier = self._get_authorization_code(scope="claims.read")
        resp = client.post("/token", data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "http://127.0.0.1:54321/callback",
            "client_id": "claims-adjuster-assist-client",
            "code_verifier": verifier,
        })
        assert resp.status_code == 200
        assert resp.json().get("refresh_token") is None

    def test_token_exchange_invalid_pkce(self):
        code, _ = self._get_authorization_code()
        resp = client.post("/token", data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "http://127.0.0.1:54321/callback",
            "client_id": "claims-adjuster-assist-client",
            "code_verifier": "wrong_verifier_that_definitely_fails",
        })
        assert resp.status_code == 400
        assert "pkce" in resp.text.lower()

    def test_authorization_code_single_use(self):
        code, verifier = self._get_authorization_code()

        resp1 = client.post("/token", data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "http://127.0.0.1:54321/callback",
            "client_id": "claims-adjuster-assist-client",
            "code_verifier": verifier,
        })
        assert resp1.status_code == 200

        resp2 = client.post("/token", data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "http://127.0.0.1:54321/callback",
            "client_id": "claims-adjuster-assist-client",
            "code_verifier": verifier,
        })
        assert resp2.status_code == 400

    def test_refresh_token_rotation_revokes_old_token(self):
        code, verifier = self._get_authorization_code()
        first = client.post("/token", data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "http://127.0.0.1:54321/callback",
            "client_id": "claims-adjuster-assist-client",
            "code_verifier": verifier,
        }).json()
        old_refresh = first["refresh_token"]

        refreshed = client.post("/token", data={
            "grant_type": "refresh_token",
            "refresh_token": old_refresh,
            "client_id": "claims-adjuster-assist-client",
        })
        assert refreshed.status_code == 200
        assert refreshed.json()["refresh_token"] != old_refresh

        # Replaying the now-rotated old refresh token must fail.
        replay = client.post("/token", data={
            "grant_type": "refresh_token",
            "refresh_token": old_refresh,
            "client_id": "claims-adjuster-assist-client",
        })
        assert replay.status_code == 400
