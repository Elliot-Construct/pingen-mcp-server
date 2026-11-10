# directory

## ADDED Requirements

### Requirement: User and association tools

The server SHALL expose read tools for the `user.general` and `user.associations` tags of `reference/openapi.json`: authenticated-user details (`GET /user`) and the associations collection (`GET /user/associations`), each calling exactly the documented method and path.

#### Scenario: authenticated user fetched

- **WHEN** the user-details tool is called
- **THEN** the server issues `GET /user` with the current bearer token and returns the JSON:API document unchanged

#### Scenario: associations listed with pagination

- **WHEN** the associations tool is called with pagination arguments
- **THEN** the server issues `GET /user/associations` carrying `page[number]`/`page[limit]` when supplied

### Requirement: Organisation tools

The server SHALL expose read tools for the `organisations.general` tag: organisation collection (`GET /organisations`) and organisation details (`GET /organisations/{organisationId}`).

#### Scenario: organisation list and details

- **WHEN** the organisation list tool or details tool is called
- **THEN** the server issues `GET /organisations` or `GET /organisations/{organisationId}` as documented in the vendored spec

### Requirement: Directory tools verified against the vendored spec

The directory domain SHALL be covered by unit tests that mock HTTP and assert each tool's method and path against the 4 directory operations of `reference/openapi.json`.

#### Scenario: every directory operation has a test

- **WHEN** the directory test module runs
- **THEN** each of the 4 user/associations/organisations operations is exercised by at least one mocked request assertion
