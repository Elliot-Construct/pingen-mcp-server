"""OAuth 2.0 support for both Pingen grants.

- Client credentials: server-to-server; token cached until ``expires_in`` minus
  a 60 s skew, then re-fetched (Pingen issues no refresh token for this grant).
- Authorization code: delegated end-user access; authorize URL per the official
  docs (43-character alphanumeric ``code_verifier`` used as ``code_challenge``),
  code exchange, and refresh with rotation - Pingen REVOKES the used refresh
  token, so the new one is persisted before the next request.

Token material lives in memory and in a token file outside the repository.
"""

from __future__ import annotations

import json
import secrets
import string
import time
import urllib.parse
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx

from .config import Config

TOKEN_ENDPOINT_PATH = "/auth/access-tokens"
AUTHORIZE_ENDPOINT_PATH = "/auth/authorize"
SKEW_SECONDS = 60.0
CODE_VERIFIER_LENGTH = 43  # official docs: exactly 43 alphanumerical characters
DEFAULT_EXPIRES_IN = 3600.0


class AuthError(RuntimeError):
    """Authentication failure. Messages never contain secret values."""


@dataclass
class TokenSet:
    access_token: str
    expires_at: float  # epoch seconds
    grant_type: str
    token_type: str = "Bearer"
    refresh_token: str | None = None


def generate_state() -> str:
    return secrets.token_urlsafe(32)


def generate_code_verifier() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(CODE_VERIFIER_LENGTH))


def build_authorize_url(
    config: Config,
    *,
    state: str,
    code_verifier: str,
    redirect_uri: str | None = None,
    scope: str | None = None,
) -> str:
    """Build the ``/auth/authorize`` URL for step 1 of the authorization-code flow."""
    if not config.client_id:
        raise AuthError("PINGEN_CLIENT_ID is not configured")
    redirect = redirect_uri or config.redirect_uri
    if not redirect:
        raise AuthError("redirect_uri is required (set PINGEN_REDIRECT_URI or pass redirect_uri)")
    params: dict[str, str] = {
        "response_type": "code",
        "state": state,
        "code_challenge": code_verifier,
        "client_id": config.client_id,
        "redirect_uri": redirect,
    }
    scope_value = scope or (" ".join(config.scopes) if config.scopes else None)
    if scope_value:
        params["scope"] = scope_value
    return (
        config.identity_base_url
        + AUTHORIZE_ENDPOINT_PATH
        + "?"
        + urllib.parse.urlencode(params)
    )


class TokenStore:
    """File-backed token store. The path is always outside the repository."""

    def __init__(self, path: Path):
        self.path = path

    def load(self, grant_type: str) -> TokenSet | None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(data, dict) or data.get("grant_type") != grant_type:
            return None
        try:
            return TokenSet(
                access_token=str(data["access_token"]),
                expires_at=float(data["expires_at"]),
                grant_type=str(data["grant_type"]),
                token_type=str(data.get("token_type", "Bearer")),
                refresh_token=data.get("refresh_token"),
            )
        except (KeyError, TypeError, ValueError):
            return None

    def save(self, tokens: TokenSet) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(json.dumps(asdict(tokens), indent=2), encoding="utf-8")
        tmp.replace(self.path)  # atomic on POSIX and Windows


class TokenProvider:
    """Base class: POSTs form-encoded grants to the identity token endpoint."""

    def __init__(
        self,
        config: Config,
        store: TokenStore,
        *,
        transport: httpx.BaseTransport | None = None,
        clock: Callable[[], float] = time.time,
    ):
        self._config = config
        self._store = store
        self._clock = clock
        self._http = httpx.Client(transport=transport, timeout=30.0)

    def get_token(self) -> str:
        raise NotImplementedError

    def close(self) -> None:
        self._http.close()

    def _require_credentials(self) -> None:
        if not self._config.client_id or not self._config.client_secret:
            raise AuthError(
                "PINGEN_CLIENT_ID / PINGEN_CLIENT_SECRET are not configured "
                "(set them directly or point PINGEN_ENV_FILE at the credentials file)"
            )

    def _post_grant(self, fields: dict[str, str]) -> dict:
        self._require_credentials()
        data = {
            "client_id": self._config.client_id or "",
            "client_secret": self._config.client_secret or "",
            **fields,
        }
        url = self._config.identity_base_url + TOKEN_ENDPOINT_PATH
        response = self._http.post(url, data=data)
        if response.status_code >= 400:
            raise AuthError(
                f"token endpoint returned HTTP {response.status_code}: {response.text[:300]}"
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise AuthError("token endpoint returned a non-JSON response") from exc
        if "access_token" not in payload:
            raise AuthError("token endpoint response is missing access_token")
        return payload

    def _scope_fields(self) -> dict[str, str]:
        if self._config.scopes:
            return {"scope": " ".join(self._config.scopes)}
        return {}


class ClientCredentialsProvider(TokenProvider):
    """Server-to-server grant. Token is cached until expiry minus skew."""

    def __init__(self, config: Config, store: TokenStore, **kwargs):
        super().__init__(config, store, **kwargs)
        self._cached: TokenSet | None = store.load("client_credentials")

    def get_token(self) -> str:
        now = self._clock()
        if self._cached and now < self._cached.expires_at - SKEW_SECONDS:
            return self._cached.access_token
        payload = self._post_grant(
            {"grant_type": "client_credentials", **self._scope_fields()}
        )
        tokens = TokenSet(
            access_token=str(payload["access_token"]),
            expires_at=now + float(payload.get("expires_in", DEFAULT_EXPIRES_IN)),
            grant_type="client_credentials",
            refresh_token=payload.get("refresh_token"),
        )
        self._store.save(tokens)
        self._cached = tokens
        return tokens.access_token


class AuthorizationCodeProvider(TokenProvider):
    """Delegated grant: authorize URL, code exchange, refresh with rotation."""

    def __init__(self, config: Config, store: TokenStore, **kwargs):
        super().__init__(config, store, **kwargs)
        self._cached: TokenSet | None = store.load("authorization_code")

    def build_authorize_url(
        self,
        *,
        state: str | None = None,
        code_verifier: str | None = None,
        redirect_uri: str | None = None,
        scope: str | None = None,
    ) -> dict[str, str]:
        """Step 1 helper: generates state/code_verifier and the URL to open.

        Returns the generated ``state`` and ``code_verifier`` alongside the URL
        so the caller can verify state and complete the exchange later. The
        caller must persist ``code_verifier`` (valid for the exchange) itself.
        """
        state = state or generate_state()
        code_verifier = code_verifier or generate_code_verifier()
        url = build_authorize_url(
            self._config,
            state=state,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri,
            scope=scope,
        )
        return {"url": url, "state": state, "code_verifier": code_verifier}

    def exchange_code(
        self,
        *,
        code: str,
        code_verifier: str,
        state: str,
        expected_state: str | None = None,
        redirect_uri: str | None = None,
        scope: str | None = None,
    ) -> TokenSet:
        """Step 2: exchange the authorization code for access + refresh token."""
        if expected_state is not None and not secrets.compare_digest(
            state, expected_state
        ):
            raise AuthError(
                "state mismatch: returned state does not match the generated one; aborting"
            )
        redirect = redirect_uri or self._config.redirect_uri
        if not redirect:
            raise AuthError("redirect_uri is required for the code exchange")
        extra: dict[str, str] = {
            "grant_type": "authorization_code",
            "redirect_uri": redirect,
            "code": code,
            "code_verifier": code_verifier,
        }
        scope_value = scope or (" ".join(self._config.scopes) if self._config.scopes else None)
        if scope_value:
            extra["scope"] = scope_value
        payload = self._post_grant(extra)
        tokens = TokenSet(
            access_token=str(payload["access_token"]),
            expires_at=self._clock() + float(payload.get("expires_in", DEFAULT_EXPIRES_IN)),
            grant_type="authorization_code",
            refresh_token=payload.get("refresh_token"),
        )
        self._store.save(tokens)
        self._cached = tokens
        return tokens

    def get_token(self) -> str:
        now = self._clock()
        if self._cached is None:
            raise AuthError(
                "no authorization-code tokens stored; run the interactive flow first "
                "(build_authorize_url, user consent, exchange_code)"
            )
        if now < self._cached.expires_at - SKEW_SECONDS:
            return self._cached.access_token
        if not self._cached.refresh_token:
            raise AuthError(
                "authorization-code token expired and no refresh token stored; "
                "re-run the interactive flow"
            )
        return self._refresh(self._cached.refresh_token)

    def _refresh(self, refresh_token: str) -> str:
        payload = self._post_grant(
            {"grant_type": "refresh_token", "refresh_token": refresh_token}
        )
        now = self._clock()
        tokens = TokenSet(
            access_token=str(payload["access_token"]),
            expires_at=now + float(payload.get("expires_in", DEFAULT_EXPIRES_IN)),
            grant_type="authorization_code",
            # Pingen revokes the used refresh token; the rotated one MUST win.
            refresh_token=payload.get("refresh_token") or refresh_token,
        )
        self._store.save(tokens)
        self._cached = tokens
        return tokens.access_token


def provider_for(
    config: Config,
    store: TokenStore | None = None,
    **kwargs,
) -> TokenProvider:
    """Select the token provider from ``config.grant_type``."""
    store = store or TokenStore(config.token_file)
    if config.grant_type == "client_credentials":
        return ClientCredentialsProvider(config, store, **kwargs)
    if config.grant_type == "authorization_code":
        return AuthorizationCodeProvider(config, store, **kwargs)
    raise AuthError(f"unsupported grant type: {config.grant_type!r}")
