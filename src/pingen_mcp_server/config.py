"""Environment-driven configuration for the Pingen MCP server.

Precedence: process environment beats values read from PINGEN_ENV_FILE.
No secret values are ever written by this module.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

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
