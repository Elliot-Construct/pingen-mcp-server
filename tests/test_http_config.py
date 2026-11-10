"""HTTP deployment-mode configuration (PINGEN-02).

Fail closed: HTTP mode is fully configured or fully off, never partial.
"""

from __future__ import annotations

import pytest

from pingen_mcp_server.config import ConfigError, load_http_config

AUTH_VARS = {
    "PINGEN_MCP_AUTH_ISSUER": "https://idp.example/realms/estate/",
    "PINGEN_MCP_AUTH_JWKS_URI": "https://idp.example/realms/estate/protocol/openid-connect/certs",
    "PINGEN_MCP_AUTH_AUDIENCE": "https://pingen-mcp.datawyse.ai/mcp",
}
PUBLIC = {"PINGEN_MCP_PUBLIC_URL": "https://pingen-mcp.datawyse.ai/mcp"}


def test_stdio_mode_when_unconfigured():
    assert load_http_config({}) is None


def test_stray_auth_vars_without_public_url_fail():
    with pytest.raises(ConfigError, match="PINGEN_MCP_PUBLIC_URL"):
        load_http_config(dict(AUTH_VARS))


def test_partial_http_config_fails_closed():
    with pytest.raises(ConfigError) as exc:
        load_http_config({"PINGEN_MCP_PUBLIC_URL": "https://pingen-mcp.datawyse.ai/mcp"})
    for var in AUTH_VARS:
        assert var in str(exc.value)


def test_full_config_parsed():
    cfg = load_http_config(
        {
            **PUBLIC,
            "PINGEN_MCP_PORT": "9001",
            "PINGEN_MCP_BIND": "0.0.0.0",
            **AUTH_VARS,
        }
    )
    assert cfg is not None
    assert cfg.public_url == "https://pingen-mcp.datawyse.ai/mcp"
    assert cfg.hostname == "pingen-mcp.datawyse.ai"
    assert cfg.port == 9001
    assert cfg.bind == "0.0.0.0"
    assert cfg.issuer == AUTH_VARS["PINGEN_MCP_AUTH_ISSUER"]
    assert cfg.jwks_uri == AUTH_VARS["PINGEN_MCP_AUTH_JWKS_URI"]
    assert cfg.audience == AUTH_VARS["PINGEN_MCP_AUTH_AUDIENCE"]


def test_trailing_slash_stripped_from_public_url():
    cfg = load_http_config({**PUBLIC, "PINGEN_MCP_PUBLIC_URL": PUBLIC["PINGEN_MCP_PUBLIC_URL"] + "/", **AUTH_VARS})
    assert cfg is not None
    assert cfg.public_url == "https://pingen-mcp.datawyse.ai/mcp"


def test_non_integer_port_fails():
    with pytest.raises(ConfigError, match="PINGEN_MCP_PORT"):
        load_http_config({**PUBLIC, "PINGEN_MCP_PORT": "abc", **AUTH_VARS})


def test_out_of_range_port_fails():
    with pytest.raises(ConfigError, match="out of range"):
        load_http_config({**PUBLIC, "PINGEN_MCP_PORT": "70000", **AUTH_VARS})


def test_relative_public_url_fails():
    with pytest.raises(ConfigError, match="absolute"):
        load_http_config(
            {"PINGEN_MCP_PUBLIC_URL": "pingen-mcp.datawyse.ai/mcp", **AUTH_VARS}
        )
