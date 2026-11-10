# Proposal — deploy-pingen-mcp-http

## Why

PINGEN-01 delivered a complete Pingen MCP server (49 tools) that speaks **stdio
only**, so it can only run as a local child process of a configured client.
Registry card PINGEN-02 asks for a **public HTTPS streamable-HTTP deployment**
reachable by any MCP client over the internet, with the estate's identity layer
enforcing authentication and no anonymous path to any tool.

## What Changes

- **HTTP transport entry point.** The FastMCP app gains a streamable-HTTP run
  mode bound to a non-published socket (Docker container with no `ports:`
  mapping, reached only through Traefik). The existing stdio entry point and its
  behaviour are untouched.
- **Resource-server authentication.** When HTTP mode is configured, the app is
  constructed with a `RemoteAuthProvider` + `JWTVerifier` (fastmcp 4.1.7):
  Bearer tokens are validated against the identity layer's JWKS with issuer and
  audience checks, RFC 9728 protected-resource metadata is served, and every
  unauthenticated request gets a fail-closed `401` carrying the
  `WWW-Authenticate` challenge the MCP specification requires.
- **Identity-layer client provisioning.** One pre-registered confidential OIDC
  client for our own MCP consumers, created idempotently against the estate
  identity layer; its credentials live outside the repository.
- **Public routing.** New `pingen-mcp.datawyse.ai` hostname: Cloudflare A record
  (DNS-only, added to the DDNS sync targets) + one Traefik `Host()` router with
  its own LE cert.
- **Verification harness.** A scripted proof covering the four card criteria:
  anonymous 401, identity-layer token accepted, a real MCP client listing 49
  tools over the public URL, and route/cert/DDNS durability across
  `docker restart traefik`.

## Capabilities

### New Capabilities

- `public-deployment` — how the server is exposed publicly, how it authenticates
  callers at the transport edge, and how the routing/DNS/TLS wiring is proven
  durable.

### Modified Capabilities

- None. `authentication` (PINGEN-01) governs the server's *outbound* Pingen API
  grants and is untouched; this change only adds *inbound* caller
  authentication at the MCP transport layer.

## Impact

- Repository: `src/pingen_mcp_server/` (new `http_serve` wiring inside
  `server.py` + config keys), `Dockerfile`, `scripts/verify_public_deploy.py`,
  README deployment section, this OpenSpec change.
- Infrastructure (outside the repo): one Traefik router + service, one Cloudflare
  A record, one DDNS sync target, one identity-layer OIDC client, one Docker
  container with no published ports.
- No changes to other routes or services; no Pingen API writes; no releases.
