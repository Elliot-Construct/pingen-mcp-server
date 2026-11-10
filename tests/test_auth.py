"""Auth tests - criterion c2: client-credentials fetch, authorization-code
exchange, and refresh rotation, all with zero network (httpx.MockTransport)."""

from __future__ import annotations

import json
import urllib.parse
from pathlib import Path

import httpx
import pytest

from pingen_mcp_server.auth import (
    AuthorizationCodeProvider,
    AuthError,
    ClientCredentialsProvider,
    TokenSet,
    TokenStore,
    build_authorize_url,
    generate_code_verifier,
    provider_for,
)
from pingen_mcp_server.config import load_config

TOKEN_PATH = "/auth/access-tokens"


class Clock:
    def __init__(self, now: float = 1_700_000_000.0):
        self.now = now

    def __call__(self) -> float:
        return self.now


def form_body(request: httpx.Request) -> dict[str, str]:
    return {
        k: v[0]
        for k, v in urllib.parse.parse_qs(request.content.decode()).items()
    }


def token_config(tmp_path: Path, **extra: str):
    env = {
        "PINGEN_TOKEN_FILE": str(tmp_path / "tokens.json"),
        "PINGEN_CLIENT_ID": "test-client-id",
        "PINGEN_CLIENT_SECRET": "test-client-secret",
        **extra,
    }
    return load_config(env)


def counting_transport(handler):
    calls: list[httpx.Request] = []

    def wrapped(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return handler(request)

    return httpx.MockTransport(wrapped), calls


# ---------------------------------------------------------------------------
# Client-credentials grant
# ---------------------------------------------------------------------------


def test_client_credentials_fetches_and_persists(tmp_path, store):
    config = token_config(tmp_path, PINGEN_SCOPES="letter")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "identity.pingen.com"
        assert request.url.path == TOKEN_PATH
        body = form_body(request)
        assert body["grant_type"] == "client_credentials"
        assert body["client_id"] == "test-client-id"
        assert body["client_secret"] == "test-client-secret"
        assert body["scope"] == "letter"
        return httpx.Response(
            200, json={"token_type": "Bearer", "expires_in": 43200, "access_token": "cc-token"}
        )

    clock = Clock()
    provider = ClientCredentialsProvider(
        config, store, transport=httpx.MockTransport(handler), clock=clock
    )
    assert provider.get_token() == "cc-token"

    saved = store.load("client_credentials")
    assert saved is not None
    assert saved.access_token == "cc-token"
    assert saved.refresh_token is None  # this grant issues no refresh token
    assert saved.expires_at == clock.now + 43200
    assert json.loads(Path(config.token_file).read_text())["grant_type"] == "client_credentials"


def test_client_credentials_token_cached_within_skew(tmp_path, store):
    config = token_config(tmp_path)
    transport, calls = counting_transport(
        lambda r: httpx.Response(200, json={"access_token": "t", "expires_in": 43200})
    )
    clock = Clock()
    provider = ClientCredentialsProvider(config, store, transport=transport, clock=clock)
    provider.get_token()
    clock.now += 43200 - 61  # still inside expires_at - 60s window
    provider.get_token()
    assert len(calls) == 1


def test_client_credentials_refetched_at_skew_boundary(tmp_path, store):
    config = token_config(tmp_path)
    transport, calls = counting_transport(
        lambda r: httpx.Response(200, json={"access_token": "t", "expires_in": 43200})
    )
    clock = Clock()
    provider = ClientCredentialsProvider(config, store, transport=transport, clock=clock)
    provider.get_token()
    clock.now += 43200 - 60  # boundary: now < expires_at - skew is False
    provider.get_token()
    assert len(calls) == 2


def test_client_credentials_requires_credentials(tmp_path, store):
    config = load_config({"PINGEN_TOKEN_FILE": str(tmp_path / "tokens.json")})

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no HTTP must happen without credentials")

    provider = ClientCredentialsProvider(
        config, store, transport=httpx.MockTransport(handler)
    )
    with pytest.raises(AuthError) as exc:
        provider.get_token()
    assert "PINGEN_CLIENT_ID" in str(exc.value)


def test_token_endpoint_http_error_raises_auth_error(tmp_path, store):
    config = token_config(tmp_path)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid_client"})

    provider = ClientCredentialsProvider(
        config, store, transport=httpx.MockTransport(handler)
    )
    with pytest.raises(AuthError) as exc:
        provider.get_token()
    assert "401" in str(exc.value)


# ---------------------------------------------------------------------------
# Authorization-code grant
# ---------------------------------------------------------------------------


def test_authorize_url_shape(tmp_path, store):
    config = token_config(
        tmp_path,
        PINGEN_REDIRECT_URI="http://localhost:8080/callback",
        PINGEN_SCOPES="letter batch",
    )
    provider = AuthorizationCodeProvider(config, store)
    result = provider.build_authorize_url()
    assert set(result) == {"url", "state", "code_verifier"}
    verifier = result["code_verifier"]
    assert len(verifier) == 43 and verifier.isalnum()  # docs: exactly 43 chars

    from urllib.parse import parse_qs, urlsplit

    parts = urlsplit(result["url"])
    assert (parts.scheme, parts.hostname, parts.path) == (
        "https",
        "identity.pingen.com",
        "/auth/authorize",
    )
    params = parse_qs(parts.query)
    assert params["response_type"] == ["code"]
    assert params["state"] == [result["state"]]
    assert params["code_challenge"] == [verifier]
    assert params["client_id"] == ["test-client-id"]
    assert params["redirect_uri"] == ["http://localhost:8080/callback"]
    assert params["scope"] == ["letter batch"]


def test_authorize_url_requires_redirect(tmp_path, store):
    config = token_config(tmp_path)
    with pytest.raises(AuthError) as exc:
        build_authorize_url(config, state="s", code_verifier=generate_code_verifier())
    assert "redirect_uri" in str(exc.value)


def test_exchange_code_persists_tokens(tmp_path, store):
    config = token_config(tmp_path, PINGEN_REDIRECT_URI="http://localhost:8080/callback")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "identity.pingen.com"
        assert request.url.path == TOKEN_PATH
        body = form_body(request)
        assert body["grant_type"] == "authorization_code"
        assert body["client_id"] == "test-client-id"
        assert body["client_secret"] == "test-client-secret"
        assert body["redirect_uri"] == "http://localhost:8080/callback"
        assert body["code"] == "the-code"
        assert body["code_verifier"] == "v" * 43
        return httpx.Response(
            200,
            json={
                "token_type": "Bearer",
                "expires_in": 43200,
                "access_token": "ac-token",
                "refresh_token": "refresh-1",
            },
        )

    clock = Clock()
    provider = AuthorizationCodeProvider(
        config, store, transport=httpx.MockTransport(handler), clock=clock
    )
    tokens = provider.exchange_code(
        code="the-code", code_verifier="v" * 43, state="st", expected_state="st"
    )
    assert tokens.access_token == "ac-token"
    assert tokens.refresh_token == "refresh-1"

    saved = store.load("authorization_code")
    assert saved is not None
    assert saved.access_token == "ac-token"
    assert saved.refresh_token == "refresh-1"
    assert saved.expires_at == clock.now + 43200


def test_exchange_state_mismatch_refuses_without_http(tmp_path, store):
    config = token_config(tmp_path, PINGEN_REDIRECT_URI="http://cb")

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no HTTP must happen on state mismatch")

    provider = AuthorizationCodeProvider(
        config, store, transport=httpx.MockTransport(handler)
    )
    with pytest.raises(AuthError) as exc:
        provider.exchange_code(
            code="c", code_verifier="v" * 43, state="attacker", expected_state="mine"
        )
    assert "state mismatch" in str(exc.value)


def test_get_token_without_exchange_raises(tmp_path, store):
    config = token_config(tmp_path)
    provider = AuthorizationCodeProvider(config, store)
    with pytest.raises(AuthError) as exc:
        provider.get_token()
    assert "no authorization-code tokens" in str(exc.value)


def test_expired_token_refreshed_and_rotation_persisted(tmp_path, store):
    config = token_config(tmp_path)
    clock = Clock()
    store.save(
        TokenSet(
            access_token="old-token",
            expires_at=clock.now - 1,
            grant_type="authorization_code",
            refresh_token="refresh-1",
        )
    )

    def handler(request: httpx.Request) -> httpx.Response:
        body = form_body(request)
        assert body["grant_type"] == "refresh_token"
        assert body["refresh_token"] == "refresh-1"  # the stored one
        return httpx.Response(
            200,
            json={
                "access_token": "new-token",
                "expires_in": 43200,
                "refresh_token": "refresh-2",
            },
        )

    provider = AuthorizationCodeProvider(
        config, store, transport=httpx.MockTransport(handler), clock=clock
    )
    assert provider.get_token() == "new-token"

    saved = store.load("authorization_code")
    assert saved is not None
    assert saved.access_token == "new-token"
    assert saved.refresh_token == "refresh-2"  # rotated value won, old is revoked


def test_refresh_response_without_new_refresh_token_keeps_old(tmp_path, store):
    config = token_config(tmp_path)
    clock = Clock()
    store.save(
        TokenSet(
            access_token="old",
            expires_at=clock.now - 1,
            grant_type="authorization_code",
            refresh_token="keep-me",
        )
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"access_token": "fresh", "expires_in": 43200}
        )

    provider = AuthorizationCodeProvider(
        config, store, transport=httpx.MockTransport(handler), clock=clock
    )
    assert provider.get_token() == "fresh"
    saved = store.load("authorization_code")
    assert saved is not None and saved.refresh_token == "keep-me"


# ---------------------------------------------------------------------------
# Store + selection
# ---------------------------------------------------------------------------


def test_token_store_ignores_wrong_grant_and_corrupt_files(tmp_path):
    path = tmp_path / "tokens.json"
    store = TokenStore(path)
    store.save(TokenSet(access_token="a", expires_at=1, grant_type="client_credentials"))
    assert store.load("authorization_code") is None
    path.write_text("{not json", encoding="utf-8")
    assert store.load("client_credentials") is None


def test_provider_for_selects_by_grant(tmp_path):
    cc = token_config(tmp_path)
    ac = token_config(tmp_path, PINGEN_GRANT_TYPE="authorization_code")
    assert isinstance(provider_for(cc), ClientCredentialsProvider)
    assert isinstance(provider_for(ac), AuthorizationCodeProvider)
