# Pieces MCP endpoints + message flow

Pieces MCP exposes an SSE endpoint and a messages endpoint under a versioned MCP path.

Typical base URL (port can vary):
- `http://127.0.0.1:39300`

> **Binding note:** Pieces MCP binds to **127.0.0.1 only** (loopback). It does NOT listen on 0.0.0.0 or the LAN interface. To reach it from another machine (e.g., WSL -> Aurora), set up a Windows port proxy on the Pieces host:
> ```powershell
> # Elevated PowerShell on the Windows host
> netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=39300 connectaddress=127.0.0.1 connectport=39300
> ```

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
