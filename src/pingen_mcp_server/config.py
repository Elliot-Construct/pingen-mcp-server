"""Environment-driven configuration for the Pingen MCP server.

Precedence: process environment beats values read from PINGEN_ENV_FILE.
No secret values are ever written by this module.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

ENVIRONMENTS: dict[str, tuple[str, str]] = {
    # (resource API base, identity base)
    "production": ("https://api.pingen.com", "https://identity.pingen.com"),
    "staging": ("https://api-staging.pingen.com", "https://identity-staging.pingen.com"),
}
GRANT_TYPES = ("client_credentials", "authorization_code")
DEFAULT_ENVIRONMENT = "production"
DEFAULT_GRANT_TYPE = "client_credentials"


class ConfigError(RuntimeError):
    """Invalid configuration. The message names the offending variable."""


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse a KEY=VALUE env file. '#' starts a comment; quotes are stripped."""
    if not path.is_file():
        raise ConfigError(f"PINGEN_ENV_FILE points at a missing file: {path}")
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def default_token_file() -> Path:
    """Token storage outside the repository (platform user config dir)."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Local"
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        root = Path(xdg) if xdg else Path.home() / ".config"
    return root / "pingen-mcp" / "tokens.json"


@dataclass(frozen=True)
class Config:
    environment: str
    grant_type: str
    api_base_url: str
    identity_base_url: str
    client_id: str | None = None
    client_secret: str | None = None
    redirect_uri: str | None = None
    scopes: tuple[str, ...] = ()
    token_file: Path = field(default_factory=default_token_file)
    env_file: Path | None = None


def load_config(env: Mapping[str, str] | None = None) -> Config:
    """Build a :class:`Config` from an environment mapping.

    When ``env`` is ``None`` the process environment is used. Values already
    present in ``env``/the process environment win over values read from the
    file named by ``PINGEN_ENV_FILE``.
    """
    process = dict(os.environ) if env is None else dict(env)
    merged = dict(process)
    env_file: Path | None = None
    if process.get("PINGEN_ENV_FILE"):
        env_file = Path(process["PINGEN_ENV_FILE"])
        merged = {**parse_env_file(env_file), **process}

    environment = merged.get("PINGEN_ENVIRONMENT") or DEFAULT_ENVIRONMENT
    if environment not in ENVIRONMENTS:
        allowed = ", ".join(sorted(ENVIRONMENTS))
        raise ConfigError(
            f"PINGEN_ENVIRONMENT={environment!r} is not supported (allowed: {allowed})"
        )
    api_default, identity_default = ENVIRONMENTS[environment]

    grant_type = merged.get("PINGEN_GRANT_TYPE") or DEFAULT_GRANT_TYPE
    if grant_type not in GRANT_TYPES:
        allowed = ", ".join(GRANT_TYPES)
        raise ConfigError(
            f"PINGEN_GRANT_TYPE={grant_type!r} is not supported (allowed: {allowed})"
        )

    token_file = (
        Path(merged["PINGEN_TOKEN_FILE"])
        if merged.get("PINGEN_TOKEN_FILE")
        else default_token_file()
    )
    return Config(
        environment=environment,
        grant_type=grant_type,
        api_base_url=(merged.get("PINGEN_API_BASE_URL") or api_default).rstrip("/"),
        identity_base_url=(merged.get("PINGEN_IDENTITY_BASE_URL") or identity_default).rstrip("/"),
        client_id=merged.get("PINGEN_CLIENT_ID") or None,
        client_secret=merged.get("PINGEN_CLIENT_SECRET") or None,
        redirect_uri=merged.get("PINGEN_REDIRECT_URI") or None,
        scopes=tuple((merged.get("PINGEN_SCOPES") or "").split()),
        token_file=token_file,
        env_file=env_file,
    )


# ---------------------------------------------------------------------------
# HTTP deployment mode (PINGEN-02): streamable HTTP + resource-server auth.
# ---------------------------------------------------------------------------

DEFAULT_HTTP_PORT = 8747
DEFAULT_HTTP_BIND = "127.0.0.1"
HTTP_AUTH_VARS = (
    "PINGEN_MCP_AUTH_ISSUER",
    "PINGEN_MCP_AUTH_JWKS_URI",
    "PINGEN_MCP_AUTH_AUDIENCE",
)


@dataclass(frozen=True)
class HttpConfig:
    """How to serve the MCP streamable-HTTP endpoint with caller auth.

    Every value names the estate identity layer that issues tokens for this
    resource; nothing product-specific is hardcoded, so the deployment is
    identical whichever identity provider the estate runs.
    """

    public_url: str  # canonical resource URL, e.g. https://pingen-mcp.datawyse.ai/mcp
    bind: str  # interface to listen on (container: 0.0.0.0; local: 127.0.0.1)
    port: int
    issuer: str  # expected JWT `iss`
    jwks_uri: str  # where to fetch signing keys
    audience: str  # expected JWT `aud` (RFC 8707 resource or client id)

    @property
    def hostname(self) -> str:
        """Host header value the reverse proxy will forward."""
        return urlparse(self.public_url).hostname or ""


def load_http_config(env: Mapping[str, str] | None = None) -> HttpConfig | None:
    """Return HTTP-mode configuration, or ``None`` when running stdio-only.

    HTTP mode is all-or-nothing (fail closed): a partial set of variables is a
    :class:`ConfigError`, never a silent downgrade to an unauthenticated or
    stdio server.
    """
    process = dict(os.environ) if env is None else dict(env)
    public_url = (process.get("PINGEN_MCP_PUBLIC_URL") or "").strip()

    if not public_url:
        stray = [key for key in HTTP_AUTH_VARS if (process.get(key) or "").strip()]
        if stray:
            raise ConfigError(
                f"{', '.join(stray)} set but PINGEN_MCP_PUBLIC_URL is not: "
                "HTTP mode must be fully configured or fully off"
            )
        return None

    missing = [key for key in HTTP_AUTH_VARS if not (process.get(key) or "").strip()]
    if missing:
        raise ConfigError(
            f"HTTP mode requires {', '.join(missing)}: they must name the identity "
            f"layer that issues tokens for {public_url}"
        )

    parsed = urlparse(public_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ConfigError(
            f"PINGEN_MCP_PUBLIC_URL must be an absolute http(s) URL, got {public_url!r}"
        )

    port_raw = (process.get("PINGEN_MCP_PORT") or str(DEFAULT_HTTP_PORT)).strip()
    try:
        port = int(port_raw)
    except ValueError as exc:
        raise ConfigError(f"PINGEN_MCP_PORT must be an integer, got {port_raw!r}") from exc
    if not 0 < port < 65536:
        raise ConfigError(f"PINGEN_MCP_PORT out of range: {port}")

    return HttpConfig(
        public_url=public_url.rstrip("/"),
        bind=(process.get("PINGEN_MCP_BIND") or DEFAULT_HTTP_BIND).strip(),
        port=port,
        issuer=(process.get("PINGEN_MCP_AUTH_ISSUER") or "").strip(),
        jwks_uri=(process.get("PINGEN_MCP_AUTH_JWKS_URI") or "").strip(),
        audience=(process.get("PINGEN_MCP_AUTH_AUDIENCE") or "").strip(),
    )
