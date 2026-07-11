# Troubleshooting Pieces MCP (practical + failure-mode oriented)

This file is designed to help you get from "it failed" to an actionable bug report or a reliable fallback.

## 1) Connection problems (can't reach MCP)

Symptoms:
- MCP host says "cannot connect"
- your requests hang / time out

Checklist:
1. Ensure **PiecesOS is running** and **LTM is enabled** (see `PREREQS.md`). Quick check: `curl http://localhost:39300/.well-known/version` returns the version as plain text.
2. If you have the Pieces CLI installed, you can also run `pieces mcp status` or `pieces mcp repair` to check and auto-fix MCP setup for supported platforms.
3. Confirm the **URL** is correct, including the versioned path (`.../model_context_protocol/2025-03-26/mcp` recommended, or `.../sse`).
4. Avoid **multiple Pieces MCP instances** across apps at the same time (some clients can interfere).
5. Run:
   - `python scripts/pieces_mcp_scan.py`
   - `python scripts/pieces_mcp_rpc.py --list-tools`

## 1a) HTTP 400 "Missing sessionId query parameter" on POST to /messages

Exact symptom:
```
POST failed: HTTPError: HTTP Error 400: Bad Request
{"jsonrpc":"2.0","error":{"code":-32602,"message":"Missing sessionId query parameter"},"id":null}
```

Root cause: the client POSTed to a hand-built `/messages` URL. The SSE transport requires you to:
1. Open the `/sse` stream first.
2. Read the server's `endpoint` event -- its data is the POST URL, including per-connection `sessionId` and `token` query parameters.
3. POST to that exact URL.

Current PiecesOS builds enforce this strictly; older builds tolerated bare `/messages` POSTs. The bundled scripts handle the handshake automatically as of skill v4.0.0 -- if you see this error, you are running pre-4.0 scripts or a custom client that skips the endpoint event. Alternatively, switch to the StreamableHTTP endpoint (`/mcp`), which has no endpoint-event handshake at all.

## 1b) HTTP 400 -32700 "Parse error" on POST to /messages

The SSE `/messages` endpoint requires **integer** JSON-RPC ids. String ids (`"id": "1"`) are rejected with `-32700 Parse error` (verified on PiecesOS 12.5.0). The StreamableHTTP `/mcp` endpoint accepts both; string ids are recommended there for tunnel compatibility. See the id table in `MCP_ENDPOINTS.md`.

## 2) Tool exists, but retrieval fails ("Failed to extract context")

There is a publicly reported failure mode where:
- `tools/list` works
- `create_pieces_memory` works
- but `ask_pieces_ltm` returns an error like "Failed to extract context"

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

## 3) "Workstream summary" generation fails (connection closed)

There is a reported failure mode during summary generation where the internal HTTP request fails with a connection closing before headers are received:
- https://github.com/pieces-app/support/issues/751

**Implications for your pipelines:**
- If you call a local endpoint that performs heavy synthesis, implement:
  - request timeouts
  - bounded payload sizes
  - retries with backoff
  - chunking (split a big request into smaller ones)
- Emit structured errors (HTTP status, endpoint, duration, payload size) so failures aren't silent.

## 4) Observability: make failures explain themselves

If you build an agent workflow around MCP tools, do not "swallow" tool failures.
Always record:
- tool name
- request payload (redact secrets)
- raw response / error text
- timing (start/end)
- host + port + MCP version path

This makes "it failed" reproducible.

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
2. **Wrong JSON-RPC ID type:** Use string `"id": "1"` over tunnels (integer ids have caused 500s on some setups; note the SSE transport is the opposite -- integers only)
3. **Missing headers:** Both `Content-Type: application/json` AND `Accept: application/json, text/event-stream` are required
4. **Stale session:** If a session expires, send a fresh `initialize` (no session header needed) and use the new server-assigned `mcp-session-id` from the response headers

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

## 10) Port/socket exhaustion from SSE connections + netsh port-proxy (real incident: May 11, 2026)

If you see `connect ECONNREFUSED` on the MCP port while PiecesOS is confirmed running, you may have exhausted the Windows ephemeral port range. This is an **environmental issue, not a Pieces regression**.

Each SSE connection holds a TCP port open for the session lifetime. If you are also running `netsh interface portproxy` rules (e.g., forwarding a port for RDP), those proxies consume additional sockets. Combined with multiple SSE-based agent sessions, this can exhaust the default Windows dynamic port range.

**Confirmed root cause:** A `netsh` port-proxy forwarding port `39301` to `39334` for an RDP window was consuming sockets alongside long-lived SSE connections. Each SSE session held a port open for its full lifetime, and the proxy rules added more. The default Windows dynamic port range was too narrow to sustain both.

**Check:**
```powershell
# Count connections to MCP port
netstat -ano | Select-String ":39300" | Measure-Object
# Show dynamic port range
netsh int ipv4 show dynamicport tcp
# List all portproxy rules (look for stale ones)
netsh interface portproxy show all
```

**Fixes:**
1. Clean up stale proxy rules: `netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=39301`
2. Widen the dynamic port range (elevated PowerShell): `netsh int ipv4 set dynamicport tcp start=10000 num=55535`
3. Extend request timeout from 10 to 15 minutes to reduce need for additional connections.
4. Prefer the StreamableHTTP endpoint (`/model_context_protocol/2025-03-26/mcp`) which releases ports after each response.
5. Reuse sessions instead of opening new SSE connections per call.

## 11) Pieces Docs MCP -- separate from local LTM server

The Pieces Docs MCP (`https://docs.pieces.app/api/mcp`) is a **remote server** for searching official documentation. It does NOT connect to your local PiecesOS instance or LTM data. If you need LTM workstream summaries, use the local MCP server at `localhost:39300`. If you need docs about Pieces features/setup, use the remote Docs MCP.

## 12) SSE endpoint timing out from WSL

When running from WSL2 in default NAT networking mode, the SSE endpoint (`/2024-11-05/sse`) may time out because long-lived connections are unreliable across the WSL-Windows network boundary. Use the StreamableHTTP endpoint (`/2025-03-26/mcp`) instead, which uses short-lived HTTP requests that are more tolerant of network latency.

## 13) Hermes Agent MCP client fails but server is reachable

If `hermes mcp test pieces` reports a connection failure but the curl verification flow succeeds (see SKILL.md StreamableHTTP section), the issue is in Hermes' HTTP MCP client, not the Pieces server.

**Symptoms:** Hermes MCP reload says pieces did not connect, but `curl` to the MCP endpoint works.

**Root cause (Hermes <= v0.13.0):** The native HTTP MCP client does not send `Accept: application/json, text/event-stream` as a request header. Pieces MCP requires this dual Accept header on every request and returns error -32000 "Not Acceptable" without it.

**Fix:**
1. Update Hermes: `hermes update` (fixed after v0.13.0)
2. Verify version: `hermes --version`
3. As a workaround, call Pieces MCP tools via curl or the scripts in this skill until the update
