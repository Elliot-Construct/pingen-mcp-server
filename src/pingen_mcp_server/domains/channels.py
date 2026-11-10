"""Channels domain: deliveries.ebills.* + deliveries.emails.* (17 operations).

Contract: each tool is a plain function whose first parameter is a
:class:`pingen_mcp_server.client.PingenClient`, listed in ``TOOLS`` as
``tool_name -> function``. Tool names come from the vendored spec's
operationId with ``.``/``-`` replaced by ``_`` (design.md decision 2).
"""

from __future__ import annotations

from ..client import PingenClient


# --- eBills -----------------------------------------------------------------


def deliveries_ebills_list(
    client: PingenClient,
    organisation_id: str,
    page_number: int | None = None,
    page_limit: int | None = None,
    query: dict[str, str] | None = None,
):
    """Get a collection of ebills. GET /organisations/{organisationId}/deliveries/ebills

    Extra query parameters (sort, filter, q, include, fields[...]) pass
    through verbatim via ``query``; ``page_number``/``page_limit`` map to
    ``page[number]``/``page[limit]``.
    """
    return client.collection(
        f"/organisations/{organisation_id}/deliveries/ebills",
        page_number=page_number,
        page_limit=page_limit,
        query=query,
    )


def deliveries_ebills_create(client: PingenClient, organisation_id: str, payload: dict):
    """Create a new ebill. POST /organisations/{organisationId}/deliveries/ebills

    ``payload`` is the full JSON:API document, sent through unchanged.
    """
    return client.post(
        f"/organisations/{organisation_id}/deliveries/ebills", json_body=payload
    )


def deliveries_ebills_show(
    client: PingenClient,
    organisation_id: str,
    ebill_id: str,
    query: dict[str, str] | None = None,
):
    """Get details of an ebill. GET /organisations/{organisationId}/deliveries/ebills/{ebillId}

    ``query`` keys (include, fields[...]) pass through verbatim.
    """
    return client.get(
        f"/organisations/{organisation_id}/deliveries/ebills/{ebill_id}",
        params=query or None,
    )


def deliveries_ebills_delete(client: PingenClient, organisation_id: str, ebill_id: str):
    """Delete a eBill. DELETE /organisations/{organisationId}/deliveries/ebills/{ebillId}"""
    return client.delete(f"/organisations/{organisation_id}/deliveries/ebills/{ebill_id}")


def deliveries_ebills_send(client: PingenClient, organisation_id: str, ebill_id: str):
    """Send an eBill. PATCH /organisations/{organisationId}/deliveries/ebills/{ebillId}/send

    Sends the eBill immediately; the request carries no body.
    """
    return client.patch(f"/organisations/{organisation_id}/deliveries/ebills/{ebill_id}/send")


def deliveries_ebills_cancel(client: PingenClient, organisation_id: str, ebill_id: str):
    """Cancel an ebill. PATCH /organisations/{organisationId}/deliveries/ebills/{ebillId}/cancel

    Cancels a pending ebill; the request carries no body.
    """
    return client.patch(f"/organisations/{organisation_id}/deliveries/ebills/{ebill_id}/cancel")


def deliveries_ebills_events(
    client: PingenClient,
    organisation_id: str,
    ebill_id: str,
    page_number: int | None = None,
    page_limit: int | None = None,
    query: dict[str, str] | None = None,
):
    """Get a collection of ebill events. GET /organisations/{organisationId}/deliveries/ebills/{ebillId}/events

    Extra query parameters (language, sort, filter, q, include, fields[...])
    pass through verbatim via ``query``.
    """
    return client.collection(
        f"/organisations/{organisation_id}/deliveries/ebills/{ebill_id}/events",
        page_number=page_number,
        page_limit=page_limit,
        query=query,
    )


def deliveries_ebills_file(client: PingenClient, organisation_id: str, ebill_id: str):
    """Get file of ebill. GET /organisations/{organisationId}/deliveries/ebills/{ebillId}/file

    Answers 302 to the stored PDF; returns the ``{"redirect_url",
    "status_code"}`` envelope without following the redirect.
    """
    return client.get(f"/organisations/{organisation_id}/deliveries/ebills/{ebill_id}/file")


def deliveries_ebills_events_image(
    client: PingenClient,
    organisation_id: str,
    ebill_id: str,
    deliverable_event_id: str,
):
    """Get an image of an ebill event. GET /organisations/{organisationId}/deliveries/ebills/{ebillId}/events/{deliverableEventId}/image

    Answers 302 to the image; returns the ``{"redirect_url", "status_code"}``
    envelope without following the redirect.
    """
    return client.get(
        f"/organisations/{organisation_id}/deliveries/ebills/{ebill_id}/events/{deliverable_event_id}/image"
    )


# --- Emails -----------------------------------------------------------------


def deliveries_emails_list(
    client: PingenClient,
    organisation_id: str,
    page_number: int | None = None,
    page_limit: int | None = None,
    query: dict[str, str] | None = None,
):
    """Get a collection of emails. GET /organisations/{organisationId}/deliveries/emails

    Extra query parameters (sort, filter, q, include, fields[...]) pass
    through verbatim via ``query``; ``page_number``/``page_limit`` map to
    ``page[number]``/``page[limit]``.
    """
    return client.collection(
        f"/organisations/{organisation_id}/deliveries/emails",
        page_number=page_number,
        page_limit=page_limit,
        query=query,
    )


def deliveries_emails_create(client: PingenClient, organisation_id: str, payload: dict):
    """Create a new email. POST /organisations/{organisationId}/deliveries/emails

    ``payload`` is the full JSON:API document, sent through unchanged.
    """
    return client.post(
        f"/organisations/{organisation_id}/deliveries/emails", json_body=payload
    )


def deliveries_emails_show(
    client: PingenClient,
    organisation_id: str,
    email_id: str,
    query: dict[str, str] | None = None,
):
    """Get details of an email. GET /organisations/{organisationId}/deliveries/emails/{emailId}

    ``query`` keys (include, fields[...]) pass through verbatim.
    """
    return client.get(
        f"/organisations/{organisation_id}/deliveries/emails/{email_id}",
        params=query or None,
    )


def deliveries_emails_delete(client: PingenClient, organisation_id: str, email_id: str):
    """Delete an email. DELETE /organisations/{organisationId}/deliveries/emails/{emailId}"""
    return client.delete(f"/organisations/{organisation_id}/deliveries/emails/{email_id}")


def deliveries_emails_cancel(client: PingenClient, organisation_id: str, email_id: str):
    """Cancel an email. PATCH /organisations/{organisationId}/deliveries/emails/{emailId}/cancel

    Cancels a pending email; the request carries no body.
    """
    return client.patch(f"/organisations/{organisation_id}/deliveries/emails/{email_id}/cancel")


def deliveries_emails_events(
    client: PingenClient,
    organisation_id: str,
    email_id: str,
    page_number: int | None = None,
    page_limit: int | None = None,
    query: dict[str, str] | None = None,
):
    """Get a collection of email events. GET /organisations/{organisationId}/deliveries/emails/{emailId}/events

    Extra query parameters (language, sort, filter, q, include, fields[...])
    pass through verbatim via ``query``.
    """
    return client.collection(
        f"/organisations/{organisation_id}/deliveries/emails/{email_id}/events",
        page_number=page_number,
        page_limit=page_limit,
        query=query,
    )


def deliveries_emails_file(client: PingenClient, organisation_id: str, email_id: str):
    """Get file of email. GET /organisations/{organisationId}/deliveries/emails/{emailId}/file

    Answers 302 to the stored file; returns the ``{"redirect_url",
    "status_code"}`` envelope without following the redirect.
    """
    return client.get(f"/organisations/{organisation_id}/deliveries/emails/{email_id}/file")


def deliveries_emails_events_image(
    client: PingenClient,
    organisation_id: str,
    email_id: str,
    deliverable_event_id: str,
):
    """Get an image of an email event. GET /organisations/{organisationId}/deliveries/emails/{emailId}/events/{deliverableEventId}/image

    Answers 302 to the image; returns the ``{"redirect_url", "status_code"}``
    envelope without following the redirect.
    """
    return client.get(
        f"/organisations/{organisation_id}/deliveries/emails/{email_id}/events/{deliverable_event_id}/image"
    )


TOOLS: dict = {
    "deliveries_ebills_list": deliveries_ebills_list,
    "deliveries_ebills_create": deliveries_ebills_create,
    "deliveries_ebills_show": deliveries_ebills_show,
    "deliveries_ebills_delete": deliveries_ebills_delete,
    "deliveries_ebills_send": deliveries_ebills_send,
    "deliveries_ebills_cancel": deliveries_ebills_cancel,
    "deliveries_ebills_file": deliveries_ebills_file,
    "deliveries_ebills_events": deliveries_ebills_events,
    "deliveries_ebills_events_image": deliveries_ebills_events_image,
    "deliveries_emails_list": deliveries_emails_list,
    "deliveries_emails_create": deliveries_emails_create,
    "deliveries_emails_show": deliveries_emails_show,
    "deliveries_emails_delete": deliveries_emails_delete,
    "deliveries_emails_cancel": deliveries_emails_cancel,
    "deliveries_emails_file": deliveries_emails_file,
    "deliveries_emails_events": deliveries_emails_events,
    "deliveries_emails_events_image": deliveries_emails_events_image,
}
