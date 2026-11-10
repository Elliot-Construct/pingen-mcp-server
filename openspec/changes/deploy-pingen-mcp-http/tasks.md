# Tasks — deploy-pingen-mcp-http

## 1. Plan (this change)

- [x] 1.1 proposal + design + capability delta authored and committed BEFORE the
      first implementation commit (sequence is part of the evidence)
- [x] 1.2 `openspec change validate deploy-pingen-mcp-http --json` → `valid: true`

## 2. Backend — streamable HTTP + resource-server auth

- [x] 2.1 Config keys for HTTP mode and token validation
      (`PINGEN_MCP_PUBLIC_URL`, `PINGEN_MCP_AUTH_ISSUER`,
      `PINGEN_MCP_AUTH_JWKS_URI`, `PINGEN_MCP_AUTH_AUDIENCE`,
      `PINGEN_MCP_PORT`) — stdio behaviour unchanged when unset
- [x] 2.2 `build_server()` gains the `RemoteAuthProvider` + `JWTVerifier` wiring
      when HTTP mode is configured; `main()` gains the HTTP run path with
      `allowed_hosts` for the public host
- [x] 2.3 Unit tests: unauthenticated request → 401 with
      `WWW-Authenticate … resource_metadata=`; well-known protected-resource
      metadata served and naming the configured authorization server; a
      signed-by-JWKS token with wrong issuer / wrong audience / expired → 401;
      valid token → handshake proceeds; `tools/list` still 49
- [x] 2.4 Full existing suite still green (no stdio regression)

## 3. Packaging — container with no published ports

- [x] 3.1 `Dockerfile` (python slim, `pip install .`, non-root, no EXPOSE)
- [x] 3.2 Compose service under `C:/ProgramData/pingen-mcp/`: env from
      `credentials.env` + IdP config, `restart: unless-stopped`, no `ports:`,
      joined to the identity layer's Docker network
- [x] 3.3 Container verified unreachable except through Traefik (no published
      port; direct socket refused)

## 4. Identity layer — pre-registered client (option A)

- [x] 4.1 Idempotent provisioning script for the OIDC client (grants, fixed
      loopback redirect URI, audience), credentials written outside the repo
- [x] 4.2 First minted token's real claims (`iss`, `aud`, `azp`, `exp`) captured
      and pinned into the verifier config (D5 — measured, not assumed)
- [x] 4.3 Client-credentials token minted for headless consumers

## 5. Public routing — DNS, TLS, Traefik

- [x] 5.1 Cloudflare A record `pingen-mcp.datawyse.ai` → current home IP,
      DNS-only; resolves to the same address before cert issuance
- [x] 5.2 Host added to `ddns-cloudflare-sync.json` targets (`name` +
      `record_name`), `--discover` proves Cloudflare holds it
- [x] 5.3 Traefik `Host()` router + service (backup routes.yml BEFORE editing;
      explicit priority; no auth-gateways middleware — auth is in the backend),
      `docker restart traefik`, `docker logs traefik` clean
- [x] 5.4 LE cert for the new host named by `openssl s_client`

## 6. Verification (card criteria c1–c4)

- [x] 6.1 c1: unauthenticated `curl` to `https://pingen-mcp.datawyse.ai/mcp`
      over trusted TLS → MCP 401 challenge (never 502/404/000)
- [x] 6.2 c2: anonymous rejected AND identity-layer token accepted
      (scripted login or minted token), evidenced by the harness
- [x] 6.3 c3: real MCP client completes the flow and `tools/list` over the
      public URL returns 49 tools
- [x] 6.4 c4: routes.yml carries the router with the auth chain, cert names the
      new host, host in DDNS targets, `docker restart traefik` leaves the route
      serving
- [ ] 6.5 Evidence (before/after command output) posted to PINGEN-02 comments

## 7. Closeout

- [x] 7.1 README deployment section (consumer config: URL, client credentials
      location, fixed redirect port)
- [ ] 7.2 `openspec validate --all --json` green; commit + push; card updated
      (criterion status left to Arthur for c2's amended wording)
