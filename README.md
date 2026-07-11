# Pieces MCP Playbook

This skill is the field manual for working with Pieces Long-Term Memory (LTM) through the Pieces MCP endpoint.

It is opinionated on purpose.

You ask cleanly.
You check scope.
You refine.
You write back only if it is reusable.

That is the full loop.

## What this repository gives you

- `SKILL.md`: the skill contract and behavior constraints.
- `references/PREREQS.md`: Pieces setup and host prerequisites.
- `references/MCP_ENDPOINTS.md`: MCP endpoint shape and low-level flow.
- `references/QUERY_PLAYBOOK.md`: retrieval shaping and quality checks.
- `references/WRITE_PLAYBOOK.md`: memory write template and policy.
- `references/TROUBLESHOOTING.md`: failure modes and practical fixes.
- `references/VECTOR_SEARCH_WITH_COUCHDB.md`: optional vector-search context.
- `scripts/pieces_mcp_client.py`: shared MCP client library (StreamableHTTP + SSE).
- `scripts/pieces_mcp_scan.py`: scan for active MCP endpoints (both transports).
- `scripts/pieces_mcp_rpc.py`: call MCP tools from shell.
- `scripts/pieces_mcp_smoke_test.py`: quick end-to-end validation.

## Install and register

### Local install

- Put the repo in a path your agent host can read.
- Point your MCP client at the local endpoint below.
- If you run a Codex-style skills host, place under:
- Windows: `%USERPROFILE%\.codex\skills\pieces-mcp-playbook`
- Linux/macOS: `~/.codex/skills/pieces-mcp-playbook`
- Restart the host so it reloads skills.

### Prerequisites

- Pieces Desktop App running.
- PiecesOS running.
- LTM enabled.
- Python 3.8+.
- Network path to the MCP endpoint.

## MCP defaults

Most setups use:

- `http://localhost:39300/model_context_protocol/2025-03-26/mcp` (StreamableHTTP, recommended)
- `http://localhost:39300/model_context_protocol/2025-03-26/sse` (SSE, legacy)

Do not lock these in stone.

Match host, port, and protocol path to your actual Pieces server. Run `python scripts/pieces_mcp_scan.py` to discover both.

## Environment variables

- `PIECES_MCP_HOST` (default `127.0.0.1`)
- `PIECES_MCP_PORT` (default `39300`)
- `PIECES_MCP_VERSION` (default `2025-03-26`)
- `PIECES_MCP_TRANSPORT` (`auto`, `streamable-http`, or `sse`; default `auto`)
- `PIECES_MCP_URL` (full base URL, e.g. an ngrok tunnel; overrides host/port)
- `PIECES_MCP_CHAT_LLM` (optional)

## Query and write contract

- Primary work-history retrieval: `search_memory` (graph-based; persons/hints/sources filters).
- Semantic retrieval: `ask_pieces_ltm` (required field: `question`).
- Optional write target: `create_pieces_memory`.
- `chat_llm` is optional but recommended on `ask_pieces_ltm` (fits context to your model).
- Use optional controls only when needed:
  - `application_sources`
  - `topics`
  - `related_questions`
  - `open_files`

## MCP host examples

### Local host (VS Code / Copilot)

```json
{
  "mcpServers": {
    "Pieces": {
      "url": "http://localhost:39300/model_context_protocol/2025-03-26/mcp"
    }
  }
}
```

## Remote host usage and `mcporter`

If MCP is on another host, set:

- `PIECES_MCP_HOST` to the target host
- `PIECES_MCP_PORT` to the target port
- `PIECES_MCP_VERSION` to the server path version

Then lock down transport with SSH tunnel or VPN. Do not expose MCP publicly.

If `mcporter` is in your toolchain, register before calling tools:

```bash
mcporter config add pieces http://<host>:<port>/model_context_protocol/2025-03-26/mcp --allow-http
mcporter list
mcporter call pieces.ask_pieces_ltm --args '{"question":"what did I work on?"}' --output json
```

If discovery still stalls:

```bash
python scripts/pieces_mcp_scan.py --host <host> --port <port>
python scripts/pieces_mcp_rpc.py --host <host> --port <port> --list-tools
```

## Run sequence

### 1) Install smoke check

Run from the folder that contains this README:

```bash
python scripts/pieces_mcp_scan.py
python scripts/pieces_mcp_rpc.py --list-tools
python scripts/pieces_mcp_smoke_test.py
```

Success means:
- endpoints discoverable (both transports reported),
- tool list returns (69 tools on PiecesOS 12.5.0).

The smoke test is read-only by default. To exercise retrieval and the write path:

```bash
python scripts/pieces_mcp_smoke_test.py --ask --write
```

`--ask` runs a real `ask_pieces_ltm` query (slow). `--write` creates an actual memory in your LTM.

### 2) Retrieval pattern

Start minimal:

```json
{
  "question": "What did I work on yesterday?"
}
```

Refine only when needed:

```json
{
  "question": "Summarize my debugging work on cache behavior yesterday afternoon.",
  "application_sources": ["Visual Studio Code", "Terminal", "Warp"],
  "topics": ["cache", "ttl", "race condition", "incident"]
}
```

Put the timeframe in the question text; there is no `time_window` parameter. For strict UTC bounds use `extract_temporal_range` plus `created` filters on the search tools (see `references/QUERY_PLAYBOOK.md`).

### 3) Validation rules

- Confirm returned artifacts match the requested time window and sources.
- Confirm topic anchors appear in returned context.
- If the signal is thin, rerun one tighter query and keep going.

### 4) Write-back (optional)

Only write back entries that future me will actually read:
- standups
- incident notes
- decision records
- runbook snippets

```json
{
  "summary_description": "Standup summary -- 2026-01-01",
  "summary": "## Standup 2026-01-01\n- Focused on cache TTL race in API path (ABC-456)\n- Added jitter and singleflight guard\n- Added follow-up validation checks\n- Next: add regression coverage"
}
```

Note the field semantics: `summary_description` is the short title, `summary` is the detailed markdown body. There is no `tags` field; put key terms in the summary text.

## Troubleshooting

- Confirm PiecesOS and LTM are running.
- Confirm host, versioned path, and port.
- Confirm endpoint response with `pieces_mcp_scan.py`.
- Confirm tool surface with `pieces_mcp_rpc.py --list-tools`.
- Run `pieces_mcp_smoke_test.py` only after those checks pass.

## Optional low-level check

For SSE/Messages-level validation, open `/sse`, capture the `endpoint` event (it carries the per-connection sessionId and token), and post JSON-RPC to that exact URL with integer ids. Never post to a hand-built `/messages` path -- it returns HTTP 400.

Use `references/MCP_ENDPOINTS.md` for command examples on both transports.

## Security and reliability

- Do not put secrets in payloads.
- Keep errors with context and no sensitive traces.
- Treat retrieval errors as recoverable state.
- Keep memory writes concise and structured.

## License

MIT (`LICENSE`).
