# public-deployment

## ADDED Requirements

### Requirement: Public streamable-HTTP endpoint

The server SHALL expose the MCP streamable-HTTP transport at `/mcp` on a
non-published interface when HTTP mode is configured (via `PINGEN_MCP_PUBLIC_URL`
and `PINGEN_MCP_PORT`), SHALL keep the stdio entry point unchanged when those
variables are unset, and SHALL be reachable publicly only through the reverse
proxy's `Host(pingen-mcp.datawyse.ai)` router — the deployment SHALL NOT publish
a container port or listen on a routable interface.

#### Scenario: HTTP mode serves the MCP endpoint

- **WHEN** the server is started with `PINGEN_MCP_PUBLIC_URL` and
  `PINGEN_MCP_PORT` set
- **THEN** `POST /mcp` answers the MCP streamable-HTTP handshake on the
  configured loopback/non-published bind, and no port mapping exposes it
  directly from the host or LAN

#### Scenario: stdio mode unchanged

- **WHEN** the server is started without HTTP-mode configuration
- **THEN** it runs over stdio exactly as delivered by `add-pingen-mcp-server`,
  and no authentication provider is constructed

### Requirement: Fail-closed caller authentication

With HTTP mode configured, the server SHALL require a Bearer access token
issued by the configured identity layer on every request to `/mcp` and to every
tool invocation, SHALL answer missing, malformed, expired, wrong-issuer or
wrong-audience tokens with HTTP 401 carrying a `WWW-Authenticate` header that
names the protected-resource metadata URL, and SHALL offer no anonymous route
to any tool.

#### Scenario: anonymous request is challenged

- **WHEN** an unauthenticated client sends `POST https://pingen-mcp.datawyse.ai/mcp`
  over trusted TLS
- **THEN** the response is HTTP 401 with
  `WWW-Authenticate: Bearer … resource_metadata="…"`, never 502, 404 or a
  completed handshake

#### Scenario: token from another issuer is rejected

- **WHEN** a well-formed, unexpired JWT signed by a key in the JWKS but with a
  different `iss` than the configured identity layer is presented
- **THEN** the request is refused with HTTP 401 and no tool result is produced

#### Scenario: token minted for another audience is rejected

- **WHEN** a token whose `aud`/`azp` does not identify this resource or its
  pre-registered client is presented
- **THEN** the request is refused with HTTP 401

### Requirement: OAuth discovery metadata

The server SHALL serve RFC 9728 protected-resource metadata at
`/.well-known/oauth-protected-resource` (and the `/mcp`-suffixed variant) that
names the configured identity layer in `authorization_servers`, so a standard
MCP client can locate the RFC 8414 authorization-server metadata without any
server-specific configuration.

#### Scenario: client discovers the authorization server

- **WHEN** an MCP client fetches the protected-resource metadata from the
  public origin root
- **THEN** the document's `authorization_servers` contains the configured
  identity layer's issuer URL, and the authorization server's own discovery
  document resolves with a `token_endpoint`

### Requirement: Host allowlisting

The server SHALL reject requests whose `Host` header is neither the configured
public hostname nor loopback, answering HTTP 421, and SHALL NOT disable
DNS-rebinding protection wholesale to accommodate the proxy.

#### Scenario: spoofed Host refused

- **WHEN** a request reaches the backend with an unrecognised `Host` value
- **THEN** it is refused with HTTP 421 before authentication is evaluated

### Requirement: Durable public routing

The deployment SHALL place a `Host(pingen-mcp.datawyse.ai)` router on the
`websecure` entrypoint with its own Let's Encrypt certificate, SHALL add the
hostname to the DDNS Cloudflare sync targets so it follows the home IP, and
SHALL keep serving after `docker restart traefik`.

#### Scenario: route survives a proxy restart

- **WHEN** `docker restart traefik` completes and the file provider reloads
- **THEN** an unauthenticated request to `https://pingen-mcp.datawyse.ai/mcp`
  still returns the 401 challenge, and `openssl s_client` reports a certificate
  whose SAN names `pingen-mcp.datawyse.ai`

#### Scenario: hostname follows the WAN IP

- **WHEN** the DDNS sync runs after a home IP change
- **THEN** the `pingen-mcp.datawyse.ai` A record is updated to the new address,
  proven by `--discover` output equal to the current public IP

### Requirement: Verification harness

The change SHALL ship a script that performs the anonymous challenge, the
authenticated acceptance, the real-client `tools/list` over the public URL and
the durability checks, and SHALL report the observed tool count and HTTP status
codes so the card's criteria can be closed from its output.

#### Scenario: harness reports the tool count

- **WHEN** the harness runs against the deployed URL with valid credentials
- **THEN** it prints the HTTP status of the anonymous request, the status of the
  authenticated request, and the number of tools listed by the MCP client,
  which SHALL be 49
