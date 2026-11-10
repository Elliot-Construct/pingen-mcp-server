"""Channels domain tests: 17 deliveries.ebills.*/deliveries.emails.* operations.

Each operation gets a test asserting the exact HTTP method + path; list
operations additionally assert page[number]/page[limit] mapping and query
pass-through; body operations assert the payload travels unchanged. All HTTP
goes through httpx.MockTransport - no network.
"""

from __future__ import annotations

import json

import httpx

from pingen_mcp_server.client import PingenClient
from pingen_mcp_server.config import load_config
from pingen_mcp_server.domains import channels

from conftest import FakeTokenProvider, json_api_response

ORG = "11111111-1111-1111-1111-111111111111"
EBILL = "22222222-2222-2222-2222-222222222222"
EMAIL = "33333333-3333-3333-3333-333333333333"
EVENT = "44444444-4444-4444-4444-444444444444"

EXPECTED_TOOLS = {
    "deliveries_ebills_list",
    "deliveries_ebills_create",
    "deliveries_ebills_show",
    "deliveries_ebills_delete",
    "deliveries_ebills_send",
    "deliveries_ebills_cancel",
    "deliveries_ebills_file",
    "deliveries_ebills_events",
    "deliveries_ebills_events_image",
    "deliveries_emails_list",
    "deliveries_emails_create",
    "deliveries_emails_show",
    "deliveries_emails_delete",
    "deliveries_emails_cancel",
    "deliveries_emails_file",
    "deliveries_emails_events",
    "deliveries_emails_events_image",
}


def make_client(tmp_path, handler):
    """PingenClient over a MockTransport; returns (client, calls)."""
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


def one_call(calls):
    assert len(calls) == 1
    return calls[0]


# --- inventory ---------------------------------------------------------------


def test_tools_exports_exactly_the_17_channel_operations():
    assert set(channels.TOOLS) == EXPECTED_TOOLS
    assert len(channels.TOOLS) == 17


def test_every_tool_docstring_names_method_and_path():
    for name, fn in channels.TOOLS.items():
        doc = (fn.__doc__ or "").strip().splitlines()[0]
        method_ok = any(m in doc for m in (" GET ", " POST ", " PATCH ", " DELETE "))
        path_ok = "/organisations/{organisationId}" in doc
        assert method_ok and path_ok, f"{name}: docstring lacks method/path: {doc!r}"


# --- ebills -----------------------------------------------------------------


def test_ebills_list_maps_pagination_and_passes_query(tmp_path):
    def handler(request):
        assert request.method == "GET"
        assert request.url.path == f"/organisations/{ORG}/deliveries/ebills"
        assert dict(request.url.params) == {
            "page[number]": "2",
            "page[limit]": "50",
            "filter[status]": "created",
        }
        return json_api_response({"data": []})

    client, calls = make_client(tmp_path, handler)
    channels.deliveries_ebills_list(
        client,
        ORG,
        page_number=2,
        page_limit=50,
        query={"filter[status]": "created"},
    )
    one_call(calls)


def test_ebills_list_without_pagination_sends_no_query(tmp_path):
    def handler(request):
        assert request.method == "GET"
        assert request.url.path == f"/organisations/{ORG}/deliveries/ebills"
        assert list(request.url.params.items()) == []
        return json_api_response({"data": []})

    client, calls = make_client(tmp_path, handler)
    channels.deliveries_ebills_list(client, ORG)
    one_call(calls)


def test_ebills_create_posts_payload_unchanged(tmp_path):
    payload = {
        "data": {
            "type": "ebills",
            "attributes": {"auto_send": False, "receiver_email": "a@example.com"},
        }
    }

    def handler(request):
        assert request.method == "POST"
        assert request.url.path == f"/organisations/{ORG}/deliveries/ebills"
        assert request.headers["Content-Type"] == "application/vnd.api+json"
        assert json.loads(request.content) == payload
        return json_api_response({"data": {"id": "e1", "type": "ebills"}}, status=201)

    client, calls = make_client(tmp_path, handler)
    result = channels.deliveries_ebills_create(client, ORG, payload)
    assert result["data"]["id"] == "e1"
    one_call(calls)


def test_ebills_show_gets_single_ebill(tmp_path):
    def handler(request):
        assert request.method == "GET"
        assert request.url.path == f"/organisations/{ORG}/deliveries/ebills/{EBILL}"
        return json_api_response({"data": {"id": EBILL, "type": "ebills"}})

    client, calls = make_client(tmp_path, handler)
    result = channels.deliveries_ebills_show(client, ORG, EBILL)
    assert result["data"]["id"] == EBILL
    one_call(calls)


def test_ebills_delete_deletes_single_ebill(tmp_path):
    def handler(request):
        assert request.method == "DELETE"
        assert request.url.path == f"/organisations/{ORG}/deliveries/ebills/{EBILL}"
        return httpx.Response(204)

    client, calls = make_client(tmp_path, handler)
    assert channels.deliveries_ebills_delete(client, ORG, EBILL) == {}
    one_call(calls)


def test_ebills_send_patches_without_body(tmp_path):
    def handler(request):
        assert request.method == "PATCH"
        assert request.url.path == f"/organisations/{ORG}/deliveries/ebills/{EBILL}/send"
        assert request.content == b""
        return json_api_response({"data": {"id": EBILL, "type": "ebills"}})

    client, calls = make_client(tmp_path, handler)
    channels.deliveries_ebills_send(client, ORG, EBILL)
    one_call(calls)


def test_ebills_cancel_patches_without_body(tmp_path):
    def handler(request):
        assert request.method == "PATCH"
        assert request.url.path == f"/organisations/{ORG}/deliveries/ebills/{EBILL}/cancel"
        assert request.content == b""
        return httpx.Response(202)

    client, calls = make_client(tmp_path, handler)
    channels.deliveries_ebills_cancel(client, ORG, EBILL)
    one_call(calls)


def test_ebills_events_lists_with_pagination_and_query(tmp_path):
    def handler(request):
        assert request.method == "GET"
        assert request.url.path == f"/organisations/{ORG}/deliveries/ebills/{EBILL}/events"
        assert dict(request.url.params) == {
            "page[number]": "3",
            "page[limit]": "10",
            "language": "de-DE",
        }
        return json_api_response({"data": []})

    client, calls = make_client(tmp_path, handler)
    channels.deliveries_ebills_events(
        client, ORG, EBILL, page_number=3, page_limit=10, query={"language": "de-DE"}
    )
    one_call(calls)


def test_ebills_file_returns_redirect_envelope(tmp_path):
    def handler(request):
        assert request.method == "GET"
        assert request.url.path == f"/organisations/{ORG}/deliveries/ebills/{EBILL}/file"
        return httpx.Response(
            302, headers={"Location": "https://files.example/ebill.pdf"}
        )

    client, calls = make_client(tmp_path, handler)
    result = channels.deliveries_ebills_file(client, ORG, EBILL)
    assert result == {
        "redirect_url": "https://files.example/ebill.pdf",
        "status_code": 302,
    }
    assert len(calls) == 1  # redirect never followed


def test_ebills_events_image_returns_redirect_envelope(tmp_path):
    def handler(request):
        assert request.method == "GET"
        assert (
            request.url.path
            == f"/organisations/{ORG}/deliveries/ebills/{EBILL}/events/{EVENT}/image"
        )
        return httpx.Response(
            302, headers={"Location": "https://files.example/event.png"}
        )

    client, calls = make_client(tmp_path, handler)
    result = channels.deliveries_ebills_events_image(client, ORG, EBILL, EVENT)
    assert result == {
        "redirect_url": "https://files.example/event.png",
        "status_code": 302,
    }
    assert len(calls) == 1  # redirect never followed


# --- emails -----------------------------------------------------------------


def test_emails_list_maps_pagination_and_passes_query(tmp_path):
    def handler(request):
        assert request.method == "GET"
        assert request.url.path == f"/organisations/{ORG}/deliveries/emails"
        assert dict(request.url.params) == {
            "page[number]": "4",
            "page[limit]": "25",
            "q": "invoice",
        }
        return json_api_response({"data": []})

    client, calls = make_client(tmp_path, handler)
    channels.deliveries_emails_list(
        client, ORG, page_number=4, page_limit=25, query={"q": "invoice"}
    )
    one_call(calls)


def test_emails_create_posts_payload_unchanged(tmp_path):
    payload = {
        "data": {
            "type": "emails",
            "attributes": {"receiver_email": "b@example.com", "subject": "Hello"},
        }
    }

    def handler(request):
        assert request.method == "POST"
        assert request.url.path == f"/organisations/{ORG}/deliveries/emails"
        assert request.headers["Content-Type"] == "application/vnd.api+json"
        assert json.loads(request.content) == payload
        return json_api_response({"data": {"id": "m1", "type": "emails"}}, status=201)

    client, calls = make_client(tmp_path, handler)
    result = channels.deliveries_emails_create(client, ORG, payload)
    assert result["data"]["id"] == "m1"
    one_call(calls)


def test_emails_show_gets_single_email(tmp_path):
    def handler(request):
        assert request.method == "GET"
        assert request.url.path == f"/organisations/{ORG}/deliveries/emails/{EMAIL}"
        return json_api_response({"data": {"id": EMAIL, "type": "emails"}})

    client, calls = make_client(tmp_path, handler)
    result = channels.deliveries_emails_show(client, ORG, EMAIL)
    assert result["data"]["id"] == EMAIL
    one_call(calls)


def test_emails_delete_deletes_single_email(tmp_path):
    def handler(request):
        assert request.method == "DELETE"
        assert request.url.path == f"/organisations/{ORG}/deliveries/emails/{EMAIL}"
        return httpx.Response(204)

    client, calls = make_client(tmp_path, handler)
    assert channels.deliveries_emails_delete(client, ORG, EMAIL) == {}
    one_call(calls)


def test_emails_cancel_patches_without_body(tmp_path):
    def handler(request):
        assert request.method == "PATCH"
        assert request.url.path == f"/organisations/{ORG}/deliveries/emails/{EMAIL}/cancel"
        assert request.content == b""
        return httpx.Response(202)

    client, calls = make_client(tmp_path, handler)
    channels.deliveries_emails_cancel(client, ORG, EMAIL)
    one_call(calls)


def test_emails_events_lists_with_pagination_and_query(tmp_path):
    def handler(request):
        assert request.method == "GET"
        assert request.url.path == f"/organisations/{ORG}/deliveries/emails/{EMAIL}/events"
        assert dict(request.url.params) == {
            "page[number]": "1",
            "page[limit]": "5",
            "language": "fr-FR",
        }
        return json_api_response({"data": []})

    client, calls = make_client(tmp_path, handler)
    channels.deliveries_emails_events(
        client, ORG, EMAIL, page_number=1, page_limit=5, query={"language": "fr-FR"}
    )
    one_call(calls)


def test_emails_file_returns_redirect_envelope(tmp_path):
    def handler(request):
        assert request.method == "GET"
        assert request.url.path == f"/organisations/{ORG}/deliveries/emails/{EMAIL}/file"
        return httpx.Response(
            302, headers={"Location": "https://files.example/email.pdf"}
        )

    client, calls = make_client(tmp_path, handler)
    result = channels.deliveries_emails_file(client, ORG, EMAIL)
    assert result == {
        "redirect_url": "https://files.example/email.pdf",
        "status_code": 302,
    }
    assert len(calls) == 1  # redirect never followed


def test_emails_events_image_returns_redirect_envelope(tmp_path):
    def handler(request):
        assert request.method == "GET"
        assert (
            request.url.path
            == f"/organisations/{ORG}/deliveries/emails/{EMAIL}/events/{EVENT}/image"
        )
        return httpx.Response(
            302, headers={"Location": "https://files.example/email-event.png"}
        )

    client, calls = make_client(tmp_path, handler)
    result = channels.deliveries_emails_events_image(client, ORG, EMAIL, EVENT)
    assert result == {
        "redirect_url": "https://files.example/email-event.png",
        "status_code": 302,
    }
    assert len(calls) == 1  # redirect never followed


# --- contract shape ----------------------------------------------------------


def test_list_operations_expose_pagination_signature():
    import inspect

    for fn in (
        channels.deliveries_ebills_list,
        channels.deliveries_emails_list,
        channels.deliveries_ebills_events,
        channels.deliveries_emails_events,
    ):
        params = list(inspect.signature(fn).parameters)
        assert params == [
            "client",
            "organisation_id",
            *[p for p in params if p in ("ebill_id", "email_id")],
            "page_number",
            "page_limit",
            "query",
        ]


def test_create_operations_require_payload():
    import inspect

    for fn in (channels.deliveries_ebills_create, channels.deliveries_emails_create):
        sig = inspect.signature(fn)
        assert list(sig.parameters) == ["client", "organisation_id", "payload"]
        assert sig.parameters["payload"].default is inspect.Parameter.empty


def test_emails_channel_has_no_send_operation():
    assert not any(name.endswith("_send") and "emails" in name for name in channels.TOOLS)
