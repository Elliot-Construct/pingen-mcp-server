"""Inventory test (criterion c3): registered MCP tools == spec-derived set.

The expected set is re-derived from reference/openapi.json at run time:
tool name = operationId with ``.``/``-`` replaced by ``_``, excluding the
``misc.webhooks`` incoming-payload examples (documented, never tools).
Any drift - missing tool, extra tool, spec re-vendoring - fails here.
"""

from __future__ import annotations

import asyncio

from conftest import load_spec
from pingen_mcp_server.server import mcp

EXPECTED_COUNT = 49  # client-callable operations in the vendored spec


def expected_tools() -> set[str]:
    spec = load_spec()
    expected: set[str] = set()
    for path, item in spec["paths"].items():
        for method in ("get", "post", "put", "patch", "delete"):
            if method not in item:
                continue
            op = item[method]
            if "misc.webhooks" in op.get("tags", []):
                continue  # incoming payload examples -> README, not tools
            operation_id = op.get("operationId")
            assert operation_id, f"operation without operationId: {method.upper()} {path}"
            expected.add(operation_id.replace(".", "_").replace("-", "_"))
    return expected


def registered_tools() -> set[str]:
    return {tool.name for tool in asyncio.run(mcp.list_tools())}


def test_registered_tools_match_vendored_spec():
    expected = expected_tools()
    registered = registered_tools()
    missing = sorted(expected - registered)
    extra = sorted(registered - expected)
    assert len(expected) == EXPECTED_COUNT, (
        f"spec drift: derived {len(expected)} operations, expected {EXPECTED_COUNT}"
    )
    assert not missing, f"missing tools (in spec, not registered): {missing}"
    assert not extra, f"unexpected tools (registered, not in spec): {extra}"


def test_incoming_webhook_payloads_are_not_tools():
    registered = registered_tools()
    assert not any(name.startswith("your_webhook_url") for name in registered)
    assert "webhook_delivered" not in registered
