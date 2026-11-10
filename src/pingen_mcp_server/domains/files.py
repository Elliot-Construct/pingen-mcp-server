"""Files domain: misc.files (1 operation: file upload registration).

Contract: each tool is a plain function whose first parameter is a
:class:`pingen_mcp_server.client.PingenClient`, listed in ``TOOLS`` as
``tool_name -> function``. Tool names come from the vendored spec's
operationId with ``.``/``-`` replaced by ``_`` (design.md decision 2).
"""

from __future__ import annotations

from typing import Any

from ..client import PingenClient


def files_file_upload(
    client: PingenClient, fields_file_uploads: str | None = None
) -> Any:
    """Get details for file upload (upload registration/destination etc). GET /file-upload

    Registration metadata only: the server never proxies file bytes, so the
    JSON:API response passes through unchanged. The optional
    ``fields_file_uploads`` argument maps to the query parameter
    ``fields[file_uploads]`` (which attributes of ``file_uploads`` to return)
    and is omitted from the request when not given.
    """
    params = (
        {"fields[file_uploads]": fields_file_uploads}
        if fields_file_uploads is not None
        else None
    )
    return client.get("/file-upload", params=params)


TOOLS: dict = {"files_file_upload": files_file_upload}
