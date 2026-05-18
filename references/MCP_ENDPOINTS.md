# Pieces MCP endpoints + message flow

Pieces MCP exposes three types of endpoint under a versioned MCP path: an SSE stream (for local/LAN use), a Messages endpoint (companion to SSE), and a direct JSON-RPC/StreamableHTTP endpoint (recommended for local/LAN and required for cloud/remote use via HTTPS tunnels).

Typical base URL (port can vary):
- Local: `http://127.0.0.1:39300`
- Cloud/remote: `https://<tunnel-host>` (e.g., `https://abc123.ngrok-free.dev`)

> **Binding note:** Pieces MCP binds to **127.0.0.1 only** (loopback). It does NOT listen on 0.0.0.0 or the LAN interface. To reach it from another machine (e.g., WSL -> Aurora), set up a Windows port proxy on the Pieces host:
> ```powershell
> # Elevated PowerShell on the Windows host
> netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=39300 connectaddress=127.0.0.1 connectport=39300
> ```
>
> For cross-network access (PiecesOS on a different network), use an HTTPS tunnel (ngrok, Cloudflare Tunnel, etc.) instead. See `references/CLOUD_CONNECTIVITY.md`.

## MCP protocol versions

Pieces 12.3.11 responds to both of these versioned paths:
- `2025-03-26` (confirmed working, preferred)
- `2024-11-05` (older, also works)

Always check `/.well-known/version` to confirm the Pieces version if unsure.

## Endpoints

### SSE stream (server -> client)
- `/model_context_protocol/2025-03-26/sse`

The client opens a long-lived SSE connection (Accept: `text/event-stream`). The server sends an `endpoint` event containing the messages URL with a `sessionId` and `token`:

```
event: endpoint
data: /model_context_protocol/2025-03-26/messages?sessionId=1777506843324&token=AAABndup-...
```

**Important:** The sessionId + token are per-connection. You MUST open the SSE stream first, capture the messages endpoint from the `endpoint` event, then POST to that URL. The response to your POST comes back on the SSE stream (the POST itself returns "Message processed").

### Messages (client -> server)
- `/model_context_protocol/2025-03-26/messages?sessionId=...&token=...`

The client sends JSON-RPC requests (e.g., `tools/list`, `tools/call`) to this endpoint using the sessionId from the SSE handshake.

### Version endpoint
- `/.well-known/version` -- returns the Pieces version as plain text (e.g., `12.3.11`)

### StreamableHTTP endpoint (recommended for local/LAN, required for cloud/remote)
- `/model_context_protocol/2025-03-26/mcp`

This is a direct JSON-RPC endpoint that does NOT use SSE. **Recommended over SSE for all connections** -- it uses short-lived HTTP requests that release ephemeral ports immediately, avoiding the port exhaustion risk of long-lived SSE connections. Use this for both local/LAN and cloud/remote connections.

For cloud/remote: Connect over an HTTPS tunnel (ngrok, Cloudflare Tunnel, custom proxy). The client sends JSON-RPC requests via POST and receives JSON-RPC responses directly -- no SSE handshake needed.

**Session management is required** -- the client must:
1. Send an `initialize` request with a client-generated session ID header
2. Extract the server-assigned `mcp-session-id` from the response headers (a 13-digit timestamp like `1774202062499`)
3. Use that server-assigned session ID for all subsequent requests

**Required headers for all requests:**
```
Content-Type: application/json
Accept: application/json, text/event-stream
mcp-session-id: <SESSION_ID>
```

See `references/CLOUD_CONNECTIVITY.md` for the full curl flow and session management details.

## Minimal curl flow (debugging)

1) Start the SSE listener (terminal A):

```bash
curl -s -N "http://192.168.86.34:39300/model_context_protocol/2025-03-26/sse" \
  -H "Accept: text/event-stream"
```

Capture the `data:` line -- that's your messages URL.

2) Send a JSON-RPC request (terminal B), using the messages URL from step 1:

```bash
curl -s "http://192.168.86.34:39300/model_context_protocol/2025-03-26/messages?sessionId=XXX&token=YYY" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

You should see the response event show up in the SSE terminal (terminal A).

## Using the RPC script (recommended)

The included script handles the SSE handshake + POST + response capture automatically:

```bash
# List all tools
python scripts/pieces_mcp_rpc.py --host 192.168.86.34 --mcp-version 2025-03-26 --list-tools

# Call a specific tool
python scripts/pieces_mcp_rpc.py --host 192.168.86.34 --mcp-version 2025-03-26 \
  --call-tool ask_pieces_ltm \
  --args '{"question":"What did I work on yesterday?","chat_llm":"gemini-2.5-flash"}'

# Full-text search
python scripts/pieces_mcp_rpc.py --host 192.168.86.34 --mcp-version 2025-03-26 \
  --call-tool workstream_summaries_full_text_search \
  --args '{"query":"caching bug","limit":5}'

# Batch snapshot
python scripts/pieces_mcp_rpc.py --host 192.168.86.34 --mcp-version 2025-03-26 \
  --call-tool workstream_summaries_batch_snapshot \
  --args '{"identifiers":["uuid-1","uuid-2"]}'
```

Environment variable overrides: `PIECES_MCP_HOST`, `PIECES_MCP_PORT`, `PIECES_MCP_VERSION`.

## Port discovery
Most docs and issues reference port `39300`, but it can vary. Use:

```bash
python scripts/pieces_mcp_scan.py
```

to scan a small port range and find a responsive MCP server.

## Hermes Agent config (YAML)

When using Hermes Agent, configure the Pieces MCP server in `~/.hermes/config.yaml` under `mcp_servers`:

```yaml
mcp_servers:
  pieces:
    url: "http://aurora:39300/model_context_protocol/2025-03-26/mcp"
```

For LAN connections (WSL -> Windows host), use the host's LAN IP or hostname (e.g., `aurora`, `192.168.86.34`). A `netsh` portproxy on the Windows host is required (see binding note above).

Test the connection:
```bash
hermes mcp test pieces
```

List all MCP servers:
```bash
hermes mcp list
```

**Known issue (Hermes <= v0.13.0):** The native HTTP MCP client may fail to connect because it doesn't send `Accept: application/json, text/event-stream`. The server is reachable and working — verify with the curl flow below. Update Hermes with `hermes update` for the fix.
