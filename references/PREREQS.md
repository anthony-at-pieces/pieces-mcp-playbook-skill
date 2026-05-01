# Prerequisites for Pieces MCP usage

## 1) PiecesOS + Pieces Desktop App
- Install the **Pieces Desktop App** and ensure it is actively running.
- Ensure **PiecesOS** is running on the machine (it powers collection + local services).
- Enable **Long‑Term Memory (LTM‑2.7)**:
  - Open the PiecesOS **Quick Menu** (PiecesOS tray/menu bar icon on Windows or macOS)
  - Select **Enable Long‑Term Memory Engine**

Reference:
- https://docs.pieces.app/products/quick-guides/ltm-context

## 2) MCP host configuration (examples)

### Visual Studio Code / GitHub Copilot (Agent mode)
Your VS Code `settings.json` should include a Pieces MCP server entry such as:

```json
{
  "mcpServers": {
    "Pieces": {
      "url": "http://localhost:39300/model_context_protocol/2024-11-05/sse"
    }
  }
}
```

Notes:
- Copilot must be in **Agent** mode (not Ask) to use MCP tools.
- Don’t add the `ask_pieces_ltm` tool as “context”; Agent mode uses it automatically.

Reference:
- https://docs.pieces.app/products/mcp/github-copilot

### Claude Desktop
Pieces provides a setup path for Claude Desktop as well.

Reference:
- https://docs.pieces.app/products/mcp/claude-desktop

## 3) Port awareness
Most examples use `localhost:39300`, but your local port can vary depending on configuration.
If your host can’t connect, use `scripts/pieces_mcp_scan.py` to discover the port and confirm endpoints.


## 4) Suggested environment variables (for wrappers/scripts)

These scripts and many wrapper implementations look for:

- `PIECES_MCP_HOST` (default: 127.0.0.1)
- `PIECES_MCP_PORT` (default: 39300)
- `PIECES_MCP_VERSION` (default: 2024-11-05)
- `PIECES_MCP_CHAT_LLM` (optional; used by some `ask_pieces_ltm` schemas)

Example:

```bash
export PIECES_MCP_PORT=39300
export PIECES_MCP_VERSION=2024-11-05
```


## 5) Where to find the correct SSE URL (authoritative)
Pieces documents that you can find the current MCP SSE endpoint URL:
- in the Pieces Desktop App under **Settings → Model Context Protocol (MCP)**
- or in the PiecesOS Quick Menu

The URL is usually formatted like:
`http://localhost:{port_number}/model_context_protocol/{version}/sse`

Reference:
- https://docs.pieces.app/products/mcp/cursor
