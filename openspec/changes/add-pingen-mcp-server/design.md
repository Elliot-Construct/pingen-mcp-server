# Design — Pingen MCP server

## Context

- Introducing commit: `a658135` ("Initialise pingen-mcp-server: README, MIT licence, vendored Pingen OpenAPI spec").
- Contract: `reference/openapi.json` — Pingen OpenAPI 3.0.0, API v2.0.0, JSON:API (`application/vnd.api+json`), 2335 schemas, 54 documented operations = **49 client-callable** + 5 `misc.webhooks` incoming-payload examples (Pingen POSTs those to a customer URL; they are not calls we make).
- Official docs (https://api.pingen.com/documentation) confirmed on 2026-11-10: environments, both grants, pagination (`page[number]`/`page[limit]`, default 20, max 100), rate-limit headers (`X-Ratelimit-*`), `X-Request-Id`.

## Goals / Non-Goals

### Goals

- One typed MCP tool per client-callable operation, mechanically checkable against the vendored spec.
- Both OAuth 2.0 grants selectable by configuration; refresh handled server-side; secrets never in the repo.
- Default verification needs no network (mocked HTTP); live verification against staging is opt-in.
- Fresh clone follows README → install → start → list tools.

### Non-Goals

- No inbound webhook listener/server — incoming payload shapes are documented in the README only.
- No binary upload proxying — `GET /file-upload` returns upload registration details; the client uploads directly.
- No auto-pagination across pages; page arguments are exposed instead.
- No package publishing, no paid infrastructure, no changes to other repos.

## Decisions

1. **Stack: Python 3.11+, `fastmcp`, `httpx`, `uv`/`pyproject.toml`; tests with `pytest` + `respx`.** Trade-off: the official MCP TypeScript SDK is equally viable; Python is chosen for the team's pytest/respx tooling and the official Pingen Python SDK patterns. FastMCP derives typed tool schemas from signatures and provides the `fastmcp list/call` verification gate.
2. **1:1 tool mapping (49 tools), named `<domain>_<resource>_<action>`** (e.g. `letters_letter_send`, `channels_ebill_create`). Trade-off: a large tool surface, but a mechanical mapping is the only one that satisfies "tool list matches the vendored spec" without judgement calls; clients may filter by prefix.
3. **JSON:API pass-through.** Tools return response bodies as parsed JSON unchanged — no DTO/normalisation layer. Trade-off: clients see raw `data/attributes/relationships`, but spec drift becomes impossible and minion tests stay declarative (assert method/path/params).
4. **Grant selection by configuration.** `PINGEN_GRANT_TYPE=client_credentials|authorization_code` (default `client_credentials`; unknown values fail fast). Client-credentials: cache token until `expires_in` − 60 s skew, then re-POST. Authorization code: `auth_authorize_url` builds `/auth/authorize` (`response_type=code`, random `state`, 43-char `code_verifier` per docs), `auth_exchange_code` POSTs `grant_type=authorization_code`; refreshes POST `grant_type=refresh_token` and **persist the rotated refresh token** (Pingen revokes the used refresh token on every use).
5. **Environment mapping (docs-confirmed, card corrected).** `PINGEN_ENVIRONMENT=production` → `https://api.pingen.com` + `https://identity.pingen.com`; `=staging` → `https://api-staging.pingen.com` + `https://identity-staging.pingen.com`. The registry card's guessed `api.pingen-staging.com` does **not** exist in the official docs; `api-staging.pingen.com` governs. Bases overridable via `PINGEN_API_BASE_URL`/`PINGEN_IDENTITY_BASE_URL` for tests.
6. **Secrets handling.** Client id/secret come from process env or an env file named by `PINGEN_ENV_FILE` (dev host: `C:/ProgramData/pingen-mcp/credentials.env`, git-ignored scope). Access/refresh tokens persist to `PINGEN_TOKEN_FILE` (default: platform user config dir, outside the repo). Repo ships `.env.example` with placeholder names only. No secret value ever appears in commits, logs, card comments or chat.
7. **Uniform collection arguments.** List tools take optional `page_number`/`page_limit` (mapped to `page[number]`/`page[limit]`) plus an optional `query` mapping passed through verbatim for spec-defined `sort`/`filter`/`include`/`fields` keys. Trade-off: a free-form `query` dict is less self-documenting than per-filter arguments, but keeps 49 tools maintainable against a 6.4 MB spec without inventing filters.
8. **Domain split for parallel implementation** (one sub-agent per domain, integration by the controller): letters (14 ops), batches (9), channels = ebills+emails (17), webhooks (4), directory = user+associations+organisations (4), files (1). Core (`config.py`, `auth.py`, `client.py`, `server.py`) is built first and frozen as the interface the domain modules code against.
9. **Testing strategy.** Unit tests mock HTTP with respx and assert request method, path, query/body shape and error mapping per tool; auth tests prove both grants plus refresh rotation with zero network (criterion c2). Inventory test re-derives expected tools from `reference/openapi.json` at run time (criterion c3). `scripts/staging_smoke.py` is opt-in and never part of the default `pytest` run.

## Risks / Trade-offs

- **Staging credentials may be absent** → live smoke gated on `PINGEN_ENV_FILE`; if unprovisioned, close-out labels the smoke `NOT VERIFIED` rather than faking it.
- **Spec drift:** re-vendoring `reference/openapi.json` later can change the operation set; the inventory test fails loudly on mismatch.
- **6.4 MB spec vs sub-agent context:** controller pre-extracts per-domain operation slices (`scripts/extract_ops.py --tag <tag>`), so each minion reads only its own slice.
- **Refresh rotation bugs** brick delegated sessions after 12 h (`expires_in=43200`); an explicit unit test asserts the new refresh token is persisted.
- **Rate limits** (1000/min headers): v1 does not throttle; errors surface `X-Ratelimit-*` and `X-Request-Id` so callers can back off.
