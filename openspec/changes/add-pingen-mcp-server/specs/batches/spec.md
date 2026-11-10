# batches

## ADDED Requirements

### Requirement: Batch lifecycle tools

The server SHALL expose one tool per client-callable operation of the `batches.general` tag of `reference/openapi.json`: list, create, get, edit, delete, cancel, send and statistics, each calling exactly the documented method and path under `/organisations/{organisationId}/batches`.

#### Scenario: create and edit a batch

- **WHEN** the batch create tool is called with a payload, or the edit tool with a batch id and patch payload
- **THEN** the server issues `POST /organisations/{organisationId}/batches` or `PATCH /organisations/{organisationId}/batches/{batchId}` as documented

#### Scenario: send and cancel a batch

- **WHEN** the batch send tool or cancel tool is called
- **THEN** the server issues `PATCH …/batches/{batchId}/send` or `PATCH …/batches/{batchId}/cancel` exactly as documented in the vendored spec

#### Scenario: batch statistics fetched

- **WHEN** the statistics tool is called with organisation and batch ids
- **THEN** the server issues `GET …/batches/{batchId}/statistics` and returns the response unchanged

### Requirement: Batch event tools

The server SHALL expose a batch events tool for the `batches.events` tag that issues `GET /organisations/{organisationId}/batches/{batchId}/events`.

#### Scenario: batch events listed

- **WHEN** the batch events tool is called
- **THEN** the server issues the documented events request with pagination arguments mapped to `page[number]`/`page[limit]`

### Requirement: Batch tools verified against the vendored spec

The batch domain SHALL be covered by unit tests that mock HTTP and assert each tool's method, path and payload shape against the 9 batch operations of `reference/openapi.json`; no batch endpoint may be invented.

#### Scenario: every batch operation has a test

- **WHEN** the batch test module runs
- **THEN** each of the 9 batch operations in the vendored spec is exercised by at least one mocked request assertion
