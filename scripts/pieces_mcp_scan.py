#!/usr/bin/env python3
"""
pieces_mcp_scan.py

Find a responsive Pieces MCP SSE endpoint on localhost by scanning a small port range.

Typical usage:
  python scripts/pieces_mcp_scan.py
  python scripts/pieces_mcp_scan.py --host 127.0.0.1 --start 39000 --end 39400
  python scripts/pieces_mcp_scan.py --port 39300

This script does NOT require any third-party dependencies.
"""
from __future__ import annotations

import argparse
import http.client
import os
from dataclasses import dataclass
from typing import Iterable, Optional


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 39300
DEFAULT_START = 39000
DEFAULT_END = 39400
DEFAULT_MCP_VERSION = "2024-11-05"


@dataclass(frozen=True)
class Candidate:
    host: str
    port: int
    mcp_version: str

    @property
    def sse_path(self) -> str:
        return f"/model_context_protocol/{self.mcp_version}/sse"

    @property
    def sse_url(self) -> str:
        return f"http://{self.host}:{self.port}{self.sse_path}"


def _is_sse_endpoint(candidate: Candidate, timeout_s: float) -> bool:
    conn = http.client.HTTPConnection(candidate.host, candidate.port, timeout=timeout_s)
    try:
        conn.request("GET", candidate.sse_path, headers={"Accept": "text/event-stream"})
        resp = conn.getresponse()
        ctype = (resp.getheader("Content-Type") or "").lower()
        # Do not read the body (SSE is long-lived); just validate headers/status.
        return resp.status in (200, 204) and "text/event-stream" in ctype
    except Exception:
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _ports_to_try(explicit_port: Optional[int], start: int, end: int) -> Iterable[int]:
    if explicit_port is not None:
        yield explicit_port
        return

    # Try env override first
    env_port = os.getenv("PIECES_MCP_PORT")
    if env_port and env_port.isdigit():
        yield int(env_port)

    # Then the common default
    yield DEFAULT_PORT

    # Finally scan the range (inclusive)
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
    ap.add_argument("--mcp-version", default=DEFAULT_MCP_VERSION)
    ap.add_argument("--timeout", type=float, default=0.35, help="Per-port connect timeout seconds.")
    args = ap.parse_args()

    found = []
    for port in _ports_to_try(args.port, args.start, args.end):
        c = Candidate(args.host, port, args.mcp_version)
        if _is_sse_endpoint(c, timeout_s=args.timeout):
            found.append(c)

    if not found:
        print("No Pieces MCP SSE endpoint found.")
        print("Tips:")
        print(f"- Verify PiecesOS is running and LTM is enabled")
        print(f"- Try setting PIECES_MCP_PORT if your port is not {DEFAULT_PORT}")
        print(f"- Expand scan range: --start 30000 --end 60000")
        return 2

    print("Found Pieces MCP SSE endpoint(s):")
    for c in found[:10]:
        print(f"- {c.sse_url}")
    if len(found) > 10:
        print(f"...and {len(found)-10} more")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
