# channels

## ADDED Requirements

### Requirement: eBill lifecycle tools

The server SHALL expose one tool per client-callable operation of the `deliveries.ebills.general` tag of `reference/openapi.json`: list, create, get, delete, cancel, send and file retrieval, each calling exactly the documented method and path under `/organisations/{organisationId}/deliveries/ebills`.

#### Scenario: create and send an eBill

- **WHEN** the eBill create tool is called with a payload, or the send tool with an eBill id
- **THEN** the server issues `POST …/deliveries/ebills` or `PATCH …/deliveries/ebills/{ebillId}/send` as documented in the vendored spec

#### Scenario: eBill file fetched

- **WHEN** the eBill file tool is called
- **THEN** the server issues `GET …/deliveries/ebills/{ebillId}/file` with the current bearer token

### Requirement: eBill event tools

The server SHALL expose eBill event tools for `deliveries.ebills.events`: per-eBill events and event image retrieval.

#### Scenario: eBill events listed and image fetched

- **WHEN** the eBill events tool or event image tool is called
- **THEN** the server issues `GET …/ebills/{ebillId}/events` or `GET …/ebills/{ebillId}/events/{deliverableEventId}/image` as documented

### Requirement: Email lifecycle tools

The server SHALL expose one tool per client-callable operation of the `deliveries.emails.general` tag of `reference/openapi.json`: list, create, get, delete, cancel and file retrieval, each calling exactly the documented method and path under `/organisations/{organisationId}/deliveries/emails`.

#### Scenario: create an email

- **WHEN** the email create tool is called with a payload
- **THEN** the server issues `POST /organisations/{organisationId}/deliveries/emails` with that payload as the JSON body

#### Scenario: cancel and delete an email

- **WHEN** the cancel or delete tool is called for an email id
- **THEN** the server issues `PATCH …/emails/{emailId}/cancel` or `DELETE …/emails/{emailId}` as documented

### Requirement: Email event tools

The server SHALL expose email event tools for `deliveries.emails.events`: per-email events and event image retrieval.

#### Scenario: email events listed

- **WHEN** the email events tool is called with organisation and email ids
- **THEN** the server issues `GET /organisations/{organisationId}/deliveries/emails/{emailId}/events`

### Requirement: Channel tools verified against the vendored spec

The channels domain SHALL be covered by unit tests that mock HTTP and assert each tool's method, path and payload shape against the 17 channel operations (9 eBill + 8 email) of `reference/openapi.json`; no channel endpoint may be invented.

#### Scenario: every channel operation has a test

- **WHEN** the channel test module runs
- **THEN** each of the 17 eBill and email operations in the vendored spec is exercised by at least one mocked request assertion
