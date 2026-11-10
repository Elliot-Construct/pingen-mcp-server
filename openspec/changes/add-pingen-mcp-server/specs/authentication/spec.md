# authentication

## ADDED Requirements

### Requirement: Client-credentials grant

The server SHALL obtain machine access tokens by POSTing `grant_type=client_credentials` with `client_id` and `client_secret` (form-encoded) to `{identity_base_url}/auth/access-tokens` when the configured grant is `client_credentials`, and SHALL reuse the cached `access_token` until `expires_in` minus a 60-second skew before requesting a new one.

#### Scenario: token fetched and cached

- **WHEN** a tool first needs an API token in client-credentials mode
- **THEN** the server sends the form-encoded grant request to the configured identity base URL and caches the returned `access_token` together with its expiry

#### Scenario: near-expiry token re-fetched

- **WHEN** the cached token is within 60 seconds of its expiry
- **THEN** the next tool call obtains a fresh token before issuing the resource-API request

#### Scenario: no refresh token in this grant

- **WHEN** the client-credentials token response is stored
- **THEN** no `refresh_token` is required or persisted, because Pingen issues access tokens only for this grant

### Requirement: Authorization-code grant

The server SHALL support delegated access via the authorization-code grant through the auth module's Python API (not MCP tools, since completing the browser redirect is an operator action): `build_authorize_url` SHALL build `{identity_base_url}/auth/authorize` with `response_type=code`, a random `state`, a 43-character `code_verifier`, `client_id`, `redirect_uri` and optional `scope`; `exchange_code` SHALL POST `grant_type=authorization_code` with `client_id`, `client_secret`, `redirect_uri`, `code` and `code_verifier` to `/auth/access-tokens` and store the returned `access_token` and `refresh_token`.

#### Scenario: authorize URL built

- **WHEN** an operator runs the authorize-URL builder with a generated state and code_verifier
- **THEN** the returned URL targets the configured identity host and carries `response_type=code`, `state`, `code_challenge`, `client_id` and `redirect_uri`

#### Scenario: state verified on exchange

- **WHEN** the code exchange is invoked with a `state` that does not match the value generated for the authorize URL
- **THEN** the exchange is refused with an error naming the state mismatch, and no token request is sent

#### Scenario: code exchanged for tokens

- **WHEN** the code exchange is invoked with the valid `code` and `code_verifier`
- **THEN** the server POSTs the form-encoded `authorization_code` grant and persists the returned `access_token` and `refresh_token`

### Requirement: Refresh-token rotation

The server SHALL refresh delegated tokens by POSTing `grant_type=refresh_token` with the stored refresh token, and SHALL persist the NEW `refresh_token` returned by the response before the next request, because Pingen revokes the used refresh token on every use.

#### Scenario: rotation persisted

- **WHEN** a refresh completes and the response contains a new `refresh_token`
- **THEN** the token store is rewritten with the new refresh token, replacing the consumed one

#### Scenario: expired access token auto-refreshed

- **WHEN** a tool call needs an API token and the stored authorization-code access token is expired
- **THEN** the server performs the refresh grant transparently and retries with the new access token

### Requirement: Grant selection by configuration

The active grant SHALL be selected by the `PINGEN_GRANT_TYPE` configuration variable, SHALL default to `client_credentials` when unset, and SHALL fail fast at startup with an error naming the variable and its allowed values when set to anything else.

#### Scenario: default grant

- **WHEN** `PINGEN_GRANT_TYPE` is unset
- **THEN** the server runs in client-credentials mode

#### Scenario: invalid grant rejected

- **WHEN** `PINGEN_GRANT_TYPE` holds an unsupported value
- **THEN** startup fails with a configuration error naming `PINGEN_GRANT_TYPE` and the allowed values

### Requirement: Token and credential storage outside the repository

Access tokens, refresh tokens and client secrets SHALL live only in process memory or in a file whose path (`PINGEN_TOKEN_FILE`) resolves outside the repository tree, defaulting to the platform user config directory; no credentials file, token file or secret value SHALL be committed to the repository.

#### Scenario: default token path outside repo

- **WHEN** `PINGEN_TOKEN_FILE` is unset
- **THEN** the token store resolves to a path under the user's config directory, never under the repository tree

#### Scenario: credentials loaded from external env file

- **WHEN** `PINGEN_ENV_FILE` points at an env file outside the repository (dev host: `C:/ProgramData/pingen-mcp/credentials.env`)
- **THEN** client id and secret are read from that file at runtime and no value from it appears anywhere in the repository
