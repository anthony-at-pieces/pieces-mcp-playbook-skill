# Changelog

All notable changes to the Pieces MCP Playbook skill are documented here.

## v4.0.0 (July 11, 2026)

### Scripts rewritten: the SSE 400 "Missing sessionId query parameter" fix

The bundled scripts POSTed JSON-RPC to a hand-built `/messages` URL. Current PiecesOS builds require the POST URL delivered in the SSE `endpoint` event (it carries per-connection `sessionId` and `token` query parameters), so every script run failed with HTTP 400 "Missing sessionId query parameter". The docs had described the correct handshake since v2.0; the scripts never implemented it.

- **New `scripts/pieces_mcp_client.py`** -- shared stdlib-only client implementing both transports:
  - StreamableHTTP (`/mcp`, default): initialize -> capture `mcp-session-id` response header -> `notifications/initialized` -> requests
  - SSE (`/sse` + endpoint-event `/messages`, fallback): full endpoint-event handshake plus spec-correct initialize
- `pieces_mcp_rpc.py` and `pieces_mcp_smoke_test.py` now use the shared client; `--transport {auto,streamable-http,sse}` and `--url <tunnel-base>` flags added
- `pieces_mcp_scan.py` detects both transports per port and reports the PiecesOS version from `/.well-known/version`
- Smoke test is now read-only by default; `--ask` and `--write` opt into LTM retrieval and memory creation
- Windows cp1252 consoles no longer crash on non-ASCII tool descriptions (stdout switched to UTF-8)
- New env vars: `PIECES_MCP_TRANSPORT`, `PIECES_MCP_URL`

### JSON-RPC id asymmetry documented (verified on PiecesOS 12.5.0)

The SSE `/messages` endpoint requires integer ids; string ids fail with `-32700 Parse error`. The StreamableHTTP `/mcp` endpoint accepts both (strings recommended over tunnels). Documented in `MCP_ENDPOINTS.md` with a compatibility table; the client uses the right type per transport automatically.

### Tool catalog: 30 -> 69 tools (PiecesOS 12.5.0)

- New high-level tools: `search_memory` (the server's designated primary work-history tool), `ask_memory`, `get_user_persona`
- New categories: browser tools (`browser_activity`, `browser_lookup`), filesystem tools (`filesystem_search_paths`, `filesystem_search_text`, `filesystem_read_chunk`), Google Calendar (6 tools), utilities (`extract_temporal_range`, `time_compute`, `web_search`, `material_identifiers`)
- New singular `*_snapshot` tools (single `identifier`) alongside every `*_batch_snapshot`
- New search targets: anchors, connectors, conversation messages, materials (vector), signals (vector)
- Removed from the server: `models_full_text_search`, `entities_full_text_search`, `models_batch_snapshot`, `entities_batch_snapshot`

### Documentation corrections (verified against the live server)

- `ask_pieces_ltm`: only `question` is required; `chat_llm` is optional (was documented as required)
- `ask_pieces_ltm` has no `time_window` parameter; temporal patterns rewritten around `extract_temporal_range`, `created` filters, and `ask_memory` `time_ranges`
- `create_pieces_memory`: removed nonexistent `tags` and `source_hint` fields; fixed inverted `summary`/`summary_description` semantics in `WRITE_PLAYBOOK.md` and `README.md`
- StreamableHTTP initialize needs no client-generated session header; fixed `CLOUD_CONNECTIVITY.md` (also corrected `protocolVersion` from "0.1.0" to "2025-03-26")
- New troubleshooting entries for the `/messages` 400 and the string-id parse error

### Consolidation carried forward

This release supersedes the unreleased "4.0" frontmatter from the consolidation branch and keeps its additions:

- `references/DIRECT_PYTHON_CLIENT.md` (urllib StreamableHTTP pattern; now also points at `scripts/pieces_mcp_client.py`)
- `references/pieces-mcp-curl-patterns.md` (copy-pasteable curl flows)
- `references/pieces-mcp-tools-catalog.md` (regenerated from a live 12.5.0 `tools/list`; the earlier 68-tool version listed `assets_full_text_search`, which the live server does not expose)
- Hermes Agent configuration docs and the v3.1.0 Accept-header findings

## v3.1.0 (May 18, 2026)

### Hermes Agent configuration + StreamableHTTP Accept header fix

This release is based on live testing against the Pieces MCP server from Hermes Agent v0.13.0 running in WSL, connecting to PiecesOS on the Windows host over LAN.

- **Hermes Agent config section** -- new YAML config format for `~/.hermes/config.yaml` under `mcp_servers`, including commands for testing (`hermes mcp test pieces`) and reloading (`/reload-mcp`).
- **StreamableHTTP Accept header now documented prominently** -- the `Accept: application/json, text/event-stream` header is a HARD requirement on every POST to the `/mcp` endpoint. The server returns error -32000 "Not Acceptable" without it.
- **Hermes MCP client compatibility note (<= v0.13.0)** -- Hermes' native HTTP MCP client may fail to connect because it doesn't send the dual Accept header. Fixed after v0.13.0.
- **`chat_llm` corrected from required to optional** -- the live `ask_pieces_ltm` schema only requires `question`.
- **Outdated protocol version references fixed** -- `2024-11-05` updated to `2025-03-26` in remaining references.
- **Troubleshooting: new section 13** -- Hermes Agent MCP client failure diagnosis and fix steps.

## v3.0.0 (May 14, 2026)

### StreamableHTTP promoted as recommended transport

The `/model_context_protocol/2025-03-26/mcp` endpoint is now the primary recommended transport over SSE for all connections -- local/LAN and cloud/remote. Short-lived HTTP requests release ephemeral ports immediately, avoiding the socket exhaustion risk inherent to long-lived SSE connections.

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

- **SSE timeout from WSL** -- new troubleshooting entry (section 12 in `TROUBLESHOOTING.md`): SSE long-lived connections are unreliable across the WSL-Windows NAT boundary; use StreamableHTTP instead
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
