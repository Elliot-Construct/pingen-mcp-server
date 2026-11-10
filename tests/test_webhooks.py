"""Webhooks domain tests: exact HTTP method + path per operation, pagination
mapping, JSON:API payload passthrough, and no tools for incoming-payload
paths. All HTTP via httpx.MockTransport — no network."""

from __future__ import annotations

import inspect
import json

import httpx

from pingen_mcp_server.client import PingenClient
from pingen_mcp_server.config import load_config
from pingen_mcp_server.domains import webhooks
from pingen_mcp_server.domains.webhooks import TOOLS

from conftest import FakeTokenProvider, json_api_response

EXPECTED_TOOLS = {
    "webhooks_index",
    "webhooks_create",
    "webhooks_show",
    "webhooks_destroy",
}

# Method + path each tool's docstring must advertise (per module contract).
DOCSTRING_ENDPOINTS = {
    "webhooks_index": "GET /organisations/{organisationId}/webhooks",
    "webhooks_create": "POST /organisations/{organisationId}/webhooks",
    "webhooks_show": "GET /organisations/{organisationId}/webhooks/{webhookId}",
    "webhooks_destroy": "DELETE /organisations/{organisationId}/webhooks/{webhookId}",
}


def make_client(tmp_path, handler):
    config = load_config({"PINGEN_TOKEN_FILE": str(tmp_path / "tokens.json")})
    calls: list[httpx.Request] = []

    def wrapped(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return handler(request)

    client = PingenClient(
        config,
        FakeTokenProvider("test-token"),
        transport=httpx.MockTransport(wrapped),
    )
    return client, calls


def test_index_sends_get_with_pagination_and_query(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/organisations/org-1/webhooks"
        query = dict(request.url.params)
        assert query == {
            "page[number]": "3",
            "page[limit]": "50",
            "q": "test",
        }
        return json_api_response({"data": [{"id": "w1", "type": "webhooks"}]})

    client, calls = make_client(tmp_path, handler)
    result = webhooks.webhooks_index(
        client,
        "org-1",
        page_number=3,
        page_limit=50,
        query={"q": "test"},
    )
    assert result["data"][0]["id"] == "w1"
    assert len(calls) == 1


def test_index_without_pagination_sends_no_query(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/organisations/org-1/webhooks"
        assert list(request.url.params.items()) == []
        return json_api_response({"data": []})

    client, calls = make_client(tmp_path, handler)
    assert webhooks.webhooks_index(client, "org-1") == {"data": []}
    assert len(calls) == 1


def test_create_posts_payload_unchanged(tmp_path):
    payload = {
        "data": {
            "type": "webhooks",
            "attributes": {
                "url": "https://example.com/hook",
                "events": ["letter.delivered"],
            },
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/organisations/org-1/webhooks"
        assert request.headers["Content-Type"] == "application/vnd.api+json"
        assert json.loads(request.content) == payload  # verbatim passthrough
        return json_api_response({"data": {"id": "w1", "type": "webhooks"}}, status=201)

    client, calls = make_client(tmp_path, handler)
    result = webhooks.webhooks_create(client, "org-1", payload)
    assert result["data"]["id"] == "w1"
    assert len(calls) == 1


def test_show_gets_single_webhook(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/organisations/org-1/webhooks/w1"
        assert list(request.url.params.items()) == []
        return json_api_response({"data": {"id": "w1", "type": "webhooks"}})

    client, calls = make_client(tmp_path, handler)
    result = webhooks.webhooks_show(client, "org-1", "w1")
    assert result["data"]["id"] == "w1"
    assert len(calls) == 1


def test_destroy_deletes_webhook(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        assert request.url.path == "/organisations/org-1/webhooks/w1"
        return httpx.Response(204)

    client, calls = make_client(tmp_path, handler)
    assert webhooks.webhooks_destroy(client, "org-1", "w1") == {}
    assert len(calls) == 1


def test_tools_are_exactly_the_four_documented_operations():
    # No tool/function may exist for any incoming /your-webhook-url-for-* path:
    # TOOLS must be exactly the 4 documented operations.
    assert set(TOOLS) == EXPECTED_TOOLS
    for name, fn in TOOLS.items():
        assert callable(fn), name
        assert inspect.isfunction(fn), name


def test_incoming_payload_example_paths_are_not_present_anywhere():
    source = inspect.getsource(webhooks)
    assert "your-webhook-url" not in source
    for name, fn in TOOLS.items():
        assert "your-webhook-url" not in (fn.__doc__ or ""), name


def test_docstrings_include_http_method_and_path():
    for name, endpoint in DOCSTRING_ENDPOINTS.items():
        assert endpoint in (TOOLS[name].__doc__ or ""), name
