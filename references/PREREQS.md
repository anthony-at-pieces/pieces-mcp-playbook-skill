# Prerequisites for Pieces MCP usage

## 1) PiecesOS + Pieces Desktop App
- Install the **Pieces Desktop App** and ensure it is actively running.
- Ensure **PiecesOS** is running on the machine (it powers collection + local services).
- Enable **Long-Term Memory (LTM)**:
  - Open the PiecesOS **Quick Menu** (PiecesOS tray/menu bar icon on Windows or macOS)
  - Select **Enable Long-Term Memory Engine**

Reference:
- https://docs.pieces.app/products/quick-guides/ltm-context

## 2) MCP host configuration (examples)

### Visual Studio Code / GitHub Copilot (Agent mode)
Your VS Code `settings.json` should include a Pieces MCP server entry such as:

```json
{
  "mcpServers": {
    "Pieces": {
      "url": "http://localhost:39300/model_context_protocol/2025-03-26/mcp"
    }
  }
}
```

Notes:
- Prefer the `/mcp` (StreamableHTTP) endpoint; use `/sse` only if your client cannot speak StreamableHTTP.
- Copilot must be in **Agent** mode (not Ask) to use MCP tools.
- Don't add the `ask_pieces_ltm` tool as "context"; Agent mode uses it automatically.

Reference:
- https://docs.pieces.app/products/mcp/github-copilot

### Claude Desktop
Pieces provides a setup path for Claude Desktop as well.

Reference:
- https://docs.pieces.app/products/mcp/claude-desktop

## 3) Port awareness
Most examples use `localhost:39300`, but your local port can vary depending on configuration.
If your host can't connect, use `scripts/pieces_mcp_scan.py` to discover the port and confirm endpoints.

## 3a) Cloud/Remote connectivity (optional)

If PiecesOS is on a different network from the MCP client, you need an HTTPS tunnel:

### ngrok (most common)
1. Install ngrok: https://ngrok.com/download
2. Sign up and configure authtoken: `ngrok config add-authtoken <token>`
3. On the PiecesOS machine, start the tunnel:
   ```bash
   ngrok http 39300
   ```
4. Copy the forwarding URL (e.g., `https://abc123.ngrok-free.dev`)
5. The MCP endpoint is: `<forwarding-url>/model_context_protocol/2025-03-26/mcp`

### Other tunnel options
- **Cloudflare Tunnel:** `cloudflared tunnel --url http://localhost:39300`
- **Custom domain/proxy:** Any HTTPS proxy that forwards to `localhost:39300` on the PiecesOS machine

### mcp-remote (bridge for MCP clients)
If your MCP client (VS Code, Claude Desktop, etc.) needs a stdio-based bridge to the remote endpoint:

```bash
npm install -g mcp-remote@0.1.38
```

Then in your client's MCP config:
```json
{
  "mcpServers": {
    "pieces": {
      "command": "mcp-remote",
      "args": ["https://YOUR-TUNNEL/model_context_protocol/2025-03-26/mcp"]
    }
  }
}
```

`mcp-remote` handles session management (initialize, session-id extraction, headers) automatically. You do not need to manually manage sessions when using this bridge.

See `references/CLOUD_CONNECTIVITY.md` for the full setup guide.


## 4) Suggested environment variables (for wrappers/scripts)

These scripts and many wrapper implementations look for:

- `PIECES_MCP_HOST` (default: 127.0.0.1)
- `PIECES_MCP_PORT` (default: 39300)
- `PIECES_MCP_VERSION` (default: 2025-03-26)
- `PIECES_MCP_TRANSPORT` (`auto`, `streamable-http`, or `sse`; default: auto)
- `PIECES_MCP_URL` (full base URL such as an ngrok tunnel; overrides host/port)
- `PIECES_MCP_CHAT_LLM` (optional; passed to `ask_pieces_ltm`)

Example:

```bash
export PIECES_MCP_PORT=39300
export PIECES_MCP_VERSION=2025-03-26
```


## 5) Where to find the correct MCP URL (authoritative)
Pieces documents that you can find the current MCP endpoint URL:
- in the Pieces Desktop App under **Settings -> Model Context Protocol (MCP)**
- or in the PiecesOS Quick Menu

The URL is usually formatted like:
`http://localhost:{port_number}/model_context_protocol/{version}/mcp` (or `.../sse` for the legacy transport)

Reference:
- https://docs.pieces.app/products/mcp/cursor
