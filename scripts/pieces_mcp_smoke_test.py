#!/usr/bin/env python3
"""
pieces_mcp_smoke_test.py

End-to-end smoke test against a local Pieces MCP server:
  - /.well-known/version check
  - connect (StreamableHTTP first, SSE fallback) + initialize handshake
  - tools/list
  - optional: tools/call ask_pieces_ltm      (--ask;   slow, invokes the LTM pipeline)
  - optional: tools/call create_pieces_memory (--write; writes a real memory to LTM)

This is meant to surface *actionable* failures quickly. The default run is read-only.

Examples:
  python scripts/pieces_mcp_smoke_test.py
  python scripts/pieces_mcp_smoke_test.py --ask
  python scripts/pieces_mcp_smoke_test.py --ask --write --chat-llm gemini-2.5-flash
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from typing import Any, Dict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pieces_mcp_client import (  # noqa: E402
    DEFAULT_HOST, DEFAULT_MCP_VERSION, DEFAULT_PORT, PiecesMCPError, connect,
    ensure_utf8_stdout, tool_result_text,
)


def _pieces_version(base_url: str, timeout_s: float) -> str:
    try:
        with urllib.request.urlopen(f"{base_url}/.well-known/version", timeout=timeout_s) as resp:
            return resp.read(64).decode("utf-8", errors="replace").strip()
    except Exception as e:
        return f"unavailable ({type(e).__name__})"


def _print_call(title: str, resp: Dict[str, Any]) -> None:
    print(f"\n=== {title} ===")
    text = tool_result_text(resp)
    if text:
        print(text[:2000])
        if len(text) > 2000:
            print(f"... ({len(text)} chars total)")
    else:
        print(json.dumps(resp, indent=2, ensure_ascii=False)[:2000])


def main() -> int:
    ensure_utf8_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=os.getenv("PIECES_MCP_HOST", DEFAULT_HOST))
    ap.add_argument("--port", type=int, default=int(os.getenv("PIECES_MCP_PORT", str(DEFAULT_PORT))))
    ap.add_argument("--url", default=os.getenv("PIECES_MCP_URL"),
                    help="Full base URL (e.g. https://abc.ngrok-free.dev). Overrides --host/--port.")
    ap.add_argument("--mcp-version", default=os.getenv("PIECES_MCP_VERSION", DEFAULT_MCP_VERSION))
    ap.add_argument("--transport", default=os.getenv("PIECES_MCP_TRANSPORT", "auto"),
                    choices=["auto", "streamable-http", "sse"])
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--ask", action="store_true",
                    help="Also call ask_pieces_ltm (slow; exercises the full LTM pipeline).")
    ap.add_argument("--write", action="store_true",
                    help="Also call create_pieces_memory (writes a real memory to your LTM).")
    ap.add_argument("--chat-llm", default=os.getenv("PIECES_MCP_CHAT_LLM"),
                    help="Optional model name passed to ask_pieces_ltm.")
    args = ap.parse_args()

    base_url = (args.url.rstrip("/") if args.url else f"http://{args.host}:{args.port}")
    print(f"PiecesOS version: {_pieces_version(base_url, timeout_s=5.0)}")

    try:
        client = connect(host=args.host, port=args.port, mcp_version=args.mcp_version,
                         timeout_s=args.timeout, transport=args.transport, base_url=args.url)
    except PiecesMCPError as e:
        print(f"FAIL: could not connect: {e}")
        print("Hints:")
        print("- Is PiecesOS running with LTM enabled? (see references/PREREQS.md)")
        print("- Run `python scripts/pieces_mcp_scan.py` to locate the endpoint")
        return 3
    print(f"Connected via {client.transport} to {base_url}")

    failures = 0
    try:
        # 1) tools/list
        resp = client.request("tools/list")
        tools = resp.get("result", {}).get("tools", [])
        if not tools:
            print(f"FAIL: tools/list returned no tools: {json.dumps(resp)[:500]}")
            return 4
        tool_names = sorted(t.get("name", "") for t in tools if isinstance(t, dict))
        print(f"\n=== tools/list ===\n{len(tool_names)} tools:")
        print(", ".join(tool_names))

        # 2) ask_pieces_ltm (opt-in)
        if args.ask:
            if "ask_pieces_ltm" in tool_names:
                ask_args: Dict[str, Any] = {"question": "What did I work on today?"}
                if args.chat_llm:
                    ask_args["chat_llm"] = args.chat_llm
                try:
                    resp = client.request("tools/call", {"name": "ask_pieces_ltm", "arguments": ask_args})
                    _print_call("tools/call ask_pieces_ltm", resp)
                    if "error" in resp:
                        failures += 1
                except PiecesMCPError as e:
                    print(f"\nFAIL: ask_pieces_ltm: {e}")
                    failures += 1
            else:
                print("\n(no ask_pieces_ltm tool present; skipping --ask)")

        # 3) create_pieces_memory (opt-in)
        if args.write:
            if "create_pieces_memory" in tool_names:
                create_args = {
                    "summary_description": "Smoke test memory",
                    "summary": ("## Smoke test\nCreated by pieces_mcp_smoke_test.py to validate "
                                "the MCP write path. Safe to delete."),
                }
                try:
                    resp = client.request("tools/call", {"name": "create_pieces_memory", "arguments": create_args})
                    _print_call("tools/call create_pieces_memory", resp)
                    if "error" in resp:
                        failures += 1
                except PiecesMCPError as e:
                    print(f"\nFAIL: create_pieces_memory: {e}")
                    failures += 1
            else:
                print("\n(no create_pieces_memory tool present; skipping --write)")
    except PiecesMCPError as e:
        print(f"FAIL ({client.transport}): {e}")
        return 4
    finally:
        client.close()

    if failures:
        print(f"\nSmoke test finished with {failures} failing tool call(s).")
        return 1
    print("\nSmoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
