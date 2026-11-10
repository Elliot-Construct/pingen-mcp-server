"""Letters domain: deliveries.letters.general + deliveries.letters.events (14 operations).

Contract: each tool is a plain function whose first parameter is a
:class:`pingen_mcp_server.client.PingenClient`, listed in ``TOOLS`` as
``tool_name -> function``. Tool names come from the vendored spec's
operationId with ``.``/``-`` replaced by ``_`` (design.md decision 2).
"""

from __future__ import annotations

from typing import Any

from ..client import PingenClient


def letters_list(
    client: PingenClient,
    organisation_id: str,
    page_number: int | None = None,
    page_limit: int | None = None,
    query: dict[str, str] | None = None,
) -> Any:
    """List letters. GET /organisations/{organisationId}/deliveries/letters

    Paginated collection. ``page_number`` maps to ``page[number]`` and
    ``page_limit`` to ``page[limit]``; ``query`` keys (sort, filter, q,
    include, fields[...]) pass through verbatim.
    """
    path = f"/organisations/{organisation_id}/deliveries/letters"
    return client.collection(
        path, page_number=page_number, page_limit=page_limit, query=query
    )


def letters_create(client: PingenClient, organisation_id: str, payload: dict) -> Any:
    """Create a new letter. POST /organisations/{organisationId}/deliveries/letters

    ``payload`` is the full JSON:API document (LetterCreatePOST) and is sent
    unchanged as the request body.
    """
    path = f"/organisations/{organisation_id}/deliveries/letters"
    return client.post(path, json_body=payload)


def letters_show(
    client: PingenClient,
    organisation_id: str,
    letter_id: str,
    query: dict[str, str] | None = None,
) -> Any:
    """Get details of a letter. GET /organisations/{organisationId}/deliveries/letters/{letterId}

    Returns the JSON:API document for a single letter, unchanged.
    ``query`` keys (include, fields[...]) pass through verbatim.
    """
    path = f"/organisations/{organisation_id}/deliveries/letters/{letter_id}"
    return client.get(path, params=query or None)


def letters_delete(client: PingenClient, organisation_id: str, letter_id: str) -> Any:
    """Delete a letter. DELETE /organisations/{organisationId}/deliveries/letters/{letterId}

    Answers 204; the client returns an empty document for empty bodies.
    """
    path = f"/organisations/{organisation_id}/deliveries/letters/{letter_id}"
    return client.delete(path)


def letters_send(
    client: PingenClient, organisation_id: str, letter_id: str, payload: dict
) -> Any:
    """Send a letter. PATCH /organisations/{organisationId}/deliveries/letters/{letterId}/send

    ``payload`` is the full JSON:API document (LetterSendPATCH) and is sent
    unchanged as the request body.
    """
    path = f"/organisations/{organisation_id}/deliveries/letters/{letter_id}/send"
    return client.patch(path, json_body=payload)


def letters_cancel(client: PingenClient, organisation_id: str, letter_id: str) -> Any:
    """Cancel a letter. PATCH /organisations/{organisationId}/deliveries/letters/{letterId}/cancel

    No request body. Answers 202 once the cancellation is queued.
    """
    path = f"/organisations/{organisation_id}/deliveries/letters/{letter_id}/cancel"
    return client.patch(path)


def letters_file(client: PingenClient, organisation_id: str, letter_id: str) -> Any:
    """Get file of letter. GET /organisations/{organisationId}/deliveries/letters/{letterId}/file

    Answers 302 to the rendered PDF; the redirect is NOT followed. Returns
    ``{"redirect_url": ..., "status_code": 302}`` so the caller can fetch the
    binary themselves.
    """
    path = f"/organisations/{organisation_id}/deliveries/letters/{letter_id}/file"
    return client.get(path)


def letters_price_calculator(
    client: PingenClient, organisation_id: str, payload: dict
) -> Any:
    """Calculate price for a letter configuration. POST /organisations/{organisationId}/deliveries/letters/price-calculator

    ``payload`` is the full JSON:API document (LetterPriceCalculatorPOST) and
    is sent unchanged as the request body.
    """
    path = f"/organisations/{organisation_id}/deliveries/letters/price-calculator"
    return client.post(path, json_body=payload)


def letters_events(
    client: PingenClient,
    organisation_id: str,
    letter_id: str,
    page_number: int | None = None,
    page_limit: int | None = None,
    query: dict[str, str] | None = None,
) -> Any:
    """Get a collection of letter events. GET /organisations/{organisationId}/deliveries/letters/{letterId}/events

    Paginated collection. ``page_number`` maps to ``page[number]`` and
    ``page_limit`` to ``page[limit]``; ``query`` keys (language, sort, filter,
    q, include, fields[...]) pass through verbatim.
    """
    path = f"/organisations/{organisation_id}/deliveries/letters/{letter_id}/events"
    return client.collection(
        path, page_number=page_number, page_limit=page_limit, query=query
    )


def letters_events_image(
    client: PingenClient, organisation_id: str, letter_id: str, letter_event_id: str
) -> Any:
    """Get an image of a letter event. GET /organisations/{organisationId}/deliveries/letters/{letterId}/events/{letterEventId}/image

    Answers 302 to the actual image; the redirect is NOT followed. Returns
    ``{"redirect_url": ..., "status_code": 302}`` so the caller can fetch the
    image themselves.
    """
    path = (
        f"/organisations/{organisation_id}/deliveries/letters/{letter_id}"
        f"/events/{letter_event_id}/image"
    )
    return client.get(path)


def organisations_letters_events_delivered(
    client: PingenClient,
    organisation_id: str,
    page_number: int | None = None,
    page_limit: int | None = None,
    query: dict[str, str] | None = None,
) -> Any:
    """Get a collection of all delivered events. GET /organisations/{organisationId}/deliveries/letters/events/delivered

    Organisation-wide, paginated collection. ``page_number`` maps to
    ``page[number]`` and ``page_limit`` to ``page[limit]``; ``query`` keys
    (language, filter, q, include, fields[...]) pass through verbatim.
    """
    path = f"/organisations/{organisation_id}/deliveries/letters/events/delivered"
    return client.collection(
        path, page_number=page_number, page_limit=page_limit, query=query
    )


def organisations_letters_events_issues(
    client: PingenClient,
    organisation_id: str,
    page_number: int | None = None,
    page_limit: int | None = None,
    query: dict[str, str] | None = None,
) -> Any:
    """Get a collection of all issue events. GET /organisations/{organisationId}/deliveries/letters/events/issues

    Organisation-wide, paginated collection. ``page_number`` maps to
    ``page[number]`` and ``page_limit`` to ``page[limit]``; ``query`` keys
    (language, filter, q, include, fields[...]) pass through verbatim.
    """
    path = f"/organisations/{organisation_id}/deliveries/letters/events/issues"
    return client.collection(
        path, page_number=page_number, page_limit=page_limit, query=query
    )


def organisations_letters_events_sent(
    client: PingenClient,
    organisation_id: str,
    page_number: int | None = None,
    page_limit: int | None = None,
    query: dict[str, str] | None = None,
) -> Any:
    """Get a collection of all sent events. GET /organisations/{organisationId}/deliveries/letters/events/sent

    Organisation-wide, paginated collection. ``page_number`` maps to
    ``page[number]`` and ``page_limit`` to ``page[limit]``; ``query`` keys
    (language, filter, q, include, fields[...]) pass through verbatim.
    """
    path = f"/organisations/{organisation_id}/deliveries/letters/events/sent"
    return client.collection(
        path, page_number=page_number, page_limit=page_limit, query=query
    )


def organisations_letters_events_undeliverable(
    client: PingenClient,
    organisation_id: str,
    page_number: int | None = None,
    page_limit: int | None = None,
    query: dict[str, str] | None = None,
) -> Any:
    """Get a collection of all undeliverable events. GET /organisations/{organisationId}/deliveries/letters/events/undeliverable

    Organisation-wide, paginated collection. ``page_number`` maps to
    ``page[number]`` and ``page_limit`` to ``page[limit]``; ``query`` keys
    (language, filter, q, include, fields[...]) pass through verbatim.
    """
    path = f"/organisations/{organisation_id}/deliveries/letters/events/undeliverable"
    return client.collection(
        path, page_number=page_number, page_limit=page_limit, query=query
    )


TOOLS: dict = {
    "letters_list": letters_list,
    "letters_create": letters_create,
    "letters_show": letters_show,
    "letters_delete": letters_delete,
    "letters_send": letters_send,
    "letters_cancel": letters_cancel,
    "letters_file": letters_file,
    "letters_price_calculator": letters_price_calculator,
    "letters_events": letters_events,
    "letters_events_image": letters_events_image,
    "organisations_letters_events_delivered": organisations_letters_events_delivered,
    "organisations_letters_events_issues": organisations_letters_events_issues,
    "organisations_letters_events_sent": organisations_letters_events_sent,
    "organisations_letters_events_undeliverable": organisations_letters_events_undeliverable,
}
