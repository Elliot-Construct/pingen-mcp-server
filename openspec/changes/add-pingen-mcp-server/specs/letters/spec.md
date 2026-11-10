# letters

## ADDED Requirements

### Requirement: Letter lifecycle tools

The server SHALL expose one tool per client-callable operation of the `deliveries.letters.general` tag of `reference/openapi.json`: list, create, get, delete, cancel, send, file retrieval and price calculation, each calling exactly the documented method and path (`/organisations/{organisationId}/deliveries/letters…`).

#### Scenario: list letters

- **WHEN** the letter list tool is called with an organisation id
- **THEN** the server issues `GET /organisations/{organisationId}/deliveries/letters` with the pagination arguments mapped to `page[number]`/`page[limit]` and returns the JSON:API collection unchanged

#### Scenario: create and send a letter

- **WHEN** the letter create tool is called with the letter payload
- **THEN** the server issues `POST /organisations/{organisationId}/deliveries/letters` with that payload as the JSON body, and the send tool issues `PATCH /organisations/{organisationId}/deliveries/letters/{letterId}/send` with the letter id path parameter

#### Scenario: cancel and delete a letter

- **WHEN** the cancel tool or the delete tool is called for an existing letter id
- **THEN** the server issues `PATCH …/letters/{letterId}/cancel` or `DELETE …/letters/{letterId}` exactly as documented in the vendored spec

#### Scenario: price calculation

- **WHEN** the price-calculator tool is called with a letter configuration
- **THEN** the server issues `POST /organisations/{organisationId}/deliveries/letters/price-calculator` and returns the pricing response unchanged

### Requirement: Letter file retrieval tool

The server SHALL expose a tool that retrieves a letter's file via `GET /organisations/{organisationId}/deliveries/letters/{letterId}/file` and returns the response body for the caller.

#### Scenario: letter file fetched

- **WHEN** the letter file tool is called with organisation and letter ids
- **THEN** the server issues the documented `GET …/letters/{letterId}/file` request with the current bearer token

### Requirement: Letter event tools

The server SHALL expose event tools for the `deliveries.letters.events` tag: per-letter events (`GET …/letters/{letterId}/events`), event image retrieval (`GET …/letters/{letterId}/events/{letterEventId}/image`), and the four organisation-wide event collections (delivered, issues, sent, undeliverable).

#### Scenario: per-letter events listed

- **WHEN** the letter events tool is called with organisation and letter ids
- **THEN** the server issues `GET /organisations/{organisationId}/deliveries/letters/{letterId}/events`

#### Scenario: organisation-wide issue events listed

- **WHEN** the letter issues-events tool is called with an organisation id
- **THEN** the server issues `GET /organisations/{organisationId}/deliveries/letters/events/issues`

### Requirement: Letter tools verified against the vendored spec

The letter domain SHALL be covered by unit tests that mock HTTP and assert each tool's method, path and payload shape against the operations of `reference/openapi.json`; no letter endpoint may be invented.

#### Scenario: every letter operation has a test

- **WHEN** the letter test module runs
- **THEN** each of the 14 letter operations in the vendored spec is exercised by at least one mocked request assertion
