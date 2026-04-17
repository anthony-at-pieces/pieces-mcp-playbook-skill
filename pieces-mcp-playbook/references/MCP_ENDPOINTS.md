# Pieces MCP endpoints + message flow

Pieces MCP commonly exposes an SSE endpoint and a messages endpoint under a versioned MCP path.

Typical base URL (port can vary):
- `http://127.0.0.1:39300`

## Endpoints

### SSE stream (server → client)
- `/model_context_protocol/2024-11-05/sse`

The client opens a long‑lived SSE connection (Accept: `text/event-stream`) and receives tool responses / events there.

### Messages (client → server)
- `/model_context_protocol/2024-11-05/messages`

The client sends JSON‑RPC requests (e.g., `tools/list`, `tools/call`) to this endpoint.

## Minimal curl flow (debugging)

1) Start the SSE listener (terminal A):

```bash
curl -N "http://localhost:39300/model_context_protocol/2024-11-05/sse"   -H "Accept: text/event-stream"
```

2) Send a JSON‑RPC request (terminal B):

```bash
curl -s "http://localhost:39300/model_context_protocol/2024-11-05/messages"   -H "Content-Type: application/json"   -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

You should see the response event show up in the SSE terminal.

## Tool discovery
Run:

```bash
python scripts/pieces_mcp_rpc.py --list-tools
```

This performs the same flow (opens SSE, sends `tools/list`, prints the tool list).

## Calling a tool
Example for `ask_pieces_ltm` (your tool schema may require additional arguments):

```bash
python scripts/pieces_mcp_rpc.py \
  --call-tool ask_pieces_ltm \
  --args '{"question":"What did I work on yesterday?"}'
```

## Versioned path
The `2024-11-05` segment is the MCP protocol version used by Pieces in published examples.
If Pieces changes this in the future, you’ll need to update the path accordingly in configs and scripts.

## Port discovery
Most docs and issues reference port `39300`, but it can vary. Use:

```bash
python scripts/pieces_mcp_scan.py
```

to scan a small port range and find a responsive MCP server.
