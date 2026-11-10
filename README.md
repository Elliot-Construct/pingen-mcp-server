# pingen-mcp-server

Open-source MCP (Model Context Protocol) server for the [Pingen API](https://api.pingen.com/documentation) — programmable physical mail, email and eBill dispatch.

**Status: planning.** Implementation is tracked in the a2aorch registry (project `PINGEN`) and planned with [OpenSpec](https://openspec.dev/).

## Scope

Exposes the Pingen REST API (v2.0.0, JSON:API) as MCP tools:

- **Letters** — create, send, cancel, price, fetch files, events
- **Batches** — create, edit, send, cancel, statistics
- **Channels** — eBill and email dispatch, events
- **Webhooks** — registration and lifecycle notifications
- **User / Organisations / Associations** — read endpoints
- **Files** — upload registration

## Authentication

Supports both OAuth 2.0 grant types offered by Pingen:

1. **Client Credentials grant** — server-to-server, machine tokens (`client_id` + `client_secret`, token refresh handled by the server).
2. **Authorization Code grant** — acting on behalf of an end user who authorises a developer app (delegated access to foreign accounts).

Grant selection is configuration-driven; see the authentication docs in the repo once implementation lands.

## Reference material

- `reference/openapi.json` — the official Pingen OpenAPI 3.0 specification (downloaded from `https://api.pingen.com/documentation/swagger-docs`), vendored so builds are reproducible.
- Live docs: <https://api.pingen.com/documentation>
- Staging environment: `https://identity-staging.pingen.com/auth/register` (1:1 copy of production, letters simulated, nothing printed).

## Licence

MIT — see [LICENSE](LICENSE).

Pingen API and the Pingen name are trademarks of Pingen GmbH; this is an unofficial community integration.
