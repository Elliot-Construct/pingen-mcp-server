"""Shared test fixtures. No network: all HTTP goes through httpx.MockTransport."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from pingen_mcp_server.auth import TokenStore
from pingen_mcp_server.config import Config, load_config

REPO_ROOT = Path(__file__).resolve().parents[1]
OPENAPI_SPEC = REPO_ROOT / "reference" / "openapi.json"


def load_spec() -> dict[str, Any]:
    return json.loads(OPENAPI_SPEC.read_text(encoding="utf-8"))


class FakeTokenProvider:
    """Duck-typed token provider for PingenClient tests."""

    def __init__(self, token: str = "test-token"):
        self.token = token
        self.calls = 0

    def get_token(self) -> str:
        self.calls += 1
        return self.token


def json_api_response(data: Any, status: int = 200, **headers: str) -> httpx.Response:
    return httpx.Response(
        status,
        json=data,
        headers={"Content-Type": "application/vnd.api+json", **headers},
    )


@pytest.fixture
def token_file(tmp_path: Path) -> Path:
    return tmp_path / "tokens.json"


@pytest.fixture
def store(token_file: Path) -> TokenStore:
    return TokenStore(token_file)


@pytest.fixture
def make_config(tmp_path: Path):
    """Build a Config from a fully controlled env mapping (process env ignored).

    Defaults PINGEN_TOKEN_FILE into pytest's tmp dir so no test can ever write
    tokens to the real user config directory.
    """

    def make(**overrides: str) -> Config:
        env = {"PINGEN_TOKEN_FILE": str(tmp_path / "default-tokens.json"), **overrides}
        return load_config(env)

    return make


@pytest.fixture
def config(make_config, token_file: Path) -> Config:
    """Default test config: production hosts, client-credentials, tmp token file."""
    return make_config(
        PINGEN_TOKEN_FILE=str(token_file),
        PINGEN_CLIENT_ID="test-client-id",
        PINGEN_CLIENT_SECRET="test-client-secret",
    )
