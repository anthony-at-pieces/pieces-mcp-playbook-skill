# Troubleshooting Pieces MCP (practical + failure-mode oriented)

This file is designed to help you get from “it failed” to an actionable bug report or a reliable fallback.

## 1) Connection problems (can’t reach MCP)

Symptoms:
- MCP host says “cannot connect”
- your requests hang / time out

Checklist:
1. Ensure **PiecesOS is running** and **LTM is enabled** (see `PREREQS.md`).
2. If you have the Pieces CLI installed, you can also run `pieces mcp status` or `pieces mcp repair` to check and auto-fix MCP setup for supported platforms.
2. Confirm the **SSE URL** is correct, including the versioned path (`.../model_context_protocol/2024-11-05/sse`).
3. Avoid **multiple Pieces MCP instances** across apps at the same time (some clients can interfere).
4. Run:
   - `python scripts/pieces_mcp_scan.py`
   - `python scripts/pieces_mcp_rpc.py --list-tools`

## 2) Tool exists, but retrieval fails (“Failed to extract context”)

There is a publicly reported failure mode where:
- `tools/list` works
- `create_pieces_memory` works
- but `ask_pieces_ltm` returns an error like “Failed to extract context”

This exact pattern was captured in a GitHub support issue with reproduction steps and curl commands:
- https://github.com/pieces-app/support/issues/747

**How to design around this:**
- Treat retrieval as fallible and provide graceful degradation:
  - return partial results if any exist
  - suggest an alternate query strategy (time slicing, source slicing)
  - surface the raw error text + request payload in logs
- Add a health check step in your agent pipeline:
  - call `ask_pieces_ltm` with a trivial question
  - if it errors, skip deep research features that depend on it

## 3) “Workstream summary” generation fails (connection closed)

There is a reported failure mode during summary generation where the internal HTTP request fails with a connection closing before headers are received:
- https://github.com/pieces-app/support/issues/751

**Implications for your pipelines:**
- If you call a local endpoint that performs heavy synthesis, implement:
  - request timeouts
  - bounded payload sizes
  - retries with backoff
  - chunking (split a big request into smaller ones)
- Emit structured errors (HTTP status, endpoint, duration, payload size) so failures aren’t silent.

## 4) Observability: make failures explain themselves

If you build an agent workflow around MCP tools, do not “swallow” tool failures.
Always record:
- tool name
- request payload (redact secrets)
- raw response / error text
- timing (start/end)
- host + port + MCP version path

This makes “it failed” reproducible.

## 5) Minimal bug report template

When filing an issue (or logging internally), include:

- PiecesOS version
- OS + arch
- MCP URL used
- `tools/list` output (tool names only is fine)
- failing tool name + exact payload
- exact raw error response
- whether other tools work (e.g., create memory works but ask LTM fails)


## 6) Pieces CLI MCP commands (helpful for ops)
Pieces CLI documents MCP management commands such as:
- `pieces mcp setup`
- `pieces mcp list`
- `pieces mcp docs`
- `pieces mcp repair`
- `pieces mcp status`

Reference:
- https://docs.pieces.app/products/cli/copilot/chat


## 7) Cursor "red JSON blob" in MCP Settings (often harmless)
Pieces documents a Cursor UI quirk where MCP Settings may show a raw JSON payload or "unknown message ID" error even when tool calls work.
The chat pane is the source of truth if queries succeed.

Reference:
- https://docs.pieces.app/products/mcp/cursor

## 8) Cloud/tunnel connection failures (ngrok, HTTPS proxy)

When connecting to Pieces MCP over an HTTPS tunnel (ngrok, Cloudflare Tunnel, custom proxy), different failure modes apply:

### 8a) MCP URL sanity check fails (404/502/timeout)
`curl -i "<tunnel-url>/model_context_protocol/2025-03-26/mcp"` returns 404, 502, HTML, or times out.

**Fix:** The tunnel or PiecesOS is down. Ask the human to:
1. Confirm PiecesOS is running on the remote machine
2. Confirm the tunnel is still running (`ngrok http 39300` -- check the dashboard)
3. If ngrok was restarted, the URL changes -- get a fresh one
4. Rebuild the MCP URL and re-test

### 8b) Initialize returns HTTP 500 (Internal Server Error)
**Fix:** Check these common causes:
1. **Shell quoting issues:** Use file-based JSON (`--data-binary @init.json`) instead of inline `-d '{...}'`
2. **Wrong JSON-RPC ID type:** Use string `"id": "1"`, not integer `"id": 1`
3. **Missing headers:** Both `Content-Type: application/json` AND `Accept: application/json, text/event-stream` are required
4. **Stale session:** If re-initializing, use a fresh client session ID in the `mcp-session-id` header

### 8c) Tools seem missing or unresponsive after MCPorter config
**Fix:**
1. Confirm `mcp-remote` is installed: `npm list -g mcp-remote`
2. If missing: `npm install -g mcp-remote@0.1.38`
3. Confirm the MCP config uses `/mcp` not `/sse` for cloud connections
4. Restart the gateway after editing config
5. Test directly with curl (see `references/CLOUD_CONNECTIVITY.md`) to isolate whether the issue is the bridge or the tunnel

### 8d) ask_pieces_ltm timeouts or vague answers over tunnel
**Fix:** Same as local troubleshooting (narrow by time/topic), but also:
1. Test with direct curl to isolate MCPorter vs tunnel issues
2. Confirm the tunnel is still running (human-side)
3. Check for latency -- tunnel connections are slower than LAN

### 8e) Getting raw JSON instead of natural language
This is NOT a problem. Raw JSON responses (`summaries[]`, `events[]` arrays) are the expected format. The agent parses and synthesizes them for the human.

## 9) Tunnel URL changes (ngrok free tier)

ngrok free tier assigns a random URL each time it starts. If the agent loses connection to Pieces MCP:
1. The old tunnel URL is stale
2. Ask the human to check ngrok and paste the current forwarding URL
3. Update the MCP config and restart

For stable URLs, use ngrok's paid tier (static domains) or a custom tunnel/proxy.

## 10) Port exhaustion from many SSE connections

If you see `EADDRINUSE`, `connect ECONNREFUSED` on the MCP port while PiecesOS is confirmed running, you may have exhausted the Windows ephemeral port range.

Each SSE connection holds a TCP port open for the session lifetime. Agents that open a new connection per tool call (or run multiple concurrent instances) can hit this limit quickly.

**Check:**
```powershell
# Count connections to MCP port
netstat -ano | Select-String ":39300" | Measure-Object
# Show dynamic port range
netsh int ipv4 show dynamicport tcp
```

**Fixes:**
1. Prefer the StreamableHTTP endpoint (`/model_context_protocol/2025-03-26/mcp`) which releases ports after each response.
2. Widen the dynamic port range (elevated PowerShell): `netsh int ipv4 set dynamicport tcp start=10000 num=55535`
3. Reuse sessions instead of opening new SSE connections per call.

## 11) Pieces Docs MCP -- separate from local LTM server

The Pieces Docs MCP (`https://docs.pieces.app/api/mcp`) is a **remote server** for searching official documentation. It does NOT connect to your local PiecesOS instance or LTM data. If you need LTM workstream summaries, use the local MCP server at `localhost:39300`. If you need docs about Pieces features/setup, use the remote Docs MCP.

## 12) SSE endpoint timing out from WSL

When running from WSL2 in default NAT networking mode, the SSE endpoint (`/2024-11-05/sse`) may time out because long-lived connections are unreliable across the WSL-Windows network boundary. Use the StreamableHTTP endpoint (`/2025-03-26/mcp`) instead, which uses short-lived HTTP requests that are more tolerant of network latency.
