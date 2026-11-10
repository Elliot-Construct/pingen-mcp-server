"""Directory domain: user.general + user.associations + organisations.general (4 operations).

Contract: each tool is a plain function whose first parameter is a
:class:`pingen_mcp_server.client.PingenClient`, listed in ``TOOLS`` as
``tool_name -> function``. Tool names come from the vendored spec's
operationId with ``.``/``-`` replaced by ``_`` (design.md decision 2).
"""

from __future__ import annotations

from typing import Any

from ..client import PingenClient


def users_show(client: PingenClient, query: dict[str, str] | None = None) -> Any:
    """Get details of the authenticated user. GET /user

    ``query`` keys (fields[users]) pass through verbatim.
    """
    return client.get("/user", params=query or None)


def user_associations_list(
    client: PingenClient,
    page_number: int | None = None,
    page_limit: int | None = None,
    query: dict[str, str] | None = None,
) -> Any:
    """Get collection of associations of the authenticated user.

    GET /user/associations

    ``page_number``/``page_limit`` map to ``page[number]``/``page[limit]``;
    ``query`` passes extra query parameters (sort, filter, q, include,
    fields[...]) through verbatim.
    """
    return client.collection(
        "/user/associations",
        page_number=page_number,
        page_limit=page_limit,
        query=query,
    )


def organisations_index(
    client: PingenClient,
    page_number: int | None = None,
    page_limit: int | None = None,
    query: dict[str, str] | None = None,
) -> Any:
    """Get collection of organisations. GET /organisations

    ``page_number``/``page_limit`` map to ``page[number]``/``page[limit]``;
    ``query`` passes extra query parameters (sort, filter, q,
    fields[organisations]) through verbatim.
    """
    return client.collection(
        "/organisations",
        page_number=page_number,
        page_limit=page_limit,
        query=query,
    )


def organisations_show(
    client: PingenClient, organisation_id: str, query: dict[str, str] | None = None
) -> Any:
    """Get details of an organisation. GET /organisations/{organisationId}

    ``query`` keys (fields[organisations]) pass through verbatim.
    """
    return client.get(f"/organisations/{organisation_id}", params=query or None)


TOOLS: dict = {
    "users_show": users_show,
    "user_associations_list": user_associations_list,
    "organisations_index": organisations_index,
    "organisations_show": organisations_show,
}
