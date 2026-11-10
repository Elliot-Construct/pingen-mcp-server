"""Path fidelity audit: every domain tool must issue EXACTLY the HTTP method
and path template documented in reference/openapi.json.

Method: call each registered domain function with sentinel values for every
required argument (path params get a single sentinel segment, ``payload`` gets
a JSON:API stub) through an httpx.MockTransport, then compare the captured
request against the spec's path template with all ``{...}`` placeholders
replaced by the same sentinel. Path-parameter NAMES are invisible on the wire,
so this compares structure only - it fails on any extra/missing/reordered
segment regardless of how the module named its arguments.
"""

from __future__ import annotations

import importlib
import inspect
import re

import httpx
import pytest

from conftest import FakeTokenProvider, load_spec
from pingen_mcp_server.client import PingenClient
from pingen_mcp_server.config import load_config
from pingen_mcp_server.domains import DOMAIN_MODULES

SENTINEL = "SENTINEL"
METHODS = ("get", "post", "put", "patch", "delete")


def spec_operations() -> dict[str, tuple[str, str]]:
    """tool_name -> (method, path template) for every client-callable op."""
    spec = load_spec()
    ops: dict[str, tuple[str, str]] = {}
    for path, item in spec["paths"].items():
        for method in METHODS:
            if method not in item:
                continue
            op = item[method]
            if "misc.webhooks" in op.get("tags", []):
                continue  # incoming payload examples, never tools
            tool = op["operationId"].replace(".", "_").replace("-", "_")
            ops[tool] = (method.upper(), path)
    return ops


def domain_tools() -> dict:
    tools: dict = {}
    for name in DOMAIN_MODULES:
        module = importlib.import_module(f"pingen_mcp_server.domains.{name}")
        tools.update(module.TOOLS)
    return tools


def expected_path(path_template: str) -> str:
    return re.sub(r"\{[^}]+\}", SENTINEL, path_template)


def required_kwargs(fn) -> dict:
    kwargs = {}
    for pname, param in inspect.signature(fn).parameters.items():
        if pname == "client":
            continue
        if param.default is not inspect.Parameter.empty:
            continue  # optional args don't affect the path
        kwargs[pname] = {"data": {"type": "sentinel"}} if pname == "payload" else SENTINEL
    return kwargs


def test_every_tool_matches_spec_method_and_path(tmp_path):
    specs = spec_operations()
    tools = domain_tools()
    failures: list[str] = []

    for tool_name in sorted(tools):
        if tool_name not in specs:
            failures.append(f"{tool_name}: tool not derived from the spec at all")
            continue
        method, path_template = specs[tool_name]
        want_path = expected_path(path_template)

        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["method"] = request.method
            captured["path"] = request.url.path
            return httpx.Response(200, json={"data": {}})

        config = load_config({"PINGEN_TOKEN_FILE": str(tmp_path / "tokens.json")})
        client = PingenClient(
            config,
            FakeTokenProvider("sentinel-token"),
            transport=httpx.MockTransport(handler),
        )
        try:
            tools[tool_name](client, **required_kwargs(tools[tool_name]))
        except TypeError as exc:
            failures.append(f"{tool_name}: signature error calling with required args: {exc}")
            continue
        if captured.get("method") != method or captured.get("path") != want_path:
            failures.append(
                f"{tool_name}: expected {method} {want_path}, "
                f"got {captured.get('method')} {captured.get('path')}"
            )

    assert not failures, "path/method drift vs vendored spec:\n" + "\n".join(failures)


def test_spec_and_modules_cover_the_same_tool_set():
    specs = spec_operations()
    tools = domain_tools()
    missing = sorted(set(specs) - set(tools))
    extra = sorted(set(tools) - set(specs))
    assert not missing, f"in spec, no module: {missing}"
    assert not extra, f"in modules, not in spec: {extra}"
    assert len(specs) == 49
