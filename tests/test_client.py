"""Client tests: bearer injection, pagination mapping, JSON:API passthrough,
error mapping with X-Request-Id, and 302 redirect envelopes. No network."""

from __future__ import annotations

import json
import urllib.parse

import httpx
import pytest

from pingen_mcp_server.client import PingenApiError, PingenClient, summarize_errors
from pingen_mcp_server.config import load_config

from conftest import FakeTokenProvider, json_api_response


def make_client(tmp_path, handler, **env_extra):
    config = load_config(
        {"PINGEN_TOKEN_FILE": str(tmp_path / "tokens.json"), **env_extra}
    )
    calls: list[httpx.Request] = []

    def wrapped(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return handler(request)

    provider = FakeTokenProvider("test-token")
    client = PingenClient(
        config, provider, transport=httpx.MockTransport(wrapped)
    )
    return client, provider, calls


def test_request_injects_bearer_accept_and_full_url(tmp_path):
    payload = {"data": {"id": "u1", "type": "users"}}

    def handler(request: httpx.Request) -> httpx.Response:
        assert (request.url.scheme, request.url.host) == ("https", "api.pingen.com")
        assert request.url.path == "/user"
        assert request.headers["Authorization"] == "Bearer test-token"
        assert request.headers["Accept"] == "application/vnd.api+json"
        return json_api_response(payload)

    client, provider, _ = make_client(tmp_path, handler)
    result = client.get("/user")
    assert result == payload  # JSON:API passthrough, unchanged
    assert provider.calls == 1


def test_pagination_and_query_mapping(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        query = dict(request.url.params)
        assert query == {
            "page[number]": "2",
            "page[limit]": "50",
            "filter[status]": "created",
        }
        return json_api_response({"data": []})

    client, _, _ = make_client(tmp_path, handler)
    client.collection(
        "/organisations",
        page_number=2,
        page_limit=50,
        query={"filter[status]": "created"},
    )


def test_collection_without_args_sends_no_query(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert list(request.url.params.items()) == []
        return json_api_response({"data": []})

    client, _, _ = make_client(tmp_path, handler)
    client.collection("/organisations")


def test_post_sends_json_body_with_jsonapi_content_type(tmp_path):
    body = {"data": {"type": "letters", "attributes": {"auto_send": False}}}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.headers["Content-Type"] == "application/vnd.api+json"
        assert json.loads(request.content) == body
        return json_api_response({"data": {"id": "l1", "type": "letters"}}, status=201)

    client, _, _ = make_client(tmp_path, handler)
    result = client.post("/organisations/o1/deliveries/letters", json_body=body)
    assert result["data"]["id"] == "l1"


def test_jsonapi_error_raises_with_status_detail_and_request_id(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return json_api_response(
            {
                "errors": [
                    {
                        "status": "404",
                        "title": "Not Found",
                        "detail": "Letter does not exist",
                    }
                ]
            },
            status=404,
            **{"X-Request-Id": "req-123"},
        )

    client, _, _ = make_client(tmp_path, handler)
    with pytest.raises(PingenApiError) as exc:
        client.get("/organisations/o1/deliveries/letters/l9")
    err = exc.value
    assert err.status_code == 404
    assert err.request_id == "req-123"
    assert "404 Not Found" in str(err)
    assert "Letter does not exist" in str(err)
    assert "req-123" in str(err)


def test_non_json_error_body_is_summarised(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    client, _, _ = make_client(tmp_path, handler)
    with pytest.raises(PingenApiError) as exc:
        client.get("/user")
    assert exc.value.status_code == 500
    assert "Internal Server Error" in str(exc.value)


def test_unauthorized_raises_without_retry(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"errors": [{"status": "401", "title": "Unauthorized"}]})

    client, provider, calls = make_client(tmp_path, handler)
    with pytest.raises(PingenApiError) as exc:
        client.get("/user")
    assert exc.value.status_code == 401
    assert len(calls) == 1
    assert provider.calls == 1


def test_redirect_returns_envelope_and_is_not_followed(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            302, headers={"Location": "https://files.example/letter.pdf"}
        )

    client, _, calls = make_client(tmp_path, handler)
    result = client.get("/organisations/o1/deliveries/letters/l1/file")
    assert result == {
        "redirect_url": "https://files.example/letter.pdf",
        "status_code": 302,
    }
    assert len(calls) == 1  # MockTransport would fail on a follow-up anyway


def test_204_returns_empty_dict(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204)

    client, _, _ = make_client(tmp_path, handler)
    assert client.delete("/organisations/o1/deliveries/letters/l1") == {}


def test_summarize_errors_joins_multiple_entries():
    detail = summarize_errors(
        {
            "errors": [
                {"status": "422", "title": "Invalid", "detail": "bad field"},
                {"status": "422", "title": "Invalid", "detail": "other field"},
            ]
        }
    )
    assert "422 Invalid: bad field" in detail
    assert "other field" in detail
