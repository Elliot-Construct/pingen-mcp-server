"""Resource-server auth on the streamable-HTTP transport (PINGEN-02 c1/c2).

No network: the identity layer's JWKS is replaced by a locally generated RSA
key pair so issuer/audience/expiry enforcement is exercised for real while the
suite stays offline. The deployed wiring (JWKS URI + issuer + audience from
config) is asserted separately in ``test_auth_provider_is_wired_from_config``.
"""

from __future__ import annotations

import time

import jwt as pyjwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastmcp.server.auth import JWTVerifier, RemoteAuthProvider
from starlette.testclient import TestClient

from pingen_mcp_server.config import HttpConfig
from pingen_mcp_server.server import (
    build_auth_provider,
    build_server,
    http_allowed_hosts,
)

PUBLIC_URL = "https://pingen-mcp.datawyse.ai/mcp"
HOST = "pingen-mcp.datawyse.ai"
ISSUER = "https://idp.example/realms/estate/"
AUDIENCE = PUBLIC_URL
JWKS_URI = "https://idp.example/realms/estate/protocol/openid-connect/certs"

# One RSA key per test session: private signs tokens, public verifies them.
_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PRIVATE_PEM = _KEY.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
)
_PUBLIC_PEM = _KEY.public_key().public_bytes(
    serialization.Encoding.PEM,
    serialization.PublicFormat.SubjectPublicKeyInfo,
)

INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "auth-test", "version": "0"},
    },
}
JSON_HEADERS = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
}


def make_cfg() -> HttpConfig:
    return HttpConfig(
        public_url=PUBLIC_URL,
        bind="127.0.0.1",
        port=8747,
        issuer=ISSUER,
        jwks_uri=JWKS_URI,
        audience=AUDIENCE,
    )


def make_app():
    cfg = make_cfg()
    verifier = JWTVerifier(
        public_key=_PUBLIC_PEM,
        algorithm="RS256",
        issuer=cfg.issuer,
        audience=cfg.audience,
    )
    provider = RemoteAuthProvider(
        token_verifier=verifier,
        authorization_servers=[cfg.issuer],
        # origin, not public_url: RemoteAuthProvider appends /mcp itself
        base_url=f"https://{HOST}",
        resource_name="Pingen MCP",
    )
    server = build_server(get_client_fn=lambda: None, auth=provider)
    # Same allowlist and strict Host guard serve_http uses, so the deployed
    # behaviour is what these tests exercise.
    return server.http_app(
        allowed_hosts=http_allowed_hosts(cfg),
        host_origin_protection=True,
    )


def mint(
    *,
    iss: str = ISSUER,
    aud: str = AUDIENCE,
    lifetime: int = 3600,
    iat: int | None = None,
) -> str:
    now = int(time.time()) if iat is None else iat
    return pyjwt.encode(
        {"iss": iss, "aud": aud, "sub": "tester", "iat": now, "exp": now + lifetime},
        _PRIVATE_PEM,
        algorithm="RS256",
    )


def client() -> TestClient:
    # TestClient runs the app's lifespan, which starts the streamable-HTTP
    # session manager (ASGITransport alone leaves it uninitialized).
    return TestClient(make_app(), base_url=f"https://{HOST}")


def initialize(c: TestClient, token: str | None, host: str | None = None):
    headers = dict(JSON_HEADERS)
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    if host is not None:
        headers["Host"] = host
    return c.post("/mcp", json=INITIALIZE, headers=headers)


def test_anonymous_initialize_gets_401_challenge():
    with client() as c:
        resp = initialize(c, None)
    assert resp.status_code == 401
    www = resp.headers.get("www-authenticate", "")
    assert www.startswith("Bearer")
    assert "resource_metadata=" in www
    assert "/.well-known/oauth-protected-resource" in www


def test_protected_resource_metadata_is_public_and_names_the_as():
    """RFC 9728 §3.1: the URL in the 401 challenge must answer without auth."""
    with client() as c:
        challenge = initialize(c, None)
        www = challenge.headers.get("www-authenticate", "")
        metadata_url = www.split('resource_metadata="', 1)[1].split('"', 1)[0]
        assert metadata_url == (
            f"https://{HOST}/.well-known/oauth-protected-resource/mcp"
        )
        doc = c.get(metadata_url.replace(f"https://{HOST}", ""))
    assert doc.status_code == 200, doc.text
    assert doc.json()["authorization_servers"] == [ISSUER]
    assert doc.json()["resource"] == PUBLIC_URL


def test_valid_identity_layer_token_completes_initialize():
    with client() as c:
        resp = initialize(c, mint())
    assert resp.status_code == 200, resp.text
    assert "initialize" in resp.text or "result" in resp.text


def test_token_from_another_issuer_is_rejected():
    with client() as c:
        resp = initialize(c, mint(iss="https://idp.example/realms/other/"))
    assert resp.status_code == 401


def test_token_minted_for_another_audience_is_rejected():
    with client() as c:
        resp = initialize(c, mint(aud="https://someone-else.example/mcp"))
    assert resp.status_code == 401


def test_expired_token_is_rejected():
    now = int(time.time())
    with client() as c:
        resp = initialize(c, mint(iat=now - 7200, lifetime=3600))
    assert resp.status_code == 401


def test_garbage_token_is_rejected():
    with client() as c:
        resp = initialize(c, "not-a-jwt")
    assert resp.status_code == 401


class HostOverride:
    """ASGI wrapper that rewrites the Host header (httpx won't set it)."""

    def __init__(self, app, host: str):
        self.app = app
        self.host = host

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            scope = dict(scope)
            scope["headers"] = [
                (b"host", self.host.encode()) if k == b"host" else (k, v)
                for k, v in scope["headers"]
            ]
        return await self.app(scope, receive, send)


def test_spoofed_host_is_refused_before_auth():
    with client() as c:
        baseline = initialize(c, mint())  # correct Host passes the guard
    assert baseline.status_code != 421

    with TestClient(HostOverride(make_app(), "evil.example"), base_url=f"https://{HOST}") as c:
        evil = initialize(c, mint())
    assert evil.status_code == 421


def test_auth_provider_is_wired_from_config():
    provider = build_auth_provider(make_cfg())
    assert isinstance(provider, RemoteAuthProvider)
    verifier = provider.token_verifier
    assert isinstance(verifier, JWTVerifier)
    assert verifier.issuer == ISSUER
    assert verifier.jwks_uri == JWKS_URI
    assert verifier.audience == AUDIENCE
    assert [str(s) for s in provider.authorization_servers] == [ISSUER]


def test_tools_list_still_reports_49_over_http():
    """The transport change must not alter the tool inventory."""
    with client() as c:
        init = initialize(c, mint())
        assert init.status_code == 200, init.text
        headers = dict(JSON_HEADERS)
        headers["Authorization"] = f"Bearer {mint()}"
        session = init.headers.get("mcp-session-id")
        if session:
            headers["mcp-session-id"] = session
        listing = c.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            headers=headers,
        )
    assert listing.status_code == 200, listing.text
    assert '"tools"' in listing.text
    assert listing.text.count('"name"') >= 49
