"""FastMCP application: register every domain tool and run over stdio.

Importing this module is side-effect-light: no configuration is loaded and no
network call happens until a tool is actually invoked (the client is created
lazily on first use via :func:`get_client`).
"""

from __future__ import annotations

import functools
import inspect

from fastmcp import FastMCP

from .auth import provider_for
from .client import PingenClient
from .config import load_config
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


def build_server(get_client_fn=get_client) -> FastMCP:
    mcp = FastMCP(
        "Pingen",
        instructions=(
            "Tools for the Pingen API (programmable physical mail, email and "
            "eBill dispatch). Every tool mirrors one documented operation of "
            "the official Pingen OpenAPI spec; responses are JSON:API documents "
            "passed through unchanged."
        ),
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


mcp = build_server()


def main() -> None:
    """Console entry point: run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
