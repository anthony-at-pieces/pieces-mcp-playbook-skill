# Changelog

All notable changes to the Pieces MCP Playbook skill are documented here.

## v3.0.0 (May 14, 2026)

### StreamableHTTP promoted as recommended transport

The `/model_context_protocol/2025-03-26/mcp` endpoint is now the primary recommended transport over SSE for all connections — local/LAN and cloud/remote. Short-lived HTTP requests release ephemeral ports immediately, avoiding the socket exhaustion risk inherent to long-lived SSE connections.

- New **Connectivity Mode 2: StreamableHTTP** section with the 3-step protocol flow (initialize, initialized notification, call tools)
- `MCP_ENDPOINTS.md` updated: StreamableHTTP listed as recommended for local/LAN, not just cloud/remote
- Frontmatter and descriptions updated to reflect both SSE and StreamableHTTP support

### Port/socket exhaustion: documented from real incident (May 11, 2026)

New troubleshooting section based on a confirmed incident. Root cause: a `netsh interface portproxy` rule forwarding port 39301 to 39334 for an RDP window was consuming sockets alongside multiple long-lived SSE connections, exhausting the Windows ephemeral port range. This was an environmental issue, not a Pieces regression.

- **Diagnosis commands:** `netstat -ano` for connection count, `netsh int ipv4 show dynamicport tcp` for port range, `netsh interface portproxy show all` for stale proxy rules
- **Fixes (in priority order):** clean stale proxy rules, widen dynamic port range (`start=10000 num=55535`), extend request timeout from 10 to 15 minutes, prefer StreamableHTTP, reuse SSE sessions
- Documented in both `SKILL.md` (troubleshooting item 6) and `TROUBLESHOOTING.md` (section 10)

### Pieces Docs MCP (Remote)

New section documenting the remote MCP server for querying official Pieces documentation. Separate from the local PiecesOS MCP server that serves LTM data.

- Endpoint: `https://docs.pieces.app/api/mcp`
- Tools: `search_docs`, `read_page`, `list_sections`, `get_started`
- Configuration JSON included for `mcpServers` setup

### Other improvements

- **SSE timeout from WSL** — new troubleshooting entry (section 12 in `TROUBLESHOOTING.md`): SSE long-lived connections are unreliable across the WSL-Windows NAT boundary; use StreamableHTTP instead
- **New reference file:** `CLOUD_CONNECTIVITY.md` for ngrok/tunnel setup, session management, and remote troubleshooting
- **Files section** in SKILL.md now includes "Additional MCP servers" subsection listing the Pieces Docs MCP

### Files changed

```
SKILL.md                          | +104 -10
references/MCP_ENDPOINTS.md       | +8 -2
references/TROUBLESHOOTING.md     | +53 -6
references/CLOUD_CONNECTIVITY.md  | new file
```

## v2.0.0 (May 8, 2026)

- Full Pieces MCP tool catalog (30 tools) across 4 categories
- Network binding documentation (127.0.0.1 only, portproxy setup)
- Verified against Pieces 12.3.11
- Batch snapshot tools, vector search tools, timestamp filter documentation
- Query and write-back playbooks

## v1.0.0 (April 2026)

- Initial release
- SSE connectivity and basic RPC script
- Core LTM tools: `ask_pieces_ltm`, `create_pieces_memory`
- Prerequisites and troubleshooting references
