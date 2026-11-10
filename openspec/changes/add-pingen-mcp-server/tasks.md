# Tasks — add-pingen-mcp-server

## 1. Scaffold

- [x] 1.1 `pyproject.toml` (package `pingen-mcp-server`; deps `fastmcp`, `httpx`; dev `pytest`, `respx`), `src/pingen_mcp_server/` layout, pytest configuration
- [x] 1.2 `.env.example` with placeholder variable names only (no values)

## 2. Core (built first, frozen as minion interface)

- [x] 2.1 `config.py` — environment mapping (production/staging hosts), grant selection, `PINGEN_ENV_FILE` loading, token-file path resolution; unit tests
- [x] 2.2 `auth.py` — client-credentials provider (cache + 60 s skew re-fetch); authorization-code authorize-URL builder, code exchange, refresh with rotation persisted to token file; unit tests (satisfies criterion c2)
- [x] 2.3 `client.py` — httpx JSON:API client: bearer injection, base URL, `page[number]`/`page[limit]` mapping, query pass-through, error mapping with `X-Request-Id`; unit tests

## 3. Domains (parallel minion sub-agents, one per domain)

- [x] 3.1 letters — 14 ops (general + events) → `domains/letters.py` + `tests/test_letters.py`
- [x] 3.2 batches — 9 ops → `domains/batches.py` + `tests/test_batches.py`
- [x] 3.3 channels — ebills (9) + emails (8) → `domains/channels.py` + `tests/test_channels.py`
- [x] 3.4 webhooks — 4 org-webhook ops → `domains/webhooks.py` + `tests/test_webhooks.py`
- [x] 3.5 directory — user, associations, organisations (4 ops) → `domains/directory.py` + `tests/test_directory.py`
- [x] 3.6 files — 1 op → `domains/files.py` + `tests/test_files.py`

## 4. Integration (controller)

- [x] 4.1 `scripts/extract_ops.py` — per-tag slices of the vendored spec for bounded sub-agent context
- [x] 4.2 `server.py` — FastMCP app registering every domain module; stdio entry point `pingen-mcp-server`
- [x] 4.3 Inventory test — expected tool list re-derived from `reference/openapi.json` equals registered tools (satisfies criterion c3 structural half)

## 5. Docs & live verification

- [x] 5.1 README — install, configuration table, both grant flows, tool inventory, staging smoke instructions (satisfies criterion c4 doc half)
- [x] 5.2 `scripts/staging_smoke.py` — opt-in live smoke (staging by default; production needs an explicit flag). Staging credentials are not yet provisioned (401 invalid_client: the provided env file holds production credentials), so the live run was executed against PRODUCTION read-only under Arthur's option-B ruling: 7/7 steps HTTP 200 (user, organisations, associations, letters collection, batches collection), zero writes, probe token deleted immediately. Staging run pending Elliot's staging credentials; disclosed on the card (c3 live half)
- [x] 5.3 Fresh-clone check — fresh clone of remote main (ab97475) into scratch: venv + `pip install -e .[dev]`, README one-liner -> 49 tools, console script present, real MCP stdio handshake (initialize -> tools/list) -> 49 tools, fresh-clone pytest -> 129 passed (satisfies criterion c4)

## 6. Closeout

- [x] 6.1 Full suite green (129 passed, exit 0), `openspec change validate add-pingen-mcp-server --json` -> valid:true errors:0 warnings:0 exit 0
- [ ] 6.2 Commit and push to `main`; post plan + evidence on registry card PINGEN-01
