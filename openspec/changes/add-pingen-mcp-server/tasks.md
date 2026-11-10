# Tasks — add-pingen-mcp-server

## 1. Scaffold

- [ ] 1.1 `pyproject.toml` (package `pingen-mcp-server`; deps `fastmcp`, `httpx`; dev `pytest`, `respx`), `src/pingen_mcp_server/` layout, pytest configuration
- [ ] 1.2 `.env.example` with placeholder variable names only (no values)

## 2. Core (built first, frozen as minion interface)

- [ ] 2.1 `config.py` — environment mapping (production/staging hosts), grant selection, `PINGEN_ENV_FILE` loading, token-file path resolution; unit tests
- [ ] 2.2 `auth.py` — client-credentials provider (cache + 60 s skew re-fetch); authorization-code authorize-URL builder, code exchange, refresh with rotation persisted to token file; unit tests (satisfies criterion c2)
- [ ] 2.3 `client.py` — httpx JSON:API client: bearer injection, base URL, `page[number]`/`page[limit]` mapping, query pass-through, error mapping with `X-Request-Id`; unit tests

## 3. Domains (parallel minion sub-agents, one per domain)

- [ ] 3.1 letters — 14 ops (general + events) → `domains/letters.py` + `tests/test_letters.py`
- [ ] 3.2 batches — 9 ops → `domains/batches.py` + `tests/test_batches.py`
- [ ] 3.3 channels — ebills (9) + emails (8) → `domains/channels.py` + `tests/test_channels.py`
- [ ] 3.4 webhooks — 4 org-webhook ops → `domains/webhooks.py` + `tests/test_webhooks.py`
- [ ] 3.5 directory — user, associations, organisations (4 ops) → `domains/directory.py` + `tests/test_directory.py`
- [ ] 3.6 files — 1 op → `domains/files.py` + `tests/test_files.py`

## 4. Integration (controller)

- [ ] 4.1 `scripts/extract_ops.py` — per-tag slices of the vendored spec for bounded sub-agent context
- [ ] 4.2 `server.py` — FastMCP app registering every domain module; stdio entry point `pingen-mcp-server`
- [ ] 4.3 Inventory test — expected tool list re-derived from `reference/openapi.json` equals registered tools (satisfies criterion c3 structural half)

## 5. Docs & live verification

- [ ] 5.1 README — install, configuration table, both grant flows, tool inventory, staging smoke instructions (satisfies criterion c4 doc half)
- [ ] 5.2 `scripts/staging_smoke.py` — opt-in live checks against `api-staging.pingen.com` via `PINGEN_ENV_FILE`; run when credentials exist (satisfies criterion c3 live half)
- [ ] 5.3 Fresh-clone check — install from README on a clean checkout, start server, list tools (satisfies criterion c4)

## 6. Closeout

- [ ] 6.1 Full suite green (`pytest -q`), `openspec change validate add-pingen-mcp-server --json` passes
- [ ] 6.2 Commit and push to `main`; post plan + evidence on registry card PINGEN-01
