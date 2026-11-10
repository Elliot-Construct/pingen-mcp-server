# pingen-mcp-server

Open-source MCP (Model Context Protocol) server for the [Pingen API](https://api.pingen.com/documentation) — programmable physical mail, email and eBill dispatch.

**49 MCP tools — one per client-callable operation** of the official Pingen OpenAPI specification (v2.0.0, JSON:API), with **both OAuth 2.0 grant types** supported. Responses are JSON:API documents passed through unchanged, so what you get back is exactly what the API returns.

Implementation is tracked in the a2aorch registry (project `PINGEN`) and planned with [OpenSpec](https://openspec.dev/).

## Scope

| Domain | Tools | Covers |
| --- | ---: | --- |
| Letters | 14 | list/create/show/delete/send/cancel, file, price calculator, events (per-letter + organisation-wide) |
| Batches | 9 | list/create/show/edit/delete/send/cancel, statistics, events |
| eBills | 9 | list/create/show/delete/send/cancel, file, events, event image |
| Emails | 8 | list/create/show/delete/cancel, file, events, event image |
| Webhooks | 4 | organisation webhook registrations (list/create/show/delete) |
| User / Organisations / Associations | 4 | authenticated user, associations, organisation list/details |
| Files | 1 | file-upload registration |

The five *incoming* webhook payload shapes (`/your-webhook-url-for-*`) are documentation, not tools — see [Incoming webhooks](#incoming-webhooks).

## Install

```bash
git clone https://github.com/Elliot-Construct/pingen-mcp-server.git
cd pingen-mcp-server
python -m venv .venv
.venv/bin/pip install -e .        # Windows: .venv\Scripts\pip install -e .
```

Verify — no credentials required to list the tools:

```bash
python -c "import asyncio; from pingen_mcp_server.server import mcp; print(len(asyncio.run(mcp.list_tools())), 'tools')"
```

Run the test suite (all HTTP mocked — no network, no credentials):

```bash
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest
```

### MCP client configuration

```json
{
  "mcpServers": {
    "pingen": {
      "command": "/path/to/pingen-mcp-server/.venv/bin/python",
      "args": ["-m", "pingen_mcp_server.server"],
      "env": {
        "PINGEN_ENVIRONMENT": "staging",
        "PINGEN_GRANT_TYPE": "client_credentials",
        "PINGEN_ENV_FILE": "/secure/location/credentials.env"
      }
    }
  }
}
```

`pingen-mcp-server` (installed console script) and `python -m pingen_mcp_server.server` both start the server over stdio.

## Configuration

All configuration is environment-driven. Secrets never live in this repository.

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `PINGEN_ENVIRONMENT` | no | `production` | `production` or `staging` (see hosts below) |
| `PINGEN_GRANT_TYPE` | no | `client_credentials` | `client_credentials` or `authorization_code`; invalid values fail at startup |
| `PINGEN_CLIENT_ID` / `PINGEN_CLIENT_SECRET` | yes* | – | from your Pingen developer app |
| `PINGEN_ENV_FILE` | no | – | path to an env file with the keys above (used when not set in the process environment) |
| `PINGEN_REDIRECT_URI` | auth-code only | – | registered redirect URI for the authorization-code grant |
| `PINGEN_SCOPES` | no | app defaults | space-separated scopes (`letter batch email ebill template webhook organisation_read`) |
| `PINGEN_TOKEN_FILE` | no | `<user config dir>/pingen-mcp/tokens.json` | access/refresh token storage, always outside the repo |
| `PINGEN_API_BASE_URL` / `PINGEN_IDENTITY_BASE_URL` | no | env defaults | overrides, mainly for tests |

\* needed when a tool actually fetches a token; listing tools works without them.

### Environments

| | Resource API | Identity (tokens) |
| --- | --- | --- |
| Production | `https://api.pingen.com` | `https://identity.pingen.com` |
| Staging | `https://api-staging.pingen.com` | `https://identity-staging.pingen.com` |

Staging is a fully separate 1:1 environment — register at <https://identity-staging.pingen.com/auth/register> and create **separate** developer-app credentials. Letters are simulated (nothing is printed).

## Authentication

### Client credentials (default, server-to-server)

On first tool use the server POSTs `grant_type=client_credentials` to the identity host, caches the access token until `expires_in` minus a 60-second skew, then re-fetches automatically. This grant issues no refresh token.

### Authorization code (delegated access to a foreign account)

Interactive flows cannot complete inside an MCP tool call, so the exchange is driven through the auth module's Python API:

```python
from pingen_mcp_server.auth import provider_for
from pingen_mcp_server.config import load_config

provider = provider_for(load_config())

step1 = provider.build_authorize_url()
# Open step1["url"] in a browser; the user consents; the redirect
# carries ?code=...&state=...
provider.exchange_code(
    code="...",                       # from the redirect
    state="...",                      # from the redirect
    expected_state=step1["state"],    # verified with a constant-time compare
    code_verifier=step1["code_verifier"],
)
```

Subsequent tool calls refresh transparently with `grant_type=refresh_token`. **Pingen revokes the used refresh token on every use** — the server persists the rotated token before the next request. Tokens are stored at `PINGEN_TOKEN_FILE` (outside the repository); secrets are never committed, logged or printed.

## Public deployment (streamable HTTP)

Without HTTP configuration the entry point runs **stdio** exactly as above. Set
`PINGEN_MCP_PUBLIC_URL` and it instead serves **streamable HTTP** on
`PINGEN_MCP_PORT`, gated by resource-server authentication:

| Variable | Required in HTTP mode | Meaning |
| --- | --- | --- |
| `PINGEN_MCP_PUBLIC_URL` | yes | Canonical resource URL, e.g. `https://pingen-mcp.datawyse.ai/mcp` |
| `PINGEN_MCP_AUTH_ISSUER` | yes | Expected JWT `iss` (the identity layer's realm issuer) |
| `PINGEN_MCP_AUTH_JWKS_URI` | yes | Where signing keys are fetched from |
| `PINGEN_MCP_AUTH_AUDIENCE` | yes | Expected JWT `aud` — normally the same as `PINGEN_MCP_PUBLIC_URL` |
| `PINGEN_MCP_PORT` | no (8747) | Listen port |
| `PINGEN_MCP_BIND` | no (127.0.0.1) | Bind address; containers use `0.0.0.0` |

HTTP mode is **all or nothing**: a partial set of these variables fails at
startup with an error naming the missing ones, rather than silently serving an
unauthenticated endpoint.

**Behaviour when deployed.** Unauthenticated requests get `401` with
`WWW-Authenticate: Bearer resource_metadata="…"` pointing at the RFC 9728
document served at `/.well-known/oauth-protected-resource/<path>`, which in
turn names the authorization server. Tokens are validated against the identity
layer's JWKS for signature, issuer, expiry **and audience** — a validly signed
token minted for a different audience is rejected. Any `Host` other than the
configured public hostname is refused with `421` before authentication runs.

### Behind a reverse proxy

Point a `Host()` router at the container/process and give it its own
certificate. Do **not** put a `basicAuth`/`forwardAuth` middleware in front of
it: those consume the `Authorization` header the MCP client sends, and the
discovery paths must stay reachable anonymously. Authentication belongs to this
server. The container publishes no port at all, so the proxy is the only path
in.

### Provisioning a consumer client

The authorization server must be given a client before any consumer can obtain
a token. Create a **confidential** OpenID Connect client with:

- standard flow enabled, `S256` PKCE (authorization code + refresh token)
- service accounts enabled if the consumer is headless (client credentials)
- an **audience** protocol mapper whose value equals `PINGEN_MCP_PUBLIC_URL`,
  otherwise the resource server rejects every token on `aud`
- the consumer's exact redirect URI(s). Redirect URIs are matched exactly, so
  interactive consumers must use the registered port — this deployment
  registers `http://127.0.0.1:8747/callback` and `http://localhost:8747/callback`

Store the resulting client id and secret outside the repository. An idempotent
example script for Keycloak lives beside the deployment, not in this repo
(`C:/ProgramData/pingen-mcp/provision_idp_client.py`), because it reads that
stack's admin credentials.

### Consumer configuration

```json
{
  "mcpServers": {
    "pingen": {
      "url": "https://pingen-mcp.datawyse.ai/mcp",
      "authorization": {
        "client_id": "<from your IdP client>",
        "token_endpoint": "<identity layer token endpoint>"
      }
    }
  }
}
```

Clients that support OAuth discovery need no manual wiring: the `401`
challenge → RFC 9728 metadata → RFC 8414 authorization-server metadata chain
leads to the token endpoint automatically.

### Verifying a deployment

```bash
python scripts/verify_public_deploy.py           # c1–c4, restarts Traefik
python scripts/verify_public_deploy.py --json    # machine-readable
python scripts/verify_public_deploy.py --skip-restart
```

Exit code 0 only when every executed check passed; a check that could not run
(for example, missing consumer credentials) reports `skip` and does **not**
count as a pass.

## Tools

Naming rule: the spec's `operationId` with `.`/`-` replaced by `_` (e.g. `letters.create` → `letters_create`). Every tool mirrors exactly one documented operation — the test suite re-derives the expected list from `reference/openapi.json` and fails on any drift.

<details>
<summary>Full tool inventory (49)</summary>

**Letters (14):** `letters_list`, `letters_create`, `letters_show`, `letters_delete`, `letters_send`, `letters_cancel`, `letters_file`, `letters_price_calculator`, `letters_events`, `letters_events_image`, `organisations_letters_events_delivered`, `organisations_letters_events_issues`, `organisations_letters_events_sent`, `organisations_letters_events_undeliverable`

**Batches (9):** `batches_list`, `batches_create`, `batches_show`, `batches_edit`, `batches_delete`, `batches_send`, `batches_cancel`, `batches_events`, `organisations_batches_statistics_details`

**eBills (9):** `deliveries_ebills_list`, `deliveries_ebills_create`, `deliveries_ebills_show`, `deliveries_ebills_delete`, `deliveries_ebills_send`, `deliveries_ebills_cancel`, `deliveries_ebills_file`, `deliveries_ebills_events`, `deliveries_ebills_events_image`

**Emails (8):** `deliveries_emails_list`, `deliveries_emails_create`, `deliveries_emails_show`, `deliveries_emails_delete`, `deliveries_emails_cancel`, `deliveries_emails_file`, `deliveries_emails_events`, `deliveries_emails_events_image`

**Webhooks (4):** `webhooks_index`, `webhooks_create`, `webhooks_show`, `webhooks_destroy`

**Directory (4):** `users_show`, `user_associations_list`, `organisations_index`, `organisations_show`

**Files (1):** `files_file_upload`

</details>

### Conventions

- **Pagination** — list tools take optional `page_number` / `page_limit` (mapped to the documented `page[number]` / `page[limit]`, default 20, max 100) plus an optional `query` mapping passed through verbatim for spec-defined keys (`sort`, `filter`, `include`, `fields[...]`, `q`).
- **Pass-through** — tools return the JSON:API document as parsed JSON, unmodified (`data` / `attributes` / `relationships` intact).
- **File & image endpoints** — these answer `302` to the actual binary; tools return `{"redirect_url": ..., "status_code": 302}` so the caller fetches the file directly. The server never proxies file contents.
- **Errors** — non-2xx responses raise an error containing the HTTP status, a summary of the JSON:API error payload and the `X-Request-Id` header (always quote it in support requests).

## Incoming webhooks

Pingen POSTs these payload shapes to a URL you register with `webhooks_create` — they are **not** MCP tools:

| `data.type` | Meaning |
| --- | --- |
| `webhook_delivered` | deliverable (letter/email/eBill) delivered |
| `webhook_sent` | deliverable dispatched / sent |
| `webhook_issues` | issue with a deliverable |
| `webhook_undeliverable` | deliverable undeliverable |
| `webhook_channel_subscriptions` | recipient subscription change for a channel |

## Development

```bash
# per-domain operation slices of the vendored spec (keeps context bounded)
python scripts/extract_ops.py --list
python scripts/extract_ops.py --domain letters

# unit tests (mocked HTTP only)
python -m pytest

# LIVE smoke test - staging by default, read-only, opt-in; production needs
# an explicit --environment production flag
python scripts/staging_smoke.py
```

## Reference material

- `reference/openapi.json` — the official Pingen OpenAPI 3.0 specification (downloaded from `https://api.pingen.com/documentation/swagger-docs`), vendored so builds are reproducible.
- Live docs: <https://api.pingen.com/documentation>

## Licence

MIT — see [LICENSE](LICENSE).

Pingen API and the Pingen name are trademarks of Pingen GmbH; this is an unofficial community integration.
