"""Directory domain tests: exact HTTP method + path per operation, pagination
mapping, query pass-through, and the TOOLS inventory. No network: every
request goes through httpx.MockTransport."""

from __future__ import annotations

import httpx

from pingen_mcp_server.client import PingenClient
from pingen_mcp_server.config import load_config
from pingen_mcp_server.domains import directory

from conftest import FakeTokenProvider, json_api_response


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


def test_tools_inventory_covers_exactly_the_four_operations():
    assert sorted(directory.TOOLS) == [
        "organisations_index",
        "organisations_show",
        "user_associations_list",
        "users_show",
    ]
    for name, fn in directory.TOOLS.items():
        assert fn.__name__ == name


def test_users_show_issues_get_user(tmp_path):
    payload = {"data": {"id": "u1", "type": "users"}}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/user"
        assert list(request.url.params.items()) == []  # no payload/query args
        return json_api_response(payload)

    client, calls = make_client(tmp_path, handler)
    assert directory.users_show(client) == payload
    assert len(calls) == 1


def test_user_associations_list_issues_get_with_pagination(tmp_path):
    payload = {"data": [{"id": "a1", "type": "associations"}]}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/user/associations"
        assert dict(request.url.params) == {
            "page[number]": "3",
            "page[limit]": "25",
            "q": "acme",
        }
        return json_api_response(payload)

    client, calls = make_client(tmp_path, handler)
    result = directory.user_associations_list(
        client, page_number=3, page_limit=25, query={"q": "acme"}
    )
    assert result == payload
    assert len(calls) == 1


def test_user_associations_list_without_args_sends_no_query(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/user/associations"
        assert list(request.url.params.items()) == []
        return json_api_response({"data": []})

    client, _ = make_client(tmp_path, handler)
    assert directory.user_associations_list(client) == {"data": []}


def test_organisations_index_issues_get_with_pagination(tmp_path):
    payload = {"data": [{"id": "o1", "type": "organisations"}]}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/organisations"
        assert dict(request.url.params) == {
            "page[number]": "2",
            "page[limit]": "50",
            "sort": "created_at",
        }
        return json_api_response(payload)

    client, calls = make_client(tmp_path, handler)
    result = directory.organisations_index(
        client, page_number=2, page_limit=50, query={"sort": "created_at"}
    )
    assert result == payload
    assert len(calls) == 1


def test_organisations_show_issues_get_organisations_id(tmp_path):
    payload = {"data": {"id": "o1", "type": "organisations"}}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/organisations/o1"
        assert list(request.url.params.items()) == []
        return json_api_response(payload)

    client, calls = make_client(tmp_path, handler)
    assert directory.organisations_show(client, "o1") == payload
    assert len(calls) == 1


def test_organisation_id_is_used_verbatim(tmp_path):
    """The path segment must be built exactly from the supplied id."""
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return json_api_response({"data": {"id": "x", "type": "organisations"}})

    client, _ = make_client(tmp_path, handler)
    directory.organisations_show(client, "o-1")
    assert seen == ["/organisations/o-1"]
