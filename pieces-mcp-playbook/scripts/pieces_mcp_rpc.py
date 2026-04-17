#!/usr/bin/env python3
"""
pieces_mcp_rpc.py

A tiny MCP-over-SSE JSON-RPC client for debugging Pieces MCP locally.

Supports:
  - tools/list
  - tools/call (with arbitrary tool name + arguments)

Important:
  MCP-over-SSE typically requires opening the /sse stream FIRST, then POSTing requests
  to /messages, and reading responses from the SSE stream.

Examples:
  python scripts/pieces_mcp_rpc.py --list-tools
  python scripts/pieces_mcp_rpc.py --call-tool ask_pieces_ltm --args '{"question":"What did I work on yesterday?"}'
  python scripts/pieces_mcp_rpc.py --port 39300 --timeout 10 --list-tools

No third-party dependencies.
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import threading
import time
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 39300
DEFAULT_MCP_VERSION = "2024-11-05"


@dataclass(frozen=True)
class MCPConfig:
    host: str
    port: int
    mcp_version: str

    @property
    def sse_url(self) -> str:
        return f"http://{self.host}:{self.port}/model_context_protocol/{self.mcp_version}/sse"

    @property
    def messages_url(self) -> str:
        return f"http://{self.host}:{self.port}/model_context_protocol/{self.mcp_version}/messages"


class SSEListener(threading.Thread):
    def __init__(self, sse_url: str, out_q: "queue.Queue[Dict[str, Any]]", ready: threading.Event, timeout_s: float):
        super().__init__(daemon=True)
        self._sse_url = sse_url
        self._out_q = out_q
        self._ready = ready
        self._timeout_s = timeout_s
        self._stop = threading.Event()
        self._resp = None  # type: ignore

    def close(self) -> None:
        self._stop.set()
        try:
            if self._resp is not None:
                self._resp.close()
        except Exception:
            pass

    def run(self) -> None:
        req = urllib.request.Request(self._sse_url, headers={"Accept": "text/event-stream"})
        try:
            # NOTE: urllib timeout applies to socket ops; SSE can still be long-lived.
            self._resp = urllib.request.urlopen(req, timeout=self._timeout_s)
            self._ready.set()

            data_lines = []
            while not self._stop.is_set():
                raw = self._resp.readline()
                if not raw:
                    break
                line = raw.decode("utf-8", errors="replace").rstrip("\n")
                if line == "":
                    # dispatch event
                    if data_lines:
                        payload = "\n".join(data_lines).strip()
                        data_lines = []
                        try:
                            obj = json.loads(payload)
                            if isinstance(obj, dict):
                                self._out_q.put(obj)
                        except Exception:
                            # Not JSON payload; ignore
                            pass
                    continue

                if line.startswith("data:"):
                    data_lines.append(line[5:].lstrip())
                else:
                    # ignore "event:", comments, etc.
                    continue
        except Exception:
            self._ready.set()
            return
        finally:
            try:
                if self._resp is not None:
                    self._resp.close()
            except Exception:
                pass


def _post_json(url: str, payload: Dict[str, Any], timeout_s: float) -> Tuple[int, str]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read(1024 * 1024).decode("utf-8", errors="replace")
            return resp.status, body
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"


def _wait_for_id(out_q: "queue.Queue[Dict[str, Any]]", req_id: int, timeout_s: float) -> Optional[Dict[str, Any]]:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            msg = out_q.get(timeout=0.25)
        except queue.Empty:
            continue
        if isinstance(msg, dict) and msg.get("id") == req_id:
            return msg
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=os.getenv("PIECES_MCP_HOST", DEFAULT_HOST))
    ap.add_argument("--port", type=int, default=int(os.getenv("PIECES_MCP_PORT", str(DEFAULT_PORT))))
    ap.add_argument("--mcp-version", default=os.getenv("PIECES_MCP_VERSION", DEFAULT_MCP_VERSION))
    ap.add_argument("--timeout", type=float, default=10.0, help="Overall timeout seconds for a single request/response.")
    ap.add_argument("--list-tools", action="store_true")
    ap.add_argument("--call-tool", default=None, help="Tool name for tools/call.")
    ap.add_argument("--args", default="{}", help="JSON string for tool arguments (default: {}).")
    args = ap.parse_args()

    cfg = MCPConfig(args.host, args.port, args.mcp_version)
    out_q: "queue.Queue[Dict[str, Any]]" = queue.Queue()
    ready = threading.Event()

    listener = SSEListener(cfg.sse_url, out_q, ready, timeout_s=args.timeout)
    listener.start()
    ready.wait(timeout=2.0)

    if not args.list_tools and not args.call_tool:
        print("Nothing to do. Use --list-tools or --call-tool.")
        listener.close()
        return 2

    req_id = 1
    if args.list_tools:
        req = {"jsonrpc": "2.0", "id": req_id, "method": "tools/list"}
    else:
        try:
            tool_args = json.loads(args.args)
            if not isinstance(tool_args, dict):
                raise ValueError("tool args must be a JSON object")
        except Exception as e:
            print(f"Invalid --args JSON: {e}")
            listener.close()
            return 2

        req = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "tools/call",
            "params": {"name": args.call_tool, "arguments": tool_args},
        }

    status, body = _post_json(cfg.messages_url, req, timeout_s=args.timeout)
    # Many MCP-over-SSE servers return minimal or empty HTTP bodies here; responses arrive via SSE.
    if status == 0:
        print(f"POST failed: {body}")
        listener.close()
        return 3

    resp = _wait_for_id(out_q, req_id=req_id, timeout_s=args.timeout)
    listener.close()

    if resp is None:
        print("Timed out waiting for response on SSE stream.")
        print(f"SSE URL: {cfg.sse_url}")
        print(f"Messages URL: {cfg.messages_url}")
        return 4

    print(json.dumps(resp, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
