#!/usr/bin/env python3
"""
pieces_mcp_rpc.py

A small MCP JSON-RPC client for debugging Pieces MCP locally or over a tunnel.

Supports:
  - tools/list
  - tools/call (with arbitrary tool name + arguments)
  - both transports: StreamableHTTP (/mcp, default) and SSE (/sse + /messages)

Examples:
  python scripts/pieces_mcp_rpc.py --list-tools
  python scripts/pieces_mcp_rpc.py --call-tool ask_pieces_ltm --args '{"question":"What did I work on yesterday?"}'
  python scripts/pieces_mcp_rpc.py --transport sse --list-tools
  python scripts/pieces_mcp_rpc.py --url https://abc123.ngrok-free.dev --list-tools

No third-party dependencies.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pieces_mcp_client import (  # noqa: E402
    DEFAULT_HOST, DEFAULT_MCP_VERSION, DEFAULT_PORT, PiecesMCPError, connect, ensure_utf8_stdout,
)


def main() -> int:
    ensure_utf8_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=os.getenv("PIECES_MCP_HOST", DEFAULT_HOST))
    ap.add_argument("--port", type=int, default=int(os.getenv("PIECES_MCP_PORT", str(DEFAULT_PORT))))
    ap.add_argument("--url", default=os.getenv("PIECES_MCP_URL"),
                    help="Full base URL (e.g. https://abc.ngrok-free.dev). Overrides --host/--port.")
    ap.add_argument("--mcp-version", default=os.getenv("PIECES_MCP_VERSION", DEFAULT_MCP_VERSION))
    ap.add_argument("--transport", default=os.getenv("PIECES_MCP_TRANSPORT", "auto"),
                    choices=["auto", "streamable-http", "sse"],
                    help="auto = StreamableHTTP first, SSE fallback (default).")
    ap.add_argument("--timeout", type=float, default=15.0,
                    help="Timeout seconds for a single request/response.")
    ap.add_argument("--list-tools", action="store_true")
    ap.add_argument("--call-tool", default=None, help="Tool name for tools/call.")
    ap.add_argument("--args", default="{}", help="JSON string for tool arguments (default: {}).")
    args = ap.parse_args()

    if not args.list_tools and not args.call_tool:
        print("Nothing to do. Use --list-tools or --call-tool.")
        return 2

    if args.call_tool:
        try:
            tool_args = json.loads(args.args)
            if not isinstance(tool_args, dict):
                raise ValueError("tool args must be a JSON object")
        except ValueError as e:
            print(f"Invalid --args JSON: {e}")
            return 2

    try:
        client = connect(host=args.host, port=args.port, mcp_version=args.mcp_version,
                         timeout_s=args.timeout, transport=args.transport, base_url=args.url)
    except PiecesMCPError as e:
        print(f"Connection failed: {e}")
        print("Hints: is PiecesOS running? Try `python scripts/pieces_mcp_scan.py` to find the endpoint.")
        return 3

    try:
        if args.list_tools:
            resp = client.request("tools/list")
        else:
            resp = client.request("tools/call", {"name": args.call_tool, "arguments": tool_args})
        print(json.dumps(resp, indent=2, ensure_ascii=False))
        return 0 if "result" in resp else 1
    except PiecesMCPError as e:
        print(f"Request failed ({client.transport}): {e}")
        return 4
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
