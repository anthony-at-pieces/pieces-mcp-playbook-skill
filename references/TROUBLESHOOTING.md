# Troubleshooting Pieces MCP (practical + failure-mode oriented)

This file is designed to help you get from “it failed” to an actionable bug report or a reliable fallback.

## 1) Connection problems (can’t reach MCP)

Symptoms:
- MCP host says “cannot connect”
- your requests hang / time out

Checklist:
1. Ensure **PiecesOS is running** and **LTM is enabled** (see `PREREQS.md`).
2. If you have the Pieces CLI installed, you can also run `pieces mcp status` or `pieces mcp repair` to check and auto-fix MCP setup for supported platforms.
2. Confirm the **SSE URL** is correct, including the versioned path (`.../model_context_protocol/2024-11-05/sse`).
3. Avoid **multiple Pieces MCP instances** across apps at the same time (some clients can interfere).
4. Run:
   - `python scripts/pieces_mcp_scan.py`
   - `python scripts/pieces_mcp_rpc.py --list-tools`

## 2) Tool exists, but retrieval fails (“Failed to extract context”)

There is a publicly reported failure mode where:
- `tools/list` works
- `create_pieces_memory` works
- but `ask_pieces_ltm` returns an error like “Failed to extract context”

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

## 3) “Workstream summary” generation fails (connection closed)

There is a reported failure mode during summary generation where the internal HTTP request fails with a connection closing before headers are received:
- https://github.com/pieces-app/support/issues/751

**Implications for your pipelines:**
- If you call a local endpoint that performs heavy synthesis, implement:
  - request timeouts
  - bounded payload sizes
  - retries with backoff
  - chunking (split a big request into smaller ones)
- Emit structured errors (HTTP status, endpoint, duration, payload size) so failures aren’t silent.

## 4) Observability: make failures explain themselves

If you build an agent workflow around MCP tools, do not “swallow” tool failures.
Always record:
- tool name
- request payload (redact secrets)
- raw response / error text
- timing (start/end)
- host + port + MCP version path

This makes “it failed” reproducible.

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


## 7) Cursor “red JSON blob” in MCP Settings (often harmless)
Pieces documents a Cursor UI quirk where MCP Settings may show a raw JSON payload or “unknown message ID” error even when tool calls work.
The chat pane is the source of truth if queries succeed.

Reference:
- https://docs.pieces.app/products/mcp/cursor
