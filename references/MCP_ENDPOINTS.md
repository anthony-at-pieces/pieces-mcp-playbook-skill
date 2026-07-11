# Pieces MCP endpoints + message flow

Pieces MCP exposes three types of endpoint under a versioned MCP path: a StreamableHTTP JSON-RPC endpoint (recommended for all use, required for cloud/remote), an SSE stream (legacy), and the SSE stream's companion Messages endpoint.

Typical base URL (port can vary):
- Local: `http://127.0.0.1:39300`
- Cloud/remote: `https://<tunnel-host>` (e.g., `https://abc123.ngrok-free.dev`)

> **Binding note:** Pieces MCP binds to **127.0.0.1 only** (loopback). It does NOT listen on 0.0.0.0 or the LAN interface. To reach it from another machine, set up a Windows port proxy on the Pieces host:
> ```powershell
> # Elevated PowerShell on the Windows host
> netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=39300 connectaddress=127.0.0.1 connectport=39300
> ```
>
> For cross-network access (PiecesOS on a different network), use an HTTPS tunnel (ngrok, Cloudflare Tunnel, etc.) instead. See `references/CLOUD_CONNECTIVITY.md`.

## MCP protocol versions

PiecesOS (verified on 12.5.0) responds on both versioned paths:
- `2025-03-26` (preferred; the only path with the `/mcp` StreamableHTTP endpoint)
- `2024-11-05` (older, also works for `/sse` + `/messages`)

Note: the SSE server negotiates protocolVersion `2024-11-05` internally even when connected via the `/2025-03-26/sse` path. This is harmless.

Always check `/.well-known/version` to confirm the Pieces version if unsure.

## Endpoints

### StreamableHTTP endpoint (recommended; required for cloud/remote)
- `/model_context_protocol/2025-03-26/mcp`

A request/response JSON-RPC endpoint that does NOT use SSE. **Recommended over SSE for all connections** -- short-lived HTTP requests release ephemeral ports immediately, avoiding the port exhaustion risk of long-lived SSE connections.

**Session flow:**
1. POST an `initialize` request. No session header is needed on this first request.
2. Read the server-assigned `mcp-session-id` from the response headers (a 13-digit timestamp like `1783781966639`).
3. POST a `notifications/initialized` notification with that header (server replies HTTP 202).
4. POST `tools/list` / `tools/call` requests with that header. Responses come back directly in the HTTP response body (`application/json`, or SSE-framed `text/event-stream` on some builds -- accept both).

**Required headers for all requests:**
```
Content-Type: application/json
Accept: application/json, text/event-stream
mcp-session-id: <SESSION_ID>   (all requests after initialize)
```

A bare GET or session-less POST to `/mcp` returns HTTP 400 with a session-related JSON error. That 400 means the endpoint is alive -- it is the scanner's liveness signature.

### SSE stream (legacy; server -> client)
- `/model_context_protocol/2025-03-26/sse` (or `/2024-11-05/sse`)

The client opens a long-lived SSE connection (Accept: `text/event-stream`). The server's FIRST event is `endpoint`, containing the messages URL with a per-connection `sessionId` and `token`:

```
event: endpoint
data: /model_context_protocol/2025-03-26/messages?sessionId=1783781931469&token=AAABn1GwOc0...
```

**Important:** The sessionId + token are per-connection. You MUST open the SSE stream first, capture the messages endpoint from the `endpoint` event, then POST to that exact URL. POSTing to a hand-built `/messages` URL fails with HTTP 400 `"Missing sessionId query parameter"`. The response to your POST comes back on the SSE stream (the POST itself returns "Message processed").

### Messages (client -> server; SSE companion)
- `/model_context_protocol/2025-03-26/messages?sessionId=...&token=...`

The client sends JSON-RPC requests (e.g., `tools/list`, `tools/call`) to this endpoint using the URL from the SSE `endpoint` event.

### Version endpoint
- `/.well-known/version` -- returns the Pieces version as plain text (e.g., `12.5.0`)

## JSON-RPC id types (transport asymmetry, verified on 12.5.0)

| Transport | Integer ids (`"id": 1`) | String ids (`"id": "1"`) |
|-----------|------------------------|--------------------------|
| SSE `/messages` | Required | Rejected with `-32700 Parse error` |
| StreamableHTTP `/mcp` (local) | Works | Works |
| StreamableHTTP `/mcp` (via tunnel) | Has caused HTTP 500s on some setups | Recommended |

Rule of thumb: integers over SSE, strings over StreamableHTTP.

## Minimal curl flow (StreamableHTTP, debugging)

```bash
BASE="http://127.0.0.1:39300/model_context_protocol/2025-03-26/mcp"

# 1) initialize -- capture the mcp-session-id RESPONSE header
curl -si "$BASE" -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":"1","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"curl","version":"0"}}}' \
  | grep -i mcp-session-id

# 2) initialized notification (returns 202)
curl -s "$BASE" -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: <SESSION_ID>" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}'

# 3) list tools
curl -s "$BASE" -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: <SESSION_ID>" \
  -d '{"jsonrpc":"2.0","id":"2","method":"tools/list"}'
```

## Minimal curl flow (SSE, debugging)

1) Start the SSE listener (terminal A):

```bash
curl -s -N "http://127.0.0.1:39300/model_context_protocol/2025-03-26/sse" \
  -H "Accept: text/event-stream"
```

Capture the `data:` line of the `endpoint` event -- that's your messages URL (relative to the base).

2) Send a JSON-RPC request (terminal B), using the messages URL from step 1 verbatim. Integer ids only:

```bash
curl -s "http://127.0.0.1:39300/model_context_protocol/2025-03-26/messages?sessionId=XXX&token=YYY" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

You should see the response event show up in the SSE terminal (terminal A).

## Using the bundled scripts (recommended)

The scripts handle transport selection, the session handshake, and response capture automatically. They default to StreamableHTTP and fall back to SSE.

```bash
# Discover endpoints + PiecesOS version
python scripts/pieces_mcp_scan.py

# List all tools
python scripts/pieces_mcp_rpc.py --list-tools

# Call a specific tool
python scripts/pieces_mcp_rpc.py \
  --call-tool ask_pieces_ltm \
  --args '{"question":"What did I work on yesterday?"}'

# Full-text search
python scripts/pieces_mcp_rpc.py \
  --call-tool workstream_summaries_full_text_search \
  --args '{"query":"caching bug","limit":5}'

# Batch snapshot
python scripts/pieces_mcp_rpc.py \
  --call-tool workstream_summaries_batch_snapshot \
  --args '{"identifiers":["uuid-1","uuid-2"]}'

# Force a transport, or point at a remote tunnel
python scripts/pieces_mcp_rpc.py --transport sse --list-tools
python scripts/pieces_mcp_rpc.py --url https://abc123.ngrok-free.dev --list-tools
```

Environment variable overrides: `PIECES_MCP_HOST`, `PIECES_MCP_PORT`, `PIECES_MCP_VERSION`, `PIECES_MCP_TRANSPORT`, `PIECES_MCP_URL`.

## Port discovery
Most docs and issues reference port `39300`, but it can vary. Use:

```bash
python scripts/pieces_mcp_scan.py
```

to scan a small port range and find a responsive MCP server. It reports both transport URLs and the PiecesOS version for each hit.

## Hermes Agent config (YAML)

When using Hermes Agent, configure the Pieces MCP server in `~/.hermes/config.yaml` under `mcp_servers`:

```yaml
mcp_servers:
  pieces:
    url: "http://localhost:39300/model_context_protocol/2025-03-26/mcp"
```

For LAN connections (WSL -> Windows host), use the host's LAN IP or hostname. A `netsh` portproxy on the Windows host is required (see binding note above).

Test the connection:
```bash
hermes mcp test pieces
```

List all MCP servers:
```bash
hermes mcp list
```

**Known issue (Hermes <= v0.13.0):** The native HTTP MCP client may fail to connect because it doesn't send `Accept: application/json, text/event-stream`. The server is reachable and working -- verify with the curl flow above. Update Hermes with `hermes update` for the fix.
