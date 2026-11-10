# Add Pingen MCP server

## Why

Pingen's programmable-mail REST API (letters, eBills, emails, batches; JSON:API, v2.0.0) requires every consumer to hand-roll OAuth 2.0 (two grant types), pagination and endpoint wiring. A single MCP server turns the documented operations into typed tools with auth, environment selection and error handling implemented once and tested once.

## What Changes

- New Python package `pingen_mcp_server` (FastMCP + httpx) exposing **one MCP tool per client-callable operation** in the vendored `reference/openapi.json` (49 operations; the 5 `misc.webhooks` incoming-payload examples become README reference material, not tools).
- OAuth 2.0 support for **both** Pingen grants: client-credentials (server-to-server, server-side token reuse and re-fetch) and authorization-code (delegated end-user access, code exchange, refresh-token rotation).
- Environment-driven configuration: `PINGEN_ENVIRONMENT` selects production or staging hosts, `PINGEN_GRANT_TYPE` selects the grant, credentials load from process env or an env file (`PINGEN_ENV_FILE`). No secrets in the repo.
- Test suite: pytest + respx unit tests (no network) covering auth and every tool's request shape, plus an opt-in live smoke script against staging.
- README documenting install, configuration, both grant flows and the tool inventory.

## Capabilities

### New Capabilities

- `authentication` — client-credentials and authorization-code grants, token cache, refresh rotation, token storage outside the repo
- `server` — FastMCP application, environment configuration, JSON:API client, tool registration and inventory check, installable entry point
- `letters` — letter list/create/get/delete/send/cancel/file/price tools and letter event tools
- `batches` — batch list/create/get/edit/delete/send/cancel/statistics and batch event tools
- `channels` — eBill and email list/create/get/delete/send/cancel/file and event tools
- `webhooks` — organisation webhook registration tools; incoming payload shapes documented
- `directory` — user, associations and organisations read tools
- `files` — file-upload registration tool

### Modified Capabilities

None — the repository contains no specifications today (single initial commit `a658135`).

## Impact

- Affected repos: `github.com/Elliot-Construct/pingen-mcp-server` only (public, MIT). No other repos touched.
- Consumers: any MCP client (Hermes, Claude Desktop/Code, Cursor) able to run a stdio Python server.
- Risks: staging credentials may not be provisioned yet (live smoke stays gated); 49-tool surface can be long for some clients (document name-prefix filtering).
- Out of scope: package publishing/releases, paid infrastructure, inbound webhook listening, binary file-upload proxying.
