#!/usr/bin/env python3
"""
pieces_mcp_smoke_test.py

End-to-end smoke test against a local Pieces MCP server:
  - tools/list
  - optional tools/call ask_pieces_ltm
  - optional tools/call create_pieces_memory

This is meant to surface *actionable* failures quickly.

Examples:
  python scripts/pieces_mcp_smoke_test.py
  python scripts/pieces_mcp_smoke_test.py --chat-llm claude-3-5-sonnet-20241022
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import threading
import time
import urllib.request
from typing import Any, Dict, Optional


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 39300
DEFAULT_MCP_VERSION = "2024-11-05"


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
            self._resp = urllib.request.urlopen(req, timeout=self._timeout_s)
            self._ready.set()

            data_lines = []
            while not self._stop.is_set():
                raw = self._resp.readline()
                if not raw:
                    break
                line = raw.decode("utf-8", errors="replace").rstrip("\n")
                if line == "":
                    if data_lines:
                        payload = "\n".join(data_lines).strip()
                        data_lines = []
                        try:
                            obj = json.loads(payload)
                            if isinstance(obj, dict):
                                self._out_q.put(obj)
                        except Exception:
                            pass
                    continue
                if line.startswith("data:"):
                    data_lines.append(line[5:].lstrip())
        except Exception:
            self._ready.set()
            return
        finally:
            try:
                if self._resp is not None:
                    self._resp.close()
            except Exception:
                pass


def _post_json(url: str, payload: Dict[str, Any], timeout_s: float) -> None:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        # usually empty body; ignore
        _ = resp.read(1024)


def _wait_for_id(out_q: "queue.Queue[Dict[str, Any]]", req_id: int, timeout_s: float) -> Optional[Dict[str, Any]]:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            msg = out_q.get(timeout=0.25)
        except queue.Empty:
            continue
        if msg.get("id") == req_id:
            return msg
    return None


def _rpc(host: str, port: int, mcp_version: str, request: Dict[str, Any], timeout_s: float) -> Dict[str, Any]:
    sse_url = f"http://{host}:{port}/model_context_protocol/{mcp_version}/sse"
    msg_url = f"http://{host}:{port}/model_context_protocol/{mcp_version}/messages"

    out_q: "queue.Queue[Dict[str, Any]]" = queue.Queue()
    ready = threading.Event()
    listener = SSEListener(sse_url, out_q, ready, timeout_s=timeout_s)
    listener.start()
    ready.wait(timeout=2.0)

    req_id = int(request.get("id") or 1)
    _post_json(msg_url, request, timeout_s=timeout_s)
    resp = _wait_for_id(out_q, req_id=req_id, timeout_s=timeout_s)
    listener.close()

    if resp is None:
        return {"error": {"message": "timeout waiting for SSE response", "sse_url": sse_url, "messages_url": msg_url}}
    return resp


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=os.getenv("PIECES_MCP_HOST", DEFAULT_HOST))
    ap.add_argument("--port", type=int, default=int(os.getenv("PIECES_MCP_PORT", str(DEFAULT_PORT))))
    ap.add_argument("--mcp-version", default=os.getenv("PIECES_MCP_VERSION", DEFAULT_MCP_VERSION))
    ap.add_argument("--timeout", type=float, default=15.0)
    ap.add_argument("--chat-llm", default=os.getenv("PIECES_MCP_CHAT_LLM"), help="Optional model name for ask_pieces_ltm.")
    args = ap.parse_args()

    # 1) tools/list
    tools_list = _rpc(args.host, args.port, args.mcp_version, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, args.timeout)
    print("=== tools/list ===")
    print(json.dumps(tools_list, indent=2, ensure_ascii=False))

    tools = []
    try:
        tools = tools_list.get("result", {}).get("tools", [])  # common MCP shape
    except Exception:
        tools = []

    tool_names = {t.get("name") for t in tools if isinstance(t, dict)}
    print("\nTool names:", ", ".join(sorted(n for n in tool_names if n)))

    # 2) ask_pieces_ltm (optional)
    if "ask_pieces_ltm" in tool_names:
        ask_args: Dict[str, Any] = {"question": "What did I work on today?"}
        if args.chat_llm:
            ask_args["chat_llm"] = args.chat_llm
        ask_resp = _rpc(
            args.host,
            args.port,
            args.mcp_version,
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "ask_pieces_ltm", "arguments": ask_args}},
            args.timeout,
        )
        print("\n=== tools/call ask_pieces_ltm ===")
        print(json.dumps(ask_resp, indent=2, ensure_ascii=False))
    else:
        print("\n(no ask_pieces_ltm tool present; skipping)")

    # 3) create_pieces_memory (optional)
    if "create_pieces_memory" in tool_names:
        create_args = {
            "summary": "Smoke test memory",
            "summary_description": "Created by pieces_mcp_smoke_test.py to validate MCP write path.",
        }
        create_resp = _rpc(
            args.host,
            args.port,
            args.mcp_version,
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "create_pieces_memory", "arguments": create_args}},
            args.timeout,
        )
        print("\n=== tools/call create_pieces_memory ===")
        print(json.dumps(create_resp, indent=2, ensure_ascii=False))
    else:
        print("\n(no create_pieces_memory tool present; skipping)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
