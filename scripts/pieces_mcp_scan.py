#!/usr/bin/env python3
"""
pieces_mcp_scan.py

Find a responsive Pieces MCP server on localhost by scanning a small port range.
Detects both transports on each responsive port:
  - StreamableHTTP: /model_context_protocol/<ver>/mcp   (recommended)
  - SSE:            /model_context_protocol/<ver>/sse   (legacy)

Also reads /.well-known/version to confirm it is really PiecesOS.

Typical usage:
  python scripts/pieces_mcp_scan.py
  python scripts/pieces_mcp_scan.py --host 127.0.0.1 --start 39000 --end 39400
  python scripts/pieces_mcp_scan.py --port 39300

This script does NOT require any third-party dependencies.
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
from dataclasses import dataclass
from typing import Iterable, Optional

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 39300
DEFAULT_START = 39000
DEFAULT_END = 39400
DEFAULT_MCP_VERSION = "2025-03-26"


@dataclass
class ScanResult:
    host: str
    port: int
    mcp_version: str
    pieces_version: Optional[str] = None
    has_streamable_http: bool = False
    has_sse: bool = False

    @property
    def base(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def mcp_url(self) -> str:
        return f"{self.base}/model_context_protocol/{self.mcp_version}/mcp"

    @property
    def sse_url(self) -> str:
        return f"{self.base}/model_context_protocol/{self.mcp_version}/sse"


def _get(host: str, port: int, path: str, timeout_s: float, headers: Optional[dict] = None):
    """GET returning (status, content_type, first_bytes) or None on connection failure."""
    conn = http.client.HTTPConnection(host, port, timeout=timeout_s)
    try:
        conn.request("GET", path, headers=headers or {})
        resp = conn.getresponse()
        ctype = (resp.getheader("Content-Type") or "").lower()
        # For SSE do not read the body (stream is long-lived); headers are enough.
        body = b"" if "text/event-stream" in ctype else resp.read(512)
        return resp.status, ctype, body
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _scan_port(host: str, port: int, mcp_version: str, timeout_s: float) -> Optional[ScanResult]:
    # Fast liveness gate: anything answering HTTP here is worth probing further.
    # Closed localhost ports refuse instantly, which keeps range scans fast; the
    # timeout only matters for slow-but-alive servers, so retry once before
    # giving up (PiecesOS occasionally answers slowly under load).
    r = _get(host, port, "/.well-known/version", timeout_s)
    if r is None:
        r = _get(host, port, "/.well-known/version", max(timeout_s, 2.0))
    if r is None:
        return None

    result = ScanResult(host, port, mcp_version)
    if r[0] == 200:
        result.pieces_version = r[2].decode("utf-8", errors="replace").strip() or None

    # The port is alive; give the transport probes a more generous timeout.
    probe_timeout = max(timeout_s, 2.0)

    # StreamableHTTP signature: bare GET /mcp returns HTTP 400 JSON complaining
    # about a missing session. That 400 is GOOD -- the route exists and is alive.
    r = _get(host, port, f"/model_context_protocol/{mcp_version}/mcp", probe_timeout)
    if r is not None:
        status, ctype, body = r
        if status in (200, 400, 405) and "json" in ctype:
            result.has_streamable_http = True

    r = _get(host, port, f"/model_context_protocol/{mcp_version}/sse", probe_timeout,
             headers={"Accept": "text/event-stream"})
    if r is not None and r[0] in (200, 204) and "text/event-stream" in r[1]:
        result.has_sse = True

    if not (result.has_streamable_http or result.has_sse):
        return None
    return result


def _ports_to_try(explicit_port: Optional[int], start: int, end: int) -> Iterable[int]:
    if explicit_port is not None:
        yield explicit_port
        return
    env_port = os.getenv("PIECES_MCP_PORT")
    if env_port and env_port.isdigit():
        yield int(env_port)
    yield DEFAULT_PORT
    for p in range(start, end + 1):
        if p == DEFAULT_PORT:
            continue
        yield p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--port", type=int, default=None, help="Check only this port.")
    ap.add_argument("--start", type=int, default=DEFAULT_START, help="Scan start port (inclusive).")
    ap.add_argument("--end", type=int, default=DEFAULT_END, help="Scan end port (inclusive).")
    ap.add_argument("--mcp-version", default=os.getenv("PIECES_MCP_VERSION", DEFAULT_MCP_VERSION))
    ap.add_argument("--timeout", type=float, default=1.0, help="Per-port connect timeout seconds.")
    ap.add_argument("--json", action="store_true", help="Machine-readable output.")
    ap.add_argument("--all", action="store_true",
                    help="Scan the whole range even after a hit (default: stop at first).")
    args = ap.parse_args()

    found = []
    seen = set()
    for port in _ports_to_try(args.port, args.start, args.end):
        if port in seen:
            continue
        seen.add(port)
        result = _scan_port(args.host, port, args.mcp_version, timeout_s=args.timeout)
        if result:
            found.append(result)
            if not args.all:
                break

    if not found:
        print("No Pieces MCP endpoint found.")
        print("Tips:")
        print("- Verify PiecesOS is running and LTM is enabled")
        print(f"- Try setting PIECES_MCP_PORT if your port is not {DEFAULT_PORT}")
        print("- Expand scan range: --start 30000 --end 60000")
        return 2

    if args.json:
        print(json.dumps([{
            "host": r.host, "port": r.port, "pieces_version": r.pieces_version,
            "streamable_http": r.mcp_url if r.has_streamable_http else None,
            "sse": r.sse_url if r.has_sse else None,
        } for r in found], indent=2))
        return 0

    print("Found Pieces MCP endpoint(s):")
    for r in found[:10]:
        version = f" (PiecesOS {r.pieces_version})" if r.pieces_version else ""
        print(f"- {r.host}:{r.port}{version}")
        if r.has_streamable_http:
            print(f"    StreamableHTTP (recommended): {r.mcp_url}")
        if r.has_sse:
            print(f"    SSE (legacy):                 {r.sse_url}")
    if len(found) > 10:
        print(f"...and {len(found) - 10} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
