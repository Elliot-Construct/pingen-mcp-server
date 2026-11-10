"""HTTP client for the Pingen resource API (JSON:API, v2.0.0).

- Bearer token injected per request via the configured token provider.
- Response bodies pass through as parsed JSON, unchanged (JSON:API documents).
- 3xx redirects (file/image endpoints answer 302 per the spec) are NOT
  followed; they return a small ``redirect_url`` envelope so callers can fetch
  the binary themselves.
- Non-2xx responses raise :class:`PingenApiError` summarising the JSON:API
  error payload and carrying ``X-Request-Id``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import httpx

from .auth import TokenProvider
from .config import Config

JSON_API_MEDIA_TYPE = "application/vnd.api+json"


class PingenApiError(RuntimeError):
    """Non-2xx response from the Pingen resource API."""

    def __init__(self, status_code: int, detail: str, *, request_id: str | None = None):
        self.status_code = status_code
        self.request_id = request_id
        self.detail = detail
        message = f"Pingen API request failed with HTTP {status_code}: {detail}"
        if request_id:
            message += f" [X-Request-Id: {request_id}]"
        super().__init__(message)


def summarize_errors(body: Any) -> str:
    """Condense a JSON:API error document (or raw body) into one line."""
    if isinstance(body, dict) and isinstance(body.get("errors"), list):
        parts: list[str] = []
        for err in body["errors"][:3]:
            if not isinstance(err, dict):
                continue
            status = err.get("status", "")
            title = err.get("title") or err.get("detail") or ""
            detail = err.get("detail") if err.get("title") else None
            piece = f"{status} {title}".strip()
            if detail and detail != title:
                piece = f"{piece}: {detail}"
            if piece:
                parts.append(piece)
        if parts:
            return "; ".join(parts)
    if isinstance(body, (dict, list)):
        return json.dumps(body, ensure_ascii=True)[:300]
    return str(body)[:300]


class PingenClient:
    """Thin synchronous JSON:API client used by every domain tool."""

    def __init__(
        self,
        config: Config,
        token_provider: TokenProvider,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 30.0,
    ):
        self._config = config
        self._token_provider = token_provider
        self._http = httpx.Client(transport=transport, timeout=timeout)

    @property
    def config(self) -> Config:
        return self._config

    def close(self) -> None:
        self._http.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        headers: dict[str, str] = {
            "Authorization": f"Bearer {self._token_provider.get_token()}",
            "Accept": JSON_API_MEDIA_TYPE,
        }
        if json_body is not None:
            headers["Content-Type"] = JSON_API_MEDIA_TYPE
        url = self._config.api_base_url + path
        response = self._http.request(
            method, url, json=json_body, params=params, headers=headers
        )
        if 300 <= response.status_code < 400:
            # File/image endpoints answer 302 to the actual binary.
            return {
                "redirect_url": response.headers.get("location"),
                "status_code": response.status_code,
            }
        if response.status_code >= 400:
            try:
                body: Any = response.json()
            except ValueError:
                body = response.text
            raise PingenApiError(
                response.status_code,
                summarize_errors(body),
                request_id=response.headers.get("X-Request-Id"),
            )
        if response.status_code == 204 or not response.content:
            return {}
        try:
            return response.json()
        except ValueError as exc:
            raise PingenApiError(
                response.status_code,
                "response body is not JSON",
                request_id=response.headers.get("X-Request-Id"),
            ) from exc

    def get(self, path: str, params: Mapping[str, Any] | None = None) -> Any:
        return self.request("GET", path, params=params)

    def post(self, path: str, json_body: Any = None) -> Any:
        return self.request("POST", path, json_body=json_body)

    def patch(self, path: str, json_body: Any = None) -> Any:
        return self.request("PATCH", path, json_body=json_body)

    def delete(self, path: str, json_body: Any = None) -> Any:
        # DELETE with a body is unusual but the spec requires it for
        # DELETE /organisations/{organisationId}/batches/{batchId}.
        return self.request("DELETE", path, json_body=json_body)

    def collection(
        self,
        path: str,
        *,
        page_number: int | None = None,
        page_limit: int | None = None,
        query: Mapping[str, Any] | None = None,
    ) -> Any:
        """GET a collection with documented pagination plus query pass-through.

        ``page[number]``/``page[limit]`` default 20/max 100 per the official
        docs; ``query`` keys pass through verbatim (sort/filter/include/fields).
        """
        params: dict[str, Any] = {}
        if page_number is not None:
            params["page[number]"] = page_number
        if page_limit is not None:
            params["page[limit]"] = page_limit
        if query:
            params.update({str(k): v for k, v in query.items()})
        return self.get(path, params=params or None)
