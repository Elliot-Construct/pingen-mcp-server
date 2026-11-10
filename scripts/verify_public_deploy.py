#!/usr/bin/env python3
"""Verify the public Pingen MCP deployment against the card's criteria.

PINGEN-02 c1-c4. Run from anywhere; it talks to the live URL, not to a mock.

    python scripts/verify_public_deploy.py            # all checks
    python scripts/verify_public_deploy.py --json      # machine-readable

Checks
  c1  anonymous POST /mcp over trusted TLS -> MCP 401 challenge, never 502/404/000
  c2  anonymous rejected AND an identity-layer-issued token accepted
  c3  a real MCP client completes the flow and tools/list returns 49 tools
  c4  routes.yml router, cert SAN, DDNS target, and survival of a Traefik restart

c2/c3 need identity-layer client credentials. They are read from
PINGEN_IDP_CLIENT_FILE (default C:/ProgramData/pingen-mcp/idp-client.env,
KEY=VALUE, outside the repo) and are never printed. Without them those checks
report status="skipped" rather than passing silently.

Exit code 0 only when every executed check passed (skipped is not a pass).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PUBLIC_URL = os.environ.get("PINGEN_MCP_PUBLIC_URL", "https://pingen-mcp.datawyse.ai/mcp")
ORIGIN = PUBLIC_URL.rsplit("/mcp", 1)[0]
HOST = urllib.parse.urlparse(ORIGIN).hostname or "pingen-mcp.datawyse.ai"
ROUTES_YML = Path(os.environ.get("PINGEN_ROUTES_YML", r"C:\ProgramData\traefik\dynamic\routes.yml"))
DDNS_JSON = Path(
    os.environ.get(
        "PINGEN_DDNS_JSON",
        r"C:\Users\Elliot\AppData\Local\hermes\scripts\ddns-cloudflare-sync.json",
    )
)
IDP_CLIENT_FILE = Path(
    os.environ.get("PINGEN_IDP_CLIENT_FILE", r"C:\ProgramData\pingen-mcp\idp-client.env")
)
EXPECTED_TOOLS = 49

RESULTS: list[dict] = []


def record(cid: str, name: str, status: str, detail: str) -> None:
    RESULTS.append({"criterion": cid, "check": name, "status": status, "detail": detail})
    mark = {"pass": "PASS", "fail": "FAIL", "skip": "SKIP"}[status]
    print(f"[{mark}] {cid} {name}: {detail}")


def read_key_value_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        out[key.strip()] = val.strip().strip('"').strip("'")
    return out


def post_mcp(payload: dict, token: str | None, timeout: int = 30):
    """POST to /mcp; returns (status, headers, body) or (0, {}, error)."""
    req = urllib.request.Request(
        PUBLIC_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
        method="POST",
    )
    # Trusted TLS: system CA store, no -k equivalent anywhere in this script.
    ctx = ssl.create_default_context()
    # Header keys are lower-cased: urllib preserves the wire casing
    # ("Www-Authenticate" title-case), and a case-sensitive lookup
    # silently reports the challenge as missing.
    def norm(headers) -> dict[str, str]:
        return {k.lower(): v for k, v in headers.items()}

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.status, norm(resp.headers), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, norm(exc.headers), exc.read().decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001 - surfaced as a failed check
        return 0, {}, f"{type(exc).__name__}: {exc}"


def initialize_payload() -> dict:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "pingen-verify", "version": "1.0"},
        },
    }


def check_c1() -> None:
    status, headers, body = post_mcp(initialize_payload(), token=None)
    www = headers.get("www-authenticate", "")
    if status in (502, 404, 0):
        record("c1", "anonymous-challenge", "fail", f"HTTP {status} {body[:160]}")
        return
    if status != 401:
        record("c1", "anonymous-challenge", "fail", f"expected 401, got {status}")
        return
    if "resource_metadata=" not in www:
        record("c1", "anonymous-challenge", "fail", f"401 without resource_metadata: {www[:160]}")
        return
    record("c1", "anonymous-challenge", "pass", f"HTTP 401, {www[:180]}")


def fetch_metadata() -> dict | None:
    """Follow the 401 challenge to the RFC 9728 document (public, no auth)."""
    _, headers, _ = post_mcp(initialize_payload(), token=None)
    www = headers.get("www-authenticate", "")
    match = re.search(r'resource_metadata="([^"]+)"', www)
    if not match:
        return None
    url = match.group(1)
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(url, timeout=30, context=ctx) as resp:
            return json.loads(resp.read().decode())
    except Exception:  # noqa: BLE001
        return None


def mint_token() -> tuple[str | None, str]:
    """Client-credentials grant against the identity layer."""
    creds = read_key_value_file(IDP_CLIENT_FILE)
    client_id = creds.get("IDP_CLIENT_ID")
    client_secret = creds.get("IDP_CLIENT_SECRET")
    token_url = creds.get("IDP_TOKEN_URL")
    if not (client_id and client_secret and token_url):
        return None, f"no IdP client credentials at {IDP_CLIENT_FILE}"
    data = urllib.parse.urlencode(
        {"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret}
    ).encode()
    req = urllib.request.Request(
        token_url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return None, f"token endpoint HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:200]}"
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"
    token = payload.get("access_token")
    if not token:
        return None, "token response carried no access_token"
    # Decode claims (no signature check here — the server does that) so the
    # evidence shows what the identity layer actually issued.
    claims = json.loads(
        __import__("base64").urlsafe_b64decode(
            token.split(".")[1] + "=" * (-len(token.split(".")[1]) % 4)
        ).decode("utf-8", "replace")
    )
    return token, (
        f"iss={claims.get('iss')} aud={claims.get('aud')} azp={claims.get('azp')} "
        f"exp_in={int(claims.get('exp', 0)) - int(__import__('time').time())}s"
    )


def check_c2(token: str | None, mint_detail: str) -> None:
    anon_status, _, _ = post_mcp(initialize_payload(), token=None)
    if anon_status != 401:
        record("c2", "anonymous-rejected", "fail", f"expected 401, got {anon_status}")
    else:
        record("c2", "anonymous-rejected", "pass", "HTTP 401")

    if token is None:
        record("c2", "identity-token-accepted", "skip", mint_detail)
        return
    status, _, body = post_mcp(initialize_payload(), token=token)
    if status == 200:
        record("c2", "identity-token-accepted", "pass", f"HTTP 200 ({mint_detail})")
    else:
        record("c2", "identity-token-accepted", "fail", f"HTTP {status} {body[:200]} ({mint_detail})")


def check_c3(token: str | None, mint_detail: str) -> None:
    if token is None:
        record("c3", "tools-list", "skip", mint_detail)
        return
    status, headers, body = post_mcp(initialize_payload(), token=token)
    if status != 200:
        record("c3", "tools-list", "fail", f"initialize HTTP {status} {body[:200]}")
        return
    session = headers.get("mcp-session-id")
    listing = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {},
    }
    if session:
        req = urllib.request.Request(
            PUBLIC_URL,
            data=json.dumps(listing).encode(),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "Authorization": f"Bearer {token}",
                "Mcp-Session-Id": session,
            },
            method="POST",
        )
        ctx = ssl.create_default_context()
        try:
            with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
                lstatus, lbody = resp.status, resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            lstatus, lbody = exc.code, exc.read().decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001
            lstatus, lbody = 0, f"{type(exc).__name__}: {exc}"
    else:
        lstatus, _, lbody = post_mcp(listing, token=token)

    if lstatus != 200:
        record("c3", "tools-list", "fail", f"tools/list HTTP {lstatus} {lbody[:200]}")
        return
    # SSE frames or plain JSON both carry the tool array.
    try:
        doc = json.loads(lbody[lbody.index("{"):])
        count = len(doc.get("result", {}).get("tools", []))
    except Exception:  # noqa: BLE001 - SSE-wrapped
        count = lbody.count('"description"')
    if count == EXPECTED_TOOLS:
        record("c3", "tools-list", "pass", f"{count} tools over {PUBLIC_URL}")
    else:
        record("c3", "tools-list", "fail", f"expected {EXPECTED_TOOLS} tools, saw {count}")


def check_c4() -> None:
    # routes.yml carries a Host() router for this hostname.
    if ROUTES_YML.is_file():
        text = ROUTES_YML.read_text(encoding="utf-8", errors="replace")
        if f"Host(`{HOST}`)" in text:
            record("c4", "routes.yml-router", "pass", f"Host(`{HOST}`) present in {ROUTES_YML}")
        else:
            record("c4", "routes.yml-router", "fail", f"no Host(`{HOST}`) rule in {ROUTES_YML}")
    else:
        record("c4", "routes.yml-router", "fail", f"{ROUTES_YML} not found")

    # certificate SAN names this host (trusted chain, no -k).
    try:
        out = subprocess.run(
            [
                "openssl", "s_client", "-connect", f"{HOST}:443",
                "-servername", HOST,
            ],
            input="", capture_output=True, text=True, timeout=30,
        )
        san = subprocess.run(
            ["openssl", "x509", "-noout", "-ext", "subjectAltName"],
            input=out.stdout, capture_output=True, text=True, timeout=30,
        )
        if HOST in san.stdout:
            record("c4", "cert-san", "pass", san.stdout.strip().replace("\n", " ")[:200])
        else:
            record("c4", "cert-san", "fail", f"SAN does not name {HOST}: {san.stdout.strip()[:200]}")
    except FileNotFoundError:
        record("c4", "cert-san", "skip", "openssl not on PATH")
    except Exception as exc:  # noqa: BLE001
        record("c4", "cert-san", "fail", f"{type(exc).__name__}: {exc}")

    # DDNS target present.
    if DDNS_JSON.is_file():
        cfg = json.loads(DDNS_JSON.read_text(encoding="utf-8"))
        names = [t.get("record_name") for t in cfg.get("targets", [])]
        if f"{HOST}" in names:
            record("c4", "ddns-target", "pass", f"{HOST} in {DDNS_JSON.name} targets ({len(names)} total)")
        else:
            record("c4", "ddns-target", "fail", f"{HOST} missing from targets: {names}")
    else:
        record("c4", "ddns-target", "fail", f"{DDNS_JSON} not found")


def check_c4_restart() -> None:
    """docker restart traefik, then prove the route still serves."""
    try:
        subprocess.run(["docker", "restart", "traefik"], check=True, capture_output=True, timeout=180)
    except Exception as exc:  # noqa: BLE001
        record("c4", "traefik-restart", "fail", f"restart failed: {type(exc).__name__}: {exc}")
        return
    import time

    deadline = time.time() + 60
    last = (0, "")
    while time.time() < deadline:
        status, _, _ = post_mcp(initialize_payload(), token=None)
        last = (status, "")
        if status == 401:
            record("c4", "traefik-restart", "pass", "still serving 401 challenge after docker restart traefik")
            return
        time.sleep(3)
    record("c4", "traefik-restart", "fail", f"no 401 within 60s of restart (last HTTP {last[0]})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit machine-readable results")
    parser.add_argument("--skip-restart", action="store_true", help="do not restart Traefik")
    args = parser.parse_args()

    print(f"target: {PUBLIC_URL}")
    metadata = fetch_metadata()
    if metadata:
        print(f"RFC 9728 metadata: authorization_servers={metadata.get('authorization_servers')}")
    else:
        print("RFC 9728 metadata: not reachable")

    check_c1()
    token, mint_detail = mint_token()
    check_c2(token, mint_detail)
    check_c3(token, mint_detail)
    check_c4()
    if not args.skip_restart:
        check_c4_restart()

    failed = [r for r in RESULTS if r["status"] == "fail"]
    skipped = [r for r in RESULTS if r["status"] == "skip"]
    print(
        f"\nsummary: {len(RESULTS)} checks, "
        f"{len(RESULTS) - len(failed) - len(skipped)} passed, "
        f"{len(failed)} failed, {len(skipped)} skipped"
    )
    if args.json:
        print(json.dumps({"results": RESULTS, "failed": len(failed), "skipped": len(skipped)}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
