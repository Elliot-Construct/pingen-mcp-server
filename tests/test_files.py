"""Files domain tests: exact HTTP method + path for the file upload
registration operation, optional fields[...] query mapping, JSON:API
passthrough, and TOOLS exactness. All HTTP via httpx.MockTransport - no
network."""

from __future__ import annotations

import inspect

import httpx

from pingen_mcp_server.client import PingenClient
from pingen_mcp_server.config import load_config
from pingen_mcp_server.domains import files
from pingen_mcp_server.domains.files import TOOLS

from conftest import FakeTokenProvider, json_api_response

EXPECTED_TOOLS = {"files_file_upload"}

# The module docstring must advertise HTTP method + path (module contract).
DOCSTRING_ENDPOINT = "GET /file-upload"


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


def test_file_upload_sends_get_to_file_upload_path(tmp_path):
    payload = {
        "data": {
            "id": "fu1",
            "type": "file_uploads",
            "attributes": {
                "url": "https://upload.example/abc",
                "method": "PUT",
            },
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/file-upload"
        # Only optional query param in the slice, not supplied here.
        assert list(request.url.params.items()) == []
        assert request.headers["Accept"] == "application/vnd.api+json"
        return json_api_response(payload)

    client, calls = make_client(tmp_path, handler)
    result = files.files_file_upload(client)
    assert result == payload  # JSON:API response passes through unchanged
    assert len(calls) == 1


def test_file_upload_forwards_optional_fields_query_param(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/file-upload"
        assert dict(request.url.params) == {"fields[file_uploads]": "url"}
        return json_api_response({"data": {"id": "fu1", "type": "file_uploads"}})

    client, calls = make_client(tmp_path, handler)
    result = files.files_file_upload(client, fields_file_uploads="url")
    assert result["data"]["id"] == "fu1"
    assert len(calls) == 1


def test_file_upload_is_registration_metadata_only(tmp_path):
    # The response (upload destination etc) is returned as-is: no envelope,
    # no byte proxying, no reshaping by the tool.
    payload = {"data": {"id": "fu1", "type": "file_uploads", "attributes": {}}}

    def handler(request: httpx.Request) -> httpx.Response:
        return json_api_response(payload)

    client, _ = make_client(tmp_path, handler)
    assert files.files_file_upload(client) == payload


def test_tools_are_exactly_the_one_documented_operation():
    assert set(TOOLS) == EXPECTED_TOOLS
    for name, fn in TOOLS.items():
        assert callable(fn), name
        assert inspect.isfunction(fn), name


def test_tool_first_parameter_is_client_and_rest_optional():
    params = list(inspect.signature(files.files_file_upload).parameters.values())
    assert params[0].name == "client"
    assert params[0].annotation is not inspect.Parameter.empty
    for p in params[1:]:
        assert p.default is not inspect.Parameter.empty, (
            f"{p.name} must be optional (slice marks no required params)"
        )


def test_docstring_includes_http_method_and_path():
    assert DOCSTRING_ENDPOINT in (files.files_file_upload.__doc__ or "")
