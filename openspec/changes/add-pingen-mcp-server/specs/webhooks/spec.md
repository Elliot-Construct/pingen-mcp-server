# webhooks

## ADDED Requirements

### Requirement: Webhook registration tools

The server SHALL expose one tool per client-callable operation of the `organisations.management.webhooks` tag of `reference/openapi.json`: list, create, get and delete, each calling exactly the documented method and path under `/organisations/{organisationId}/webhooks`.

#### Scenario: create a webhook registration

- **WHEN** the webhook create tool is called with an organisation id and payload
- **THEN** the server issues `POST /organisations/{organisationId}/webhooks` with that payload as the JSON body

#### Scenario: list and delete webhooks

- **WHEN** the list tool or delete tool is called
- **THEN** the server issues `GET …/webhooks` or `DELETE …/webhooks/{webhookId}` as documented in the vendored spec

### Requirement: Incoming webhook payloads documented, not exposed as tools

The five `misc.webhooks` operations of the vendored spec describe payloads Pingen POSTs to a customer URL; the server SHALL document their payload shapes in the README's webhook section and SHALL NOT register MCP tools for them.

#### Scenario: payload examples excluded from the tool surface

- **WHEN** tools are registered at startup
- **THEN** no tool exists for any `/your-webhook-url-for-*` path in the vendored spec

#### Scenario: payload shapes documented

- **WHEN** a user reads the README webhook section
- **THEN** each of the five incoming payload types (delivered, dispatched, issues, undeliverable, channel subscriptions) is described with its `data.type` value

### Requirement: Webhook tools verified against the vendored spec

The webhooks domain SHALL be covered by unit tests that mock HTTP and assert each tool's method and path against the 4 registration operations of `reference/openapi.json`.

#### Scenario: every webhook registration operation has a test

- **WHEN** the webhook test module runs
- **THEN** each of the 4 registration operations is exercised by at least one mocked request assertion
