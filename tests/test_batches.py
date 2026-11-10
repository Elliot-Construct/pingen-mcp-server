"""Batches domain tests: exact HTTP method + path per operation, pagination
mapping, and JSON:API payload passthrough. No network (MockTransport only)."""

from __future__ import annotations

import json

import httpx

from pingen_mcp_server.client import PingenClient
from pingen_mcp_server.config import load_config
from pingen_mcp_server.domains import batches

from conftest import FakeTokenProvider, json_api_response

ORG = "11111111-2222-3333-4444-555555555555"
BATCH = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


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


def test_batches_list_sends_get_with_pagination_and_query(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == f"/organisations/{ORG}/batches"
        query = dict(request.url.params)
        assert query["page[number]"] == "3"
        assert query["page[limit]"] == "50"
        assert query["sort"] == "-created_at"
        return json_api_response({"data": []})

    client, calls = make_client(tmp_path, handler)
    batches.batches_list(
        client,
        ORG,
        page_number=3,
        page_limit=50,
        query={"sort": "-created_at"},
    )
    assert len(calls) == 1
    assert calls[0].method == "GET"
    assert calls[0].url.path == f"/organisations/{ORG}/batches"


def test_batches_create_sends_post_with_payload_unchanged(tmp_path):
    payload = {
        "data": {
            "type": "batches",
            "attributes": {"letters_type": "document"},
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == f"/organisations/{ORG}/batches"
        assert json.loads(request.content) == payload
        return json_api_response({"data": {"id": BATCH, "type": "batches"}}, status=201)

    client, calls = make_client(tmp_path, handler)
    result = batches.batches_create(client, ORG, payload)
    assert result["data"]["id"] == BATCH
    assert json.loads(calls[0].content) == payload  # verbatim, not mutated


def test_batches_show_sends_get(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == f"/organisations/{ORG}/batches/{BATCH}"
        return json_api_response({"data": {"id": BATCH, "type": "batches"}})

    client, calls = make_client(tmp_path, handler)
    result = batches.batches_show(client, ORG, BATCH)
    assert result["data"]["id"] == BATCH
    assert calls[0].method == "GET"
    assert calls[0].url.path == f"/organisations/{ORG}/batches/{BATCH}"


def test_batches_edit_sends_patch_with_payload_unchanged(tmp_path):
    payload = {
        "data": {
            "type": "batches",
            "id": BATCH,
            "attributes": {"name": "renamed"},
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PATCH"
        assert request.url.path == f"/organisations/{ORG}/batches/{BATCH}"
        assert json.loads(request.content) == payload
        return json_api_response({"data": {"id": BATCH, "type": "batches"}}, status=202)

    client, calls = make_client(tmp_path, handler)
    batches.batches_edit(client, ORG, BATCH, payload)
    assert json.loads(calls[0].content) == payload


def test_batches_delete_sends_delete_with_required_body(tmp_path):
    # The spec marks a required JSON:API body on this DELETE (BatchDeleteDELETE).
    payload = {"data": {"type": "batches", "id": BATCH}}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        assert request.url.path == f"/organisations/{ORG}/batches/{BATCH}"
        assert request.headers["Content-Type"] == "application/vnd.api+json"
        assert json.loads(request.content) == payload
        return httpx.Response(204)

    client, calls = make_client(tmp_path, handler)
    result = batches.batches_delete(client, ORG, BATCH, payload)
    assert result == {}
    assert calls[0].method == "DELETE"
    assert calls[0].url.path == f"/organisations/{ORG}/batches/{BATCH}"


def test_batches_cancel_sends_patch_without_body(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PATCH"
        assert request.url.path == f"/organisations/{ORG}/batches/{BATCH}/cancel"
        assert request.content == b""
        assert "Content-Type" not in request.headers
        return json_api_response({"data": {"id": BATCH, "type": "batches"}}, status=202)

    client, calls = make_client(tmp_path, handler)
    batches.batches_cancel(client, ORG, BATCH)
    assert calls[0].method == "PATCH"
    assert calls[0].url.path == f"/organisations/{ORG}/batches/{BATCH}/cancel"
    assert calls[0].content == b""


def test_batches_send_sends_patch_with_payload_unchanged(tmp_path):
    payload = {
        "data": {
            "type": "batches",
            "id": BATCH,
            "meta": {"delivery": {"channel": "post"}},
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PATCH"
        assert request.url.path == f"/organisations/{ORG}/batches/{BATCH}/send"
        assert json.loads(request.content) == payload
        return json_api_response({"data": {"id": BATCH, "type": "batches"}})

    client, calls = make_client(tmp_path, handler)
    batches.batches_send(client, ORG, BATCH, payload)
    assert json.loads(calls[0].content) == payload


def test_batches_events_sends_get_with_pagination(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == f"/organisations/{ORG}/batches/{BATCH}/events"
        query = dict(request.url.params)
        assert query["page[number]"] == "2"
        assert query["page[limit]"] == "10"
        assert query["language"] == "de-CH"
        return json_api_response({"data": []})

    client, calls = make_client(tmp_path, handler)
    batches.batches_events(
        client,
        ORG,
        BATCH,
        page_number=2,
        page_limit=10,
        query={"language": "de-CH"},
    )
    assert len(calls) == 1
    assert calls[0].method == "GET"
    assert calls[0].url.path == f"/organisations/{ORG}/batches/{BATCH}/events"
    params = dict(calls[0].url.params)
    assert params["page[number]"] == "2"
    assert params["page[limit]"] == "10"


def test_statistics_details_sends_get(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == f"/organisations/{ORG}/batches/{BATCH}/statistics"
        assert list(request.url.params.items()) == []
        return json_api_response({"data": {"id": BATCH, "type": "batches"}})

    client, calls = make_client(tmp_path, handler)
    batches.organisations_batches_statistics_details(client, ORG, BATCH)
    assert calls[0].method == "GET"
    assert calls[0].url.path == f"/organisations/{ORG}/batches/{BATCH}/statistics"


def test_tools_maps_all_nine_operations():
    assert set(batches.TOOLS) == {
        "batches_list",
        "batches_create",
        "batches_show",
        "batches_edit",
        "batches_delete",
        "batches_cancel",
        "batches_send",
        "batches_events",
        "organisations_batches_statistics_details",
    }
    for name, fn in batches.TOOLS.items():
        assert callable(fn), name
