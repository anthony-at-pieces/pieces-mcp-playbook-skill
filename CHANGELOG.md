# Changelog

All notable changes to the Pieces MCP Playbook skill are documented here.

## v3.1.0 (May 18, 2026)

### Hermes Agent configuration + StreamableHTTP Accept header fix

This release is based on live testing against the Pieces MCP server from Hermes Agent v0.13.0 running in WSL, connecting to PiecesOS on Aurora (LAN).

- **Hermes Agent config section** — new YAML config format for `~/.hermes/config.yaml` under `mcp_servers`, including commands for testing (`hermes mcp test pieces`) and reloading (`/reload-mcp`).
- **StreamableHTTP Accept header now documented prominently** — the `Accept: application/json, text/event-stream` header is a HARD requirement on every POST to the `/mcp` endpoint. The server returns error -32000 "Not Acceptable" without it. Moved from buried cloud troubleshooting note to the main protocol flow with copy-pasteable curl verification.
- **Hermes MCP client compatibility note (<= v0.13.0)** — Hermes' native HTTP MCP client may fail to connect because it doesn't send the dual Accept header. Server is reachable and working — the issue is client-side. Fixed after v0.13.0.
- **`chat_llm` corrected from required to optional** — the live `ask_pieces_ltm` schema only requires `question`. `chat_llm` is optional but recommended.
- **Outdated protocol version references fixed** — `2024-11-05` updated to `2025-03-26` in remaining references.
- **Troubleshooting: new section 13** — Hermes Agent MCP client failure diagnosis and fix steps.
- **MCP_ENDPOINTS.md: Hermes config section added** — YAML format, WSL->LAN hostname usage, known client issue.

### Files changed

```
SKILL.md                         | +35 -5  (Hermes config, Accept header, chat_llm fix, protocol version)
references/MCP_ENDPOINTS.md      | +24 -0  (Hermes Agent config section)
references/TROUBLESHOOTING.md    | +15 -2  (section 13: Hermes client, protocol version fixes)
```

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
