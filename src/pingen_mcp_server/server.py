"""FastMCP application: register every domain tool and run over stdio.

Importing this module is side-effect-light: no configuration is loaded and no
network call happens until a tool is actually invoked (the client is created
lazily on first use via :func:`get_client`).
"""

from __future__ import annotations

import functools
import inspect

from urllib.parse import urlparse

from fastmcp import FastMCP
from fastmcp.server.auth import JWTVerifier, RemoteAuthProvider

from .auth import provider_for
from .client import PingenClient
from .config import HttpConfig, load_config, load_http_config
from .domains import DOMAIN_MODULES, batches, channels, directory, files, letters, webhooks

_CLIENT: PingenClient | None = None


def create_client() -> PingenClient:
    """Build the shared client from the current environment."""
    config = load_config()
    return PingenClient(config, provider_for(config))


def get_client() -> PingenClient:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = create_client()
    return _CLIENT


def reset_client() -> None:
    """Drop the cached client (used by tests and after config changes)."""
    global _CLIENT
    if _CLIENT is not None:
        _CLIENT.close()
    _CLIENT = None


def _wrap_tool(fn, get_client_fn):
    """Adapt ``fn(client, ...)`` into a zero-positional-client MCP tool."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return fn(get_client_fn(), *args, **kwargs)

    signature = inspect.signature(fn)
    wrapper.__signature__ = signature.replace(
        parameters=[p for p in signature.parameters.values() if p.name != "client"]
    )
    return wrapper


def register_domain(mcp: FastMCP, tools: dict, get_client_fn=get_client) -> None:
    for name, fn in tools.items():
        mcp.tool(name=name)(_wrap_tool(fn, get_client_fn))


def build_server(get_client_fn=get_client, auth: RemoteAuthProvider | None = None) -> FastMCP:
    # Validate configuration eagerly so a bad PINGEN_* value fails at server
    # startup (import/entry point), not on the first tool call. Credentials
    # presence is NOT required here - listing tools must work without them.
    load_config()
    mcp = FastMCP(
        "Pingen",
        instructions=(
            "Tools for the Pingen API (programmable physical mail, email and "
            "eBill dispatch). Every tool mirrors one documented operation of "
            "the official Pingen OpenAPI spec; responses are JSON:API documents "
            "passed through unchanged."
        ),
        auth=auth,
    )
    modules = {
        "batches": batches,
        "channels": channels,
        "directory": directory,
        "files": files,
        "letters": letters,
        "webhooks": webhooks,
    }
    for key in DOMAIN_MODULES:
        register_domain(mcp, modules[key].TOOLS, get_client_fn)
    return mcp


def http_allowed_hosts(cfg: HttpConfig) -> list[str]:
    """Host headers the deployed endpoint accepts (design D6).

    The public hostname plus loopback for local probes; anything else is
    refused with 421 before authentication is evaluated.
    """
    return [cfg.hostname, "127.0.0.1", "localhost"]


def build_auth_provider(cfg: HttpConfig) -> RemoteAuthProvider:
    """Resource-server auth: validate Bearer JWTs against the identity layer.

    Serves RFC 9728 protected-resource metadata and the fail-closed 401
    challenge (WWW-Authenticate -> resource_metadata) the MCP specification
    requires; FastMCP's RequireAuthMiddleware rejects any request without a
    valid token before a tool can be reached.
    """
    verifier = JWTVerifier(
        jwks_uri=cfg.jwks_uri,
        issuer=cfg.issuer,
        audience=cfg.audience,
    )
    # base_url must be the ORIGIN: RemoteAuthProvider appends the MCP path
    # itself, and cfg.public_url already carries /mcp (the canonical resource).
    parsed = urlparse(cfg.public_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    return RemoteAuthProvider(
        token_verifier=verifier,
        authorization_servers=[cfg.issuer],
        base_url=origin,
        resource_name="Pingen MCP",
    )


def build_http_server(cfg: HttpConfig, get_client_fn=get_client) -> FastMCP:
    """The server as deployed publicly: same tools, auth-gated transport."""
    return build_server(get_client_fn=get_client_fn, auth=build_auth_provider(cfg))


def serve_http(cfg: HttpConfig) -> None:
    """Run the streamable-HTTP endpoint on a non-published bind.

    Reachability is deliberately narrow: the bind is loopback (or the
    container interface with no published port), and the Host allowlist
    refuses any Host other than the configured public hostname, so a spoofed
    Host is rejected with 421 before authentication is even evaluated.
    """
    server = build_http_server(cfg)
    server.run(
        transport="http",
        host=cfg.bind,
        port=cfg.port,
        allowed_hosts=http_allowed_hosts(cfg),
        # "auto" only guards loopback binds; the deployed bind may be the
        # container interface, so validate every request against the allowlist.
        host_origin_protection=True,
        show_banner=False,
    )


mcp = build_server()


def main() -> None:
    """Console entry point: stdio by default, streamable HTTP when configured."""
    http_cfg = load_http_config()
    if http_cfg is None:
        mcp.run()
    else:
        serve_http(http_cfg)


if __name__ == "__main__":
    main()
