#!/usr/bin/env python3
"""Opt-in LIVE smoke test against the Pingen API. Read-only.

Default environment is STAGING (letters simulated, nothing printed); hitting
production requires an explicit --environment production flag.

Usage:
    PYTHONPATH= .venv/Scripts/python.exe scripts/staging_smoke.py
    PYTHONPATH= .venv/Scripts/python.exe scripts/staging_smoke.py --environment production
    PINGEN_ENV_FILE=C:/ProgramData/pingen-mcp/credentials.env PYTHONPATH= \\
        .venv/Scripts/python.exe scripts/staging_smoke.py

Credentials come from the process environment or PINGEN_ENV_FILE, exactly like
the server itself. Secrets are NEVER printed - only presence and status.

Exit code 0 = every step succeeded; 1 = at least one step failed.
Never part of pytest (this file lives under scripts/, not tests/).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from pingen_mcp_server.auth import AuthError, provider_for  # noqa: E402
from pingen_mcp_server.client import PingenApiError, PingenClient  # noqa: E402
from pingen_mcp_server.config import ConfigError, load_config  # noqa: E402


def _data_count(payload) -> int:
    data = payload.get("data") if isinstance(payload, dict) else None
    return len(data) if isinstance(data, list) else (1 if data else 0)


def _first_ids(payload, limit: int = 5) -> list[str]:
    data = payload.get("data") or []
    return [str(item.get("id")) for item in data[:limit] if isinstance(item, dict)]


def run(environment: str) -> int:
    env = dict(os.environ)
    env.setdefault("PINGEN_ENVIRONMENT", environment)
    steps: list[dict] = []
    ok = True

    def record(name: str, status: str, detail: str) -> None:
        nonlocal ok
        if status != "ok":
            ok = False
        steps.append({"name": name, "status": status, "detail": detail})

    try:
        config = load_config(env)
    except ConfigError as exc:
        record("config", "fail", str(exc))
        print(json.dumps({"steps": steps}, indent=2))
        return 1

    record(
        "config",
        "ok",
        f"environment={config.environment} api={config.api_base_url} "
        f"grant={config.grant_type} client_id_set={bool(config.client_id)} "
        f"client_secret_set={bool(config.client_secret)}",
    )

    provider = provider_for(config)
    client = PingenClient(config, provider)
    try:
        try:
            token = provider.get_token()
            record("token", "ok", f"obtained ({len(token)} chars, value not printed)")
        except AuthError as exc:
            record("token", "fail", str(exc))
            _finish(steps, ok)
            return 1

        checks = [
            ("user", "/user"),
            ("organisations", "/organisations"),
            ("associations", "/user/associations"),
            ("letters", "/organisations/{org}/deliveries/letters"),
            ("batches", "/organisations/{org}/batches"),
        ]

        org_id = None
        try:
            orgs = client.get("/organisations")
            org_id = (orgs.get("data") or [{}])[0].get("id")
            record(
                "organisations",
                "ok",
                f"count={_data_count(orgs)} first_ids={_first_ids(orgs)}",
            )
        except PingenApiError as exc:
            record("organisations", "fail", str(exc))

        try:
            user = client.get("/user")
            uid = user.get("data", {}).get("id") if isinstance(user, dict) else None
            record("user", "ok", f"id={uid}")
        except PingenApiError as exc:
            record("user", "fail", str(exc))

        try:
            assoc = client.get("/user/associations")
            record("associations", "ok", f"count={_data_count(assoc)}")
        except PingenApiError as exc:
            record("associations", "fail", str(exc))

        if org_id:
            for name, path in (
                ("letters", f"/organisations/{org_id}/deliveries/letters"),
                ("batches", f"/organisations/{org_id}/batches"),
            ):
                try:
                    payload = client.collection(path, page_number=1, page_limit=5)
                    record(
                        name,
                        "ok",
                        f"page count={_data_count(payload)} ids={_first_ids(payload)}",
                    )
                except PingenApiError as exc:
                    record(name, "fail", str(exc))
        else:
            record("letters", "skip", "no organisation id available")
            record("batches", "skip", "no organisation id available")
    finally:
        client.close()
        provider.close()

    return _finish(steps, ok)


def _finish(steps: list[dict], ok: bool) -> int:
    print(json.dumps({"ok": ok, "steps": steps}, indent=2))
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--environment",
        choices=["staging", "production"],
        default="staging",
        help="staging (default) or production (explicit opt-in)",
    )
    args = parser.parse_args()
    return run(args.environment)


if __name__ == "__main__":
    sys.exit(main())
