#!/usr/bin/env python3
"""
pieces_mcp_client.py

Shared MCP client for the Pieces MCP server. Supports both transports:

  - StreamableHTTP (recommended): POST JSON-RPC to /model_context_protocol/<ver>/mcp
    Flow: initialize -> capture mcp-session-id response header -> notifications/initialized
    -> requests. Short-lived HTTP requests, no long-lived sockets.

  - SSE (legacy): GET /model_context_protocol/<ver>/sse opens a long-lived stream.
    The server's FIRST event is `endpoint`, whose data is the POST URL including
    per-connection sessionId and token query parameters. You MUST post to that URL,
    never to a hand-built /messages path (bare /messages returns HTTP 400
    "Missing sessionId query parameter"). Responses arrive on the SSE stream.

No third-party dependencies. Python 3.8+.

Usage:
    from pieces_mcp_client import connect
    client = connect(host="127.0.0.1", port=39300)   # tries StreamableHTTP, falls back to SSE
    resp = client.request("tools/list")
    client.close()
"""
from __future__ import annotations

import json
import queue
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional


def ensure_utf8_stdout() -> None:
    """Tool descriptions contain non-ASCII characters; Windows consoles default to
    cp1252 and crash on print. Switch stdout/stderr to UTF-8 with replacement."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 39300
DEFAULT_MCP_VERSION = "2025-03-26"
CLIENT_INFO = {"name": "pieces-mcp-playbook", "version": "4.0.0"}


class PiecesMCPError(Exception):
    """Raised when a transport-level or protocol-level failure occurs."""


def _parse_sse_body(body: str) -> Optional[Dict[str, Any]]:
    """Parse a text/event-stream response body and return the first JSON message."""
    data_lines = []
    for line in body.splitlines():
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
        elif line.strip() == "" and data_lines:
            try:
                return json.loads("\n".join(data_lines))
            except ValueError:
                data_lines = []
    if data_lines:
        try:
            return json.loads("\n".join(data_lines))
        except ValueError:
            return None
    return None


class StreamableHTTPClient:
    """MCP StreamableHTTP transport (the /mcp endpoint). Preferred."""

    def __init__(self, base_url: str, mcp_version: str = DEFAULT_MCP_VERSION, timeout_s: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.mcp_version = mcp_version
        self.timeout_s = timeout_s
        self.url = f"{self.base_url}/model_context_protocol/{mcp_version}/mcp"
        self.session_id: Optional[str] = None
        self._next_id = 0
        self.transport = "streamable-http"

    def _post(self, payload: Dict[str, Any], expect_response: bool) -> Optional[Dict[str, Any]]:
        headers = {
            "Content-Type": "application/json",
            # Both types are required; some builds reply application/json, others SSE-framed.
            "Accept": "application/json, text/event-stream",
        }
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
        req = urllib.request.Request(self.url, data=json.dumps(payload).encode("utf-8"),
                                     method="POST", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                sid = resp.headers.get("mcp-session-id")
                if sid:
                    self.session_id = sid
                if not expect_response:
                    return None
                body = resp.read().decode("utf-8", errors="replace")
                ctype = (resp.headers.get("Content-Type") or "").lower()
                if "text/event-stream" in ctype:
                    return _parse_sse_body(body)
                return json.loads(body) if body.strip() else None
        except urllib.error.HTTPError as e:
            detail = e.read(2048).decode("utf-8", errors="replace")
            raise PiecesMCPError(f"POST {self.url} -> HTTP {e.code}: {detail}") from e
        except (urllib.error.URLError, OSError) as e:
            raise PiecesMCPError(f"POST {self.url} failed: {e}") from e

    def connect(self) -> "StreamableHTTPClient":
        # String JSON-RPC ids: integer ids have caused HTTP 500s on some tunnel setups.
        init = {
            "jsonrpc": "2.0", "id": "init", "method": "initialize",
            "params": {"protocolVersion": self.mcp_version, "capabilities": {}, "clientInfo": CLIENT_INFO},
        }
        resp = self._post(init, expect_response=True)
        if resp is None or "result" not in resp:
            raise PiecesMCPError(f"initialize failed: {json.dumps(resp) if resp else 'empty response'}")
        if not self.session_id:
            raise PiecesMCPError("initialize succeeded but no mcp-session-id header was returned")
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"}, expect_response=False)
        return self

    def request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._next_id += 1
        payload: Dict[str, Any] = {"jsonrpc": "2.0", "id": str(self._next_id), "method": method}
        if params is not None:
            payload["params"] = params
        resp = self._post(payload, expect_response=True)
        if resp is None:
            raise PiecesMCPError(f"{method}: empty response body")
        return resp

    def close(self) -> None:
        if not self.session_id:
            return
        req = urllib.request.Request(self.url, method="DELETE",
                                     headers={"mcp-session-id": self.session_id})
        try:
            urllib.request.urlopen(req, timeout=self.timeout_s).close()
        except Exception:
            pass  # session teardown is best-effort


class SSEClient:
    """MCP SSE transport (the /sse + endpoint-event /messages pair). Legacy."""

    def __init__(self, base_url: str, mcp_version: str = DEFAULT_MCP_VERSION, timeout_s: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.mcp_version = mcp_version
        self.timeout_s = timeout_s
        self.sse_url = f"{self.base_url}/model_context_protocol/{mcp_version}/sse"
        self.messages_url: Optional[str] = None
        self.transport = "sse"
        self._next_id = 0
        self._queue: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self._endpoint_ready = threading.Event()
        self._stop = threading.Event()
        self._resp = None
        self._thread: Optional[threading.Thread] = None
        self._listen_error: Optional[str] = None

    def _listen(self) -> None:
        req = urllib.request.Request(self.sse_url, headers={"Accept": "text/event-stream"})
        event_name = None
        data_lines = []
        try:
            self._resp = urllib.request.urlopen(req, timeout=self.timeout_s)
            while not self._stop.is_set():
                raw = self._resp.readline()
                if not raw:
                    break
                line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                if line == "":
                    if data_lines:
                        payload = "\n".join(data_lines)
                        if event_name == "endpoint":
                            # data is the POST URL (usually relative) with sessionId + token
                            self.messages_url = urllib.parse.urljoin(self.base_url + "/", payload)
                            self._endpoint_ready.set()
                        else:
                            try:
                                obj = json.loads(payload)
                                if isinstance(obj, dict):
                                    self._queue.put(obj)
                            except ValueError:
                                pass
                    event_name = None
                    data_lines = []
                    continue
                if line.startswith("event:"):
                    event_name = line[6:].strip()
                elif line.startswith("data:"):
                    data_lines.append(line[5:].lstrip())
        except Exception as e:
            self._listen_error = f"{type(e).__name__}: {e}"
            self._endpoint_ready.set()
        finally:
            try:
                if self._resp is not None:
                    self._resp.close()
            except Exception:
                pass

    def _post(self, payload: Dict[str, Any]) -> None:
        assert self.messages_url is not None
        req = urllib.request.Request(self.messages_url, data=json.dumps(payload).encode("utf-8"),
                                     method="POST", headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                resp.read(1024)  # typically "Message processed"
        except urllib.error.HTTPError as e:
            detail = e.read(2048).decode("utf-8", errors="replace")
            raise PiecesMCPError(f"POST {self.messages_url} -> HTTP {e.code}: {detail}") from e
        except (urllib.error.URLError, OSError) as e:
            raise PiecesMCPError(f"POST {self.messages_url} failed: {e}") from e

    def _wait_for_id(self, req_id: int, timeout_s: float) -> Optional[Dict[str, Any]]:
        import time
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            try:
                msg = self._queue.get(timeout=0.25)
            except queue.Empty:
                continue
            if msg.get("id") == req_id:
                return msg
        return None

    def connect(self) -> "SSEClient":
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()
        if not self._endpoint_ready.wait(timeout=min(self.timeout_s, 10.0)) or self.messages_url is None:
            self.close()
            hint = self._listen_error or "no `endpoint` event received"
            raise PiecesMCPError(f"SSE handshake failed on {self.sse_url}: {hint}")
        # Spec-correct handshake. Current PiecesOS builds accept requests without it,
        # but future builds may enforce initialization, so always perform it.
        # The SSE /messages endpoint requires INTEGER JSON-RPC ids; string ids
        # are rejected with -32700 Parse error (verified on PiecesOS 12.5.0).
        self._post({"jsonrpc": "2.0", "id": 0, "method": "initialize",
                    "params": {"protocolVersion": self.mcp_version, "capabilities": {},
                               "clientInfo": CLIENT_INFO}})
        self._wait_for_id(0, timeout_s=min(self.timeout_s, 5.0))
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return self

    def request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._next_id += 1
        req_id = self._next_id
        payload: Dict[str, Any] = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params is not None:
            payload["params"] = params
        self._post(payload)
        resp = self._wait_for_id(req_id, timeout_s=self.timeout_s)
        if resp is None:
            raise PiecesMCPError(f"{method}: timed out waiting for response on SSE stream "
                                 f"(sse={self.sse_url}, messages={self.messages_url})")
        return resp

    def close(self) -> None:
        self._stop.set()
        try:
            if self._resp is not None:
                self._resp.close()
        except Exception:
            pass


def connect(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
            mcp_version: str = DEFAULT_MCP_VERSION, timeout_s: float = 15.0,
            transport: str = "auto", base_url: Optional[str] = None):
    """Connect to a Pieces MCP server. Returns a connected client.

    transport: "auto" (StreamableHTTP with SSE fallback), "streamable-http", or "sse".
    base_url:  full base URL such as "https://abc.ngrok-free.dev" (overrides host/port);
               required for cloud/tunnel connections, where only StreamableHTTP works.
    """
    base = base_url.rstrip("/") if base_url else f"http://{host}:{port}"
    if transport == "sse":
        return SSEClient(base, mcp_version, timeout_s).connect()
    if transport in ("streamable-http", "http", "mcp"):
        return StreamableHTTPClient(base, mcp_version, timeout_s).connect()
    if transport != "auto":
        raise ValueError(f"unknown transport: {transport!r}")
    try:
        return StreamableHTTPClient(base, mcp_version, timeout_s).connect()
    except PiecesMCPError as http_err:
        try:
            return SSEClient(base, mcp_version, timeout_s).connect()
        except PiecesMCPError as sse_err:
            raise PiecesMCPError(
                "could not connect over either transport.\n"
                f"  StreamableHTTP: {http_err}\n  SSE: {sse_err}") from sse_err


def tool_result_text(resp: Dict[str, Any]) -> Optional[str]:
    """Extract concatenated text content from a tools/call response, if present."""
    result = resp.get("result")
    if not isinstance(result, dict):
        return None
    parts = [c.get("text", "") for c in result.get("content", []) if isinstance(c, dict)]
    return "\n".join(p for p in parts if p) or None
