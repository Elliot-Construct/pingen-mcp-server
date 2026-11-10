"""Single-object GET tools accept the spec's query params (include, fields[...])
via the ``query`` pass-through. Complements the per-domain suites. No network."""

from __future__ import annotations

import httpx

from pingen_mcp_server.client import PingenClient
from pingen_mcp_server.config import load_config
from pingen_mcp_server.domains import batches, directory, letters

from conftest import FakeTokenProvider, json_api_response

ORG = "11111111-1111-4111-8111-111111111111"
LETTER = "22222222-2222-4222-8222-222222222222"
BATCH = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
EBILL = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
EMAIL = "cccccccc-dddd-eeee-ffff-000000000000"


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


def test_letters_show_query_pass_through(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert dict(request.url.params) == {"include": "organisation"}
        return json_api_response({"data": {"id": LETTER, "type": "letters"}})

    client, calls = make_client(tmp_path, handler)
    letters.letters_show(client, ORG, LETTER, query={"include": "organisation"})
    assert len(calls) == 1
    assert calls[0].url.path == f"/organisations/{ORG}/deliveries/letters/{LETTER}"


def test_batches_show_query_pass_through(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert dict(request.url.params) == {"fields[batches]": "id,created_at"}
        return json_api_response({"data": {"id": BATCH, "type": "batches"}})

    client, calls = make_client(tmp_path, handler)
    batches.batches_show(client, ORG, BATCH, query={"fields[batches]": "id,created_at"})
    assert len(calls) == 1


def test_ebill_and_email_show_query_pass_through(tmp_path):
    from pingen_mcp_server.domains import channels

    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(dict(request.url.params))
        return json_api_response({"data": {"id": "x", "type": "deliverables"}})

    client, _ = make_client(tmp_path, handler)
    channels.deliveries_ebills_show(client, ORG, EBILL, query={"include": "batch"})
    channels.deliveries_emails_show(client, ORG, EMAIL, query={"include": "batch"})
    assert seen == [{"include": "batch"}, {"include": "batch"}]


def test_user_and_organisation_show_query_pass_through(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return json_api_response({"data": {"id": "u", "type": "users"}})

    client, calls = make_client(tmp_path, handler)
    directory.users_show(client, query={"fields[users]": "email"})
    directory.organisations_show(client, ORG, query={"fields[organisations]": "name"})
    assert dict(calls[0].url.params) == {"fields[users]": "email"}
    assert dict(calls[1].url.params) == {"fields[organisations]": "name"}


def test_show_without_query_sends_no_params(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert list(request.url.params.items()) == []
        return json_api_response({"data": {"id": LETTER, "type": "letters"}})

    client, _ = make_client(tmp_path, handler)
    letters.letters_show(client, ORG, LETTER)
