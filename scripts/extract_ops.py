#!/usr/bin/env python3
"""Extract bounded operation slices from the vendored Pingen OpenAPI spec.

The full spec (reference/openapi.json, ~6.4 MB, 2335 schemas) is too large for
a sub-agent to read whole. This script emits one JSON slice per domain with
everything a tool implementation needs: operationId, method, path, summary,
RESOLVED parameters ($ref followed), requestBody schema and response codes.

Usage:
  python scripts/extract_ops.py --list
  python scripts/extract_ops.py --domain letters
  python scripts/extract_ops.py --domain webhooks --with-incoming
  python scripts/extract_ops.py --tag deliveries.letters.events
  python scripts/extract_ops.py --domain letters --out /tmp/letters.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = REPO_ROOT / "reference" / "openapi.json"
METHODS = ("get", "post", "put", "patch", "delete")

# Domain bundles (must cover every client-callable operation exactly once).
DOMAINS: dict[str, list[str]] = {
    "letters": ["deliveries.letters.general", "deliveries.letters.events"],
    "batches": ["batches.general", "batches.events"],
    "channels": [
        "deliveries.ebills.general",
        "deliveries.ebills.events",
        "deliveries.emails.general",
        "deliveries.emails.events",
    ],
    "webhooks": ["organisations.management.webhooks"],
    "directory": ["user.general", "user.associations", "organisations.general"],
    "files": ["misc.files"],
}
INCOMING_TAG = "misc.webhooks"  # payload examples Pingen POSTs to customers


def resolve_ref(spec: dict[str, Any], node: Any) -> Any:
    """Follow a single local $ref; leave other structures untouched."""
    if isinstance(node, dict) and "$ref" in node:
        ref = node["$ref"]
        if ref.startswith("#/"):
            target: Any = spec
            for part in ref[2:].split("/"):
                target = target[part]
            return resolve_ref(spec, target)
    return node


def tool_name_for(operation_id: str) -> str:
    return operation_id.replace(".", "_").replace("-", "_")


def slice_operation(spec: dict[str, Any], path: str, method: str, op: dict[str, Any]) -> dict[str, Any]:
    params = [resolve_ref(spec, p) for p in op.get("parameters", [])]
    params += [resolve_ref(spec, p) for p in spec["paths"][path].get("parameters", [])]
    clean_params = [
        {
            "name": p.get("name"),
            "in": p.get("in"),
            "required": p.get("required", False),
            "schema": p.get("schema"),
            "description": p.get("description"),
        }
        for p in params
        if isinstance(p, dict)
    ]
    request_body = op.get("requestBody")
    responses = {
        code: sorted((resp.get("content") or {}).keys())
        for code, resp in sorted(op.get("responses", {}).items())
    }
    return {
        "operation_id": op.get("operationId"),
        "tool_name": tool_name_for(op.get("operationId", "")),
        "method": method.upper(),
        "path": path,
        "summary": op.get("summary"),
        "tags": op.get("tags", []),
        "parameters": clean_params,
        "path_parameters": [p["name"] for p in clean_params if p["in"] == "path"],
        "query_parameters": [p["name"] for p in clean_params if p["in"] == "query"],
        "request_body": (
            {
                "required": request_body.get("required", False),
                "content_types": sorted((request_body.get("content") or {}).keys()),
                "schema": resolve_ref(spec, request_body).get("content")
                if request_body
                else None,
            }
            if request_body
            else None
        ),
        "responses": responses,
    }


def collect(spec: dict[str, Any], tags: list[str]) -> list[dict[str, Any]]:
    wanted = set(tags)
    ops: list[dict[str, Any]] = []
    for path, path_item in spec["paths"].items():
        for method in METHODS:
            if method not in path_item:
                continue
            op = path_item[method]
            if wanted.intersection(op.get("tags", [])):
                ops.append(slice_operation(spec, path, method, op))
    return sorted(ops, key=lambda o: (o["path"], o["method"]))


def incoming_payload_examples(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """The misc.webhooks operations: payload shapes Pingen POSTs to a customer
    URL. Reference material for docs - never MCP tools."""
    out: list[dict[str, Any]] = []
    for path, path_item in spec["paths"].items():
        op = path_item.get("post")
        if not op or INCOMING_TAG not in op.get("tags", []):
            continue
        content = ((op.get("responses") or {}).get("200") or {}).get("content") or {}
        example = None
        for media, media_obj in content.items():
            example = media_obj.get("example")
            if example is not None:
                break
        out.append(
            {
                "path": path,
                "operation_id": op.get("operationId"),
                "summary": op.get("summary"),
                "example": example,
            }
        )
    return sorted(out, key=lambda o: o["path"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="list domain bundles and tags")
    parser.add_argument("--domain", choices=sorted(DOMAINS))
    parser.add_argument("--tag", action="append", default=[], help="raw tag(s)")
    parser.add_argument(
        "--with-incoming",
        action="store_true",
        help="also include misc.webhooks incoming payload examples",
    )
    parser.add_argument("--out", type=Path, help="write JSON here instead of stdout")
    args = parser.parse_args()

    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))

    if args.list:
        payload: Any = {"domains": DOMAINS, "incoming_tag": INCOMING_TAG}
    elif args.domain:
        tags = DOMAINS[args.domain]
        payload = {"domain": args.domain, "tags": tags, "operations": collect(spec, tags)}
        if args.with_incoming or args.domain == "webhooks":
            payload["incoming_payload_examples"] = incoming_payload_examples(spec)
    elif args.tag:
        payload = {"tags": args.tag, "operations": collect(spec, args.tag)}
    else:
        parser.error("one of --list, --domain or --tag is required")
        return 2

    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        ops = len(payload.get("operations", [])) if isinstance(payload, dict) else 0
        print(f"wrote {args.out} ({len(text)} bytes, {ops} operations)")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
