# server

## ADDED Requirements

### Requirement: Installable FastMCP server

The repository SHALL ship an installable Python package that exposes a FastMCP application over stdio with a documented entry point; a fresh clone that follows the README SHALL install the package, start the server and retrieve its tool list.

#### Scenario: fresh clone start

- **WHEN** a user installs the package from a fresh clone following the README and runs the documented entry point
- **THEN** the MCP server starts and the registered tool list is retrievable by an MCP client

### Requirement: JSON:API client

All resource-API calls SHALL go through a single httpx-based JSON:API client that sends `Authorization: Bearer <access_token>`, targets the configured API base URL, accepts `application/vnd.api+json`, and returns response bodies as parsed JSON without transformation.

#### Scenario: bearer header injected

- **WHEN** any tool invokes the Pingen resource API
- **THEN** the request carries the current access token as a bearer authorization header

#### Scenario: response passed through unchanged

- **WHEN** the API returns a JSON:API document
- **THEN** the tool result is that document as parsed JSON, with `data`, `attributes` and `relationships` intact

#### Scenario: error surfaces status and request id

- **WHEN** the API answers with a non-2xx status
- **THEN** the tool raises an error containing the HTTP status, a summary of the JSON:API error payload, and the `X-Request-Id` response header when present

### Requirement: Environment configuration

Configuration SHALL be environment-driven: `PINGEN_ENVIRONMENT=production` selects `https://api.pingen.com` with `https://identity.pingen.com`, `PINGEN_ENVIRONMENT=staging` selects `https://api-staging.pingen.com` with `https://identity-staging.pingen.com`, and `PINGEN_API_BASE_URL`/`PINGEN_IDENTITY_BASE_URL` override either base (used by tests); an unsupported environment SHALL fail fast.

#### Scenario: staging selected

- **WHEN** `PINGEN_ENVIRONMENT=staging`
- **THEN** resource calls target `https://api-staging.pingen.com` and token calls target `https://identity-staging.pingen.com`

#### Scenario: production is the default

- **WHEN** `PINGEN_ENVIRONMENT` is unset
- **THEN** the server targets the production hosts

#### Scenario: base override used in tests

- **WHEN** `PINGEN_API_BASE_URL` is set
- **THEN** resource calls target the override instead of the environment default

### Requirement: Tool registration

Every domain module's tools SHALL be registered on the single FastMCP application at import time, and the test suite SHALL contain an inventory test that re-derives the expected tool set from `reference/openapi.json` and asserts equality with the registered tool set.

#### Scenario: inventory matches vendored spec

- **WHEN** the test suite runs the inventory test
- **THEN** the set of registered tool names equals the set derived from the client-callable operations of `reference/openapi.json`

#### Scenario: webhook payload examples excluded

- **WHEN** the inventory derives expected tools from the spec
- **THEN** operations under the `misc.webhooks` tag (incoming-payload examples) are excluded from the expected set

### Requirement: Uniform collection arguments

Every collection (list) tool SHALL accept optional `page_number` and `page_limit` arguments, SHALL map them to the `page[number]` and `page[limit]` query parameters, and SHALL accept an optional `query` mapping that is passed through verbatim as extra query parameters.

#### Scenario: pagination mapped

- **WHEN** a list tool is called with `page_number=2` and `page_limit=50`
- **THEN** the upstream request carries `page[number]=2` and `page[limit]=50`

#### Scenario: query pass-through

- **WHEN** a list tool is called with `query={"filter[status]": "created"}`
- **THEN** the upstream request carries the `filter[status]=created` query parameter unchanged
