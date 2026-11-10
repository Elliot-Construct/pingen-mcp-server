"""Webhooks domain: organisations.management.webhooks (4 operations); incoming payloads documented in README, not tools.

Contract: each tool is a plain function whose first parameter is a
:class:`pingen_mcp_server.client.PingenClient`, listed in ``TOOLS`` as
``tool_name -> function``. Tool names come from the vendored spec's
operationId with ``.``/``-`` replaced by ``_`` (design.md decision 2).
"""

from __future__ import annotations

from typing import Any

from pingen_mcp_server.client import PingenClient


def webhooks_index(
    client: PingenClient,
    organisation_id: str,
    page_number: int | None = None,
    page_limit: int | None = None,
    query: dict[str, str] | None = None,
) -> Any:
    """List organisation webhooks. GET /organisations/{organisationId}/webhooks

    Pagination maps to ``page[number]``/``page[limit]``; ``query`` keys
    (filter, q, include, fields[...]) pass through verbatim.
    """
    return client.collection(
        f"/organisations/{organisation_id}/webhooks",
        page_number=page_number,
        page_limit=page_limit,
        query=query,
    )


def webhooks_create(client: PingenClient, organisation_id: str, payload: dict) -> Any:
    """Create new webhook. POST /organisations/{organisationId}/webhooks

    ``payload`` is the full JSON:API document (``data``/``attributes``),
    passed through unchanged.
    """
    return client.post(
        f"/organisations/{organisation_id}/webhooks", json_body=payload
    )


def webhooks_show(
    client: PingenClient, organisation_id: str, webhook_id: str
) -> Any:
    """Get details of a webhook. GET /organisations/{organisationId}/webhooks/{webhookId}"""
    return client.get(f"/organisations/{organisation_id}/webhooks/{webhook_id}")


def webhooks_destroy(
    client: PingenClient, organisation_id: str, webhook_id: str
) -> Any:
    """Delete a webhook. DELETE /organisations/{organisationId}/webhooks/{webhookId}"""
    return client.delete(f"/organisations/{organisation_id}/webhooks/{webhook_id}")


TOOLS: dict = {
    "webhooks_index": webhooks_index,
    "webhooks_create": webhooks_create,
    "webhooks_show": webhooks_show,
    "webhooks_destroy": webhooks_destroy,
}
