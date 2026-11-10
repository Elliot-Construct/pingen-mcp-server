"""Batches domain: batches.general + batches.events (9 operations).

Contract: each tool is a plain function whose first parameter is a
:class:`pingen_mcp_server.client.PingenClient`, listed in ``TOOLS`` as
``tool_name -> function``. Tool names come from the vendored spec's
operationId with ``.``/``-`` replaced by ``_`` (design.md decision 2).
"""

from __future__ import annotations

from typing import Any

from ..client import PingenClient

PATH_ORG_BATCHES = "/organisations/{organisation_id}/batches"
PATH_ORG_BATCH = PATH_ORG_BATCHES + "/{batch_id}"


def batches_list(
    client: PingenClient,
    organisation_id: str,
    page_number: int | None = None,
    page_limit: int | None = None,
    query: dict[str, str] | None = None,
) -> Any:
    """List batches. GET /organisations/{organisationId}/batches

    ``page_number``/``page_limit`` map to ``page[number]``/``page[limit]``;
    ``query`` keys (sort, filter, q, include, fields[...]) pass through verbatim.
    """
    return client.collection(
        PATH_ORG_BATCHES.format(organisation_id=organisation_id),
        page_number=page_number,
        page_limit=page_limit,
        query=query,
    )


def batches_create(client: PingenClient, organisation_id: str, payload: dict) -> Any:
    """Create a new batch. POST /organisations/{organisationId}/batches

    ``payload`` is the full JSON:API document (CreateBatchPOST), sent verbatim.
    """
    return client.post(
        PATH_ORG_BATCHES.format(organisation_id=organisation_id),
        json_body=payload,
    )


def batches_show(
    client: PingenClient,
    organisation_id: str,
    batch_id: str,
    query: dict[str, str] | None = None,
) -> Any:
    """Get details of a batch. GET /organisations/{organisationId}/batches/{batchId}

    ``query`` keys (fields[batches]) pass through verbatim.
    """
    return client.get(
        PATH_ORG_BATCH.format(organisation_id=organisation_id, batch_id=batch_id),
        params=query or None,
    )


def batches_edit(
    client: PingenClient,
    organisation_id: str,
    batch_id: str,
    payload: dict,
) -> Any:
    """Edit a batch. PATCH /organisations/{organisationId}/batches/{batchId}

    ``payload`` is the full JSON:API document (BatchEditPATCH), sent verbatim.
    """
    return client.patch(
        PATH_ORG_BATCH.format(organisation_id=organisation_id, batch_id=batch_id),
        json_body=payload,
    )


def batches_delete(client: PingenClient, organisation_id: str, batch_id: str, payload: dict) -> Any:
    """Delete a batch. DELETE /organisations/{organisationId}/batches/{batchId}

    The spec marks a required JSON:API request body for this DELETE
    (schema BatchDeleteDELETE); ``payload`` is sent verbatim.
    """
    return client.delete(
        PATH_ORG_BATCH.format(organisation_id=organisation_id, batch_id=batch_id),
        json_body=payload,
    )


def batches_cancel(client: PingenClient, organisation_id: str, batch_id: str) -> Any:
    """Cancel a batch. PATCH /organisations/{organisationId}/batches/{batchId}/cancel

    No request body.
    """
    return client.patch(
        PATH_ORG_BATCH.format(organisation_id=organisation_id, batch_id=batch_id) + "/cancel"
    )


def batches_send(
    client: PingenClient,
    organisation_id: str,
    batch_id: str,
    payload: dict,
) -> Any:
    """Send a batch. PATCH /organisations/{organisationId}/batches/{batchId}/send

    ``payload`` is the full JSON:API document (one of the BatchSendChannel*
    schemas), sent verbatim.
    """
    return client.patch(
        PATH_ORG_BATCH.format(organisation_id=organisation_id, batch_id=batch_id) + "/send",
        json_body=payload,
    )


def batches_events(
    client: PingenClient,
    organisation_id: str,
    batch_id: str,
    page_number: int | None = None,
    page_limit: int | None = None,
    query: dict[str, str] | None = None,
) -> Any:
    """Get a collection of batch events. GET /organisations/{organisationId}/batches/{batchId}/events

    ``page_number``/``page_limit`` map to ``page[number]``/``page[limit]``;
    ``query`` keys (language, sort, filter, q, include, fields[...]) pass
    through verbatim.
    """
    return client.collection(
        PATH_ORG_BATCH.format(organisation_id=organisation_id, batch_id=batch_id) + "/events",
        page_number=page_number,
        page_limit=page_limit,
        query=query,
    )


def organisations_batches_statistics_details(
    client: PingenClient,
    organisation_id: str,
    batch_id: str,
) -> Any:
    """Get statistics of a batch. GET /organisations/{organisationId}/batches/{batchId}/statistics"""
    return client.get(
        PATH_ORG_BATCH.format(organisation_id=organisation_id, batch_id=batch_id) + "/statistics"
    )


TOOLS: dict = {
    "batches_list": batches_list,
    "batches_create": batches_create,
    "batches_show": batches_show,
    "batches_edit": batches_edit,
    "batches_delete": batches_delete,
    "batches_cancel": batches_cancel,
    "batches_send": batches_send,
    "batches_events": batches_events,
    "organisations_batches_statistics_details": organisations_batches_statistics_details,
}
