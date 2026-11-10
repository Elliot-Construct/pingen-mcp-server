"""Letters domain tests: exact HTTP method + path for all 14 operations,
pagination mapping, payload pass-through and 302 envelopes. No network."""

from __future__ import annotations

import json

import httpx
import pytest
from pingen_mcp_server.client import PingenClient
from pingen_mcp_server.config import load_config
from pingen_mcp_server.domains import letters
from pingen_mcp_server.domains.letters import (
    TOOLS,
    letters_cancel,
    letters_create,
    letters_delete,
    letters_events,
    letters_events_image,
    letters_file,
    letters_list,
    letters_price_calculator,
    letters_send,
    letters_show,
    organisations_letters_events_delivered,
    organisations_letters_events_issues,
    organisations_letters_events_sent,
    organisations_letters_events_undeliverable,
)

from conftest import FakeTokenProvider, json_api_response

ORG = "11111111-1111-4111-8111-111111111111"
LETTER = "22222222-2222-4222-8222-222222222222"
EVENT = "33333333-3333-4333-8333-333333333333"

EXPECTED_TOOLS = {
    "letters_list",
    "letters_create",
    "letters_show",
    "letters_delete",
    "letters_send",
    "letters_cancel",
    "letters_file",
    "letters_price_calculator",
    "letters_events",
    "letters_events_image",
    "organisations_letters_events_delivered",
    "organisations_letters_events_issues",
    "organisations_letters_events_sent",
    "organisations_letters_events_undeliverable",
}


def make_client(tmp_path, handler):
    """Client on a MockTransport that records every request. No network."""
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


# --- letters_list -----------------------------------------------------------

def test_letters_list_maps_pagination_and_path(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == f"/organisations/{ORG}/deliveries/letters"
        assert dict(request.url.params) == {
            "page[number]": "2",
            "page[limit]": "50",
            "filter[status]": "created",
            "sort": "-created_at",
        }
        return json_api_response({"data": []})

    client, calls = make_client(tmp_path, handler)
    result = letters_list(
        client,
        ORG,
        page_number=2,
        page_limit=50,
        query={"filter[status]": "created", "sort": "-created_at"},
    )
    assert result == {"data": []}
    assert len(calls) == 1


def test_letters_list_without_pagination_sends_no_query(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == f"/organisations/{ORG}/deliveries/letters"
        assert list(request.url.params.items()) == []
        return json_api_response({"data": []})

    client, _ = make_client(tmp_path, handler)
    letters_list(client, ORG)


# --- letters_create ---------------------------------------------------------

def test_letters_create_posts_payload_unchanged(tmp_path):
    payload = {
        "data": {
            "type": "letters",
            "attributes": {"auto_send": False, "address": {"name": "A. Person"}},
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == f"/organisations/{ORG}/deliveries/letters"
        assert request.headers["Content-Type"] == "application/vnd.api+json"
        assert json.loads(request.content) == payload
        return json_api_response({"data": {"id": "l1", "type": "letters"}}, status=201)

    client, calls = make_client(tmp_path, handler)
    result = letters_create(client, ORG, payload)
    assert result["data"]["id"] == "l1"
    assert len(calls) == 1


# --- letters_show -----------------------------------------------------------

def test_letters_show_gets_exact_path(tmp_path):
    body = {"data": {"id": LETTER, "type": "letters"}}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == (
            f"/organisations/{ORG}/deliveries/letters/{LETTER}"
        )
        return json_api_response(body)

    client, calls = make_client(tmp_path, handler)
    assert letters_show(client, ORG, LETTER) == body
    assert len(calls) == 1


# --- letters_delete ---------------------------------------------------------

def test_letters_delete_deletes_exact_path(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        assert request.url.path == (
            f"/organisations/{ORG}/deliveries/letters/{LETTER}"
        )
        return httpx.Response(204)

    client, calls = make_client(tmp_path, handler)
    assert letters_delete(client, ORG, LETTER) == {}
    assert len(calls) == 1


# --- letters_send -----------------------------------------------------------

def test_letters_send_patches_payload_unchanged(tmp_path):
    payload = {"data": {"type": "letters", "attributes": {"address": None}}}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PATCH"
        assert request.url.path == (
            f"/organisations/{ORG}/deliveries/letters/{LETTER}/send"
        )
        assert json.loads(request.content) == payload
        return json_api_response({"data": {"id": LETTER, "type": "letters"}})

    client, calls = make_client(tmp_path, handler)
    letters_send(client, ORG, LETTER, payload)
    assert len(calls) == 1


# --- letters_cancel ---------------------------------------------------------

def test_letters_cancel_patches_without_body(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PATCH"
        assert request.url.path == (
            f"/organisations/{ORG}/deliveries/letters/{LETTER}/cancel"
        )
        assert request.content == b""
        return httpx.Response(202)

    client, calls = make_client(tmp_path, handler)
    letters_cancel(client, ORG, LETTER)
    assert len(calls) == 1


# --- letters_file -----------------------------------------------------------

def test_letters_file_returns_302_envelope_unfollowed(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == f"/organisations/{ORG}/deliveries/letters/{LETTER}/file"
        return httpx.Response(
            302, headers={"Location": "https://files.example/letter.pdf"}
        )

    client, calls = make_client(tmp_path, handler)
    result = letters_file(client, ORG, LETTER)
    assert result == {
        "redirect_url": "https://files.example/letter.pdf",
        "status_code": 302,
    }
    assert len(calls) == 1


# --- letters_price_calculator ----------------------------------------------

def test_letters_price_calculator_posts_payload_unchanged(tmp_path):
    payload = {
        "data": {
            "type": "letters_price_calculator",
            "attributes": {"page_count": 2, "delivery": "standard"},
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == (
            f"/organisations/{ORG}/deliveries/letters/price-calculator"
        )
        assert json.loads(request.content) == payload
        return json_api_response({"data": {"type": "price", "attributes": {"amount": 125}}})

    client, calls = make_client(tmp_path, handler)
    result = letters_price_calculator(client, ORG, payload)
    assert result["data"]["attributes"]["amount"] == 125
    assert len(calls) == 1


# --- letters_events ---------------------------------------------------------

def test_letters_events_maps_pagination_and_path(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == (
            f"/organisations/{ORG}/deliveries/letters/{LETTER}/events"
        )
        assert dict(request.url.params) == {
            "page[number]": "3",
            "page[limit]": "10",
            "language": "de-DE",
        }
        return json_api_response({"data": []})

    client, calls = make_client(tmp_path, handler)
    letters_events(
        client, ORG, LETTER, page_number=3, page_limit=10, query={"language": "de-DE"}
    )
    assert len(calls) == 1


# --- letters_events_image ---------------------------------------------------

def test_letters_events_image_returns_302_envelope_unfollowed(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == (
            f"/organisations/{ORG}/deliveries/letters/{LETTER}/events/{EVENT}/image"
        )
        return httpx.Response(
            302, headers={"Location": "https://files.example/event.png"}
        )

    client, calls = make_client(tmp_path, handler)
    result = letters_events_image(client, ORG, LETTER, EVENT)
    assert result == {
        "redirect_url": "https://files.example/event.png",
        "status_code": 302,
    }
    assert len(calls) == 1


# --- organisation-wide event collections -----------------------------------

ORG_EVENT_TOOLS = [
    (organisations_letters_events_delivered, "delivered"),
    (organisations_letters_events_issues, "issues"),
    (organisations_letters_events_sent, "sent"),
    (organisations_letters_events_undeliverable, "undeliverable"),
]


@pytest.mark.parametrize("tool,suffix", ORG_EVENT_TOOLS, ids=lambda v: getattr(v, "__name__", v))
def test_org_event_collection_maps_pagination_and_path(tmp_path, tool, suffix):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == (
            f"/organisations/{ORG}/deliveries/letters/events/{suffix}"
        )
        assert dict(request.url.params) == {
            "page[number]": "4",
            "page[limit]": "25",
        }
        return json_api_response({"data": []})

    client, calls = make_client(tmp_path, handler)
    result = tool(client, ORG, page_number=4, page_limit=25)
    assert result == {"data": []}
    assert len(calls) == 1


# --- module contract --------------------------------------------------------

def test_tools_inventory_exact_14_names():
    assert set(TOOLS) == EXPECTED_TOOLS
    assert len(TOOLS) == 14
    assert all(callable(fn) for fn in TOOLS.values())


def test_tools_values_are_the_module_functions():
    for name, fn in TOOLS.items():
        assert getattr(letters, name) is fn


@pytest.mark.parametrize("name", sorted(EXPECTED_TOOLS))
def test_every_tool_docstring_has_method_and_path(name):
    doc = TOOLS[name].__doc__ or ""
    assert any(m in doc for m in ("GET ", "POST ", "PATCH ", "DELETE ")), name
    assert "/organisations/{organisationId}/deliveries/letters" in doc, name
