# Design — deploy-pingen-mcp-http

## Context

- **Introducing change:** `add-pingen-mcp-server` (PINGEN-01), commits
  `939ac0b` → `0fee3b8` → `ab97475` → `c31c7d4` → `085433c` on `main`. It built
  the 49-tool FastMCP server with both outbound Pingen grants, stdio only.
- **Card:** PINGEN-02 (Arthur, 2026-11-10 17:01 BST), which asks for a public
  streamable-HTTP deployment with the identity layer as auth, and explicitly
  requires the A/B/C-vs-D choice to be made *in this design* with justification.
- **Mid-flight premise break (2026-11-10 17:35 BST):** while this change was
  being authored, the estate retired Authentik — files moved to
  `DataWyse/_retired/authentik-20261110/`, containers removed, Traefik's `auth`
  router and `auth.datawyse.ai` now serve Keycloak realm `master` (issuer
  `https://auth.datawyse.ai/realms/master`, live). The card body and criterion
  c2 still name Authentik as a hard requirement; an `input_required` ask is on
  the card for Arthur to amend it. **This design therefore parameterises the
  identity layer** (issuer, JWKS URI and audience arrive by configuration, not
  by hardcoding a product), so the deploy is identical whichever way that ask
  is answered; only the provisioning step and three config values differ.
- **Spec ground:** MCP 2025-06-18 authorization — DCR is SHOULD (a non-DCR
  authorization server must offer another way to obtain a client ID, which is
  path 1 below); the resource server MUST serve RFC 9728 metadata, MUST put the
  metadata URL in `WWW-Authenticate` on 401, and MUST validate that the token's
  audience is itself (RFC 8707).

## Goals / Non-Goals

**Goals**

1. `https://pingen-mcp.datawyse.ai/mcp` speaks streamable HTTP and is reachable
   from the internet over trusted TLS.
2. No request reaches a tool without a valid identity-layer token (fail closed).
3. A standard MCP client discovers the authorization server from the resource
   metadata and completes the flow without custom glue.
4. Route, cert and DNS survive `docker restart traefik` and a WAN IP change.

**Non-Goals**

- No browser-facing UI or docs page on this host (no forwardAuth surface is
  needed; if one is added later it goes behind the identity layer's interactive
  login, per card option C).
- No change to the stdio entry point, the outbound Pingen grants, or any other
  Traefik route.
- No dynamic client registration surface in this change (see D1).

## Decisions

### D1 — Auth design: option A (identity-layer OIDC + pre-registered client), not D

Arthur's revised options were D (native DCR), A (pre-registered clients), B
(thin custom AS, now unnecessary), C (forwardAuth, browser-paths only). REFLEX
was near-undecided on the original list (D 0.389 / A 0.322 / B 0.290,
confidence 0.0068) and on the revised pair preferred D (0.729 vs 0.271,
confidence 0.157, residual-risk score ≈ 1.95 = low-moderate;
request `01JREFLEX668707D3D6213E1F`) — advisory only.

**Decision: A.** The card's decision test decides it: D only wins if an
arbitrary MCP client can hold the dcr-scoped bootstrap token *safely*.

- One shared bootstrap token = a fleet-wide standing credential that can create
  unlimited client objects with no RFC 7592 management endpoint and no auto
  expiry (both confirmed in the Authentik 2026.8 DCR docs; Keycloak's DCR is
  likewise gated by client policy but equally unmanageable once issued).
- Minting the token per client instead is a per-client secret — which per the
  test *is* A with extra steps.
- D buys no simpler client experience: clients run `authorization_code` + PKCE
  either way; DCR only removes our manual provisioning step, which `provision`
  automation already makes cheap.
- On Authentik, D additionally fragmented issuers (one provider = one issuer per
  registration), forcing the resource server to trust a growing issuer set.
  Keycloak's realm-wide issuer removes *that* cost, but not the token one, so
  the pick is unchanged.

Consequence: no registration endpoint is exposed; each consumer client is
created explicitly by the idempotent provisioning script and its credentials are
stored outside the repository. If a future consumer can only self-register,
revisit D with a dedicated registration client and a cleanup job — that is an
amendment, not a silent extension of this change.

### D2 — Authentication lives in the backend, not in a Traefik middleware

Option: validate the Bearer at Traefik with a forwardAuth gate (the `/fpl`
pattern, `fpl-gate` → `inject-fpl-auth`).

**Decision: validate inside the FastMCP app** via `RemoteAuthProvider` +
`JWTVerifier(jwks_uri, issuer, audience)`.

- Trade-off: a Traefik gate keeps apps auth-agnostic, but the MCP specification
  requires the *resource server* to answer 401 with a `WWW-Authenticate` pointing
  at RFC 9728 metadata and to serve that metadata itself — a gate would have to
  re-implement both, and the discovery paths would need a bypass router anyway
  (the `fpl-oauth` lesson). FastMCP ships all of it (`RequireAuthMiddleware`,
  `create_protected_resource_routes`), so in-backend validation is strictly less
  code and one less moving part.
- Fail-closed: with `auth=` set, FastMCP rejects every request lacking a valid
  token before any tool is reachable; there is no anonymous route to disable.

### D3 — Backend runs as a container with no published ports

Option: native Windows process on `127.0.0.1` (card's literal wording) vs
Docker.

**Decision: Docker, no `ports:` mapping, joined to the identity layer's Docker
network.**

- Trade-off: a native process is marginally simpler to start, but needs a
  logon-time autostart mechanism to survive reboots and inherits host quirks
  (this box's `PYTHONPATH` contaminates venv imports — already hit once during
  this task). The container restarts with the engine, has no host port at all
  (stronger than loopback: only Traefik on the shared network can reach it), and
  reaches the identity layer's JWKS over internal DNS instead of depending on
  hairpin NAT to `auth.datawyse.ai`.
- The container is the only thing that talks to the Pingen API; it holds the
  Pingen credentials by read-only env-file mount from
  `C:/ProgramData/pingen-mcp/`, never in the image or the repo.

### D4 — One confidential client, `authorization_code` + `refresh_token` + `client_credentials`

- Confidential (client-secret) because our consumers are our own agents and
  scripts, which can hold a secret; a public/PKCE-only client would be added as
  a second identity-layer client if a browser-hosted consumer appears.
- `client_credentials` is included so headless consumers (Hermes profiles) can
  authenticate without a browser; the interactive grant remains the
  MCP-canonical path and is what the verification harness exercises first.
- The client's redirect URI is a **fixed** loopback callback
  (`http://127.0.0.1:8747/callback`), documented for consumers: the identity
  layer validates redirect URIs exactly, so random client ports cannot be
  pre-registered.

### D5 — Token validation set: signature (JWKS) + issuer + expiry + audience

- `JWTVerifier` with the identity layer's JWKS URI, expected issuer, and the
  audience the resource advertises (RFC 8707 canonical resource URL
  `https://pingen-mcp.datawyse.ai/mcp`, falling back to the client_id if the
  identity layer cannot bind a resource audience — pinned from the first minted
  token's real claims during implementation, never assumed).
- `required_scopes` left unset: authorisation is client-level here, and a scope
  mismatch would fail closed on legitimate tokens without adding a security
  boundary (the issuer check already scopes tokens to *this* identity-layer
  client).

### D6 — Host allowlisting instead of disabling rebinding protection

The app binds to a non-published container interface, but requests arrive with
`Host: pingen-mcp.datawyse.ai`. Rather than switching FastMCP's DNS-rebinding
protection off, the run configuration passes `allowed_hosts` for the public host
(+ loopback for local probes), so a spoofed Host is refused with 421 before the
auth layer is exercised.

### D7 — No rate-limit middleware on this route

`ratelimit-edge` is deliberately omitted: Traefik's published-port source
rewriting (reverse-proxy skill pitfall) collapses every external caller into one
shared bucket, so a legitimate MCP session could be throttled by someone else's
traffic. The backend validates tokens cheaply on every request; if flood
protection is later needed it belongs in the backend keyed on a forwarded
header, not in Traefik.

### D8 — Verification is a script in the repo, evidence on the card

`scripts/verify_public_deploy.py` performs the four card checks (c1–c4) against
the live URL and prints machine-readable results; its output is pasted into the
PINGEN-02 comments as the closeout evidence, before/after the Traefik restart.

## Risks / Trade-offs

- **Card/criteria still name Authentik** while the estate now runs Keycloak.
  Mitigated: config-parameterised design + `input_required` ask on the card; no
  criterion is claimed closed until Arthur amends c2.
- **Fixed loopback redirect port** limits concurrent interactive authorizations
  from one machine to a single consumer at a time. Accepted: our consumers are
  few and take turns; a second client with a different port is a provisioning
  line, not a code change.
- **Single identity-layer client secret** is a shared credential across our
  headless consumers. Accepted for first-party use; rotation is a re-run of the
  provisioning script plus an env-file update.
- **Home IP dependency.** The hostname follows the WAN IP through the DDNS sync
  targets; a missed sync leaves a dead record. Mitigated by the same
  `--discover` proof every other `datawyse.ai` host uses.
