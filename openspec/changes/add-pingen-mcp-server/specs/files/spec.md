# files

## ADDED Requirements

### Requirement: File upload registration tool

The server SHALL expose a file upload registration tool for the `misc.files` tag of `reference/openapi.json` that issues `GET /file-upload` with the documented parameters and returns the response unchanged, so callers can obtain upload details and upload directly to the returned destination.

#### Scenario: upload details fetched

- **WHEN** the file upload registration tool is called
- **THEN** the server issues `GET /file-upload` with the current bearer token and returns the JSON:API response as parsed JSON

### Requirement: No binary upload proxying

The server SHALL NOT proxy, stream or store file contents; only the registration metadata returned by `GET /file-upload` is exposed as a tool result.

#### Scenario: file bytes never pass through the server

- **WHEN** any files-domain tool completes
- **THEN** the tool result contains only metadata from the API response, with no file content handled by the server

### Requirement: Files tool verified against the vendored spec

The files domain SHALL be covered by a unit test that mocks HTTP and asserts the tool's method and path against the single `misc.files` operation of `reference/openapi.json`.

#### Scenario: the file operation has a test

- **WHEN** the files test module runs
- **THEN** `GET /file-upload` is exercised by at least one mocked request assertion
