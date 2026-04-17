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
- `scripts/pieces_mcp_scan.py`: scan for active MCP SSE endpoints.
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

- `http://localhost:39300/model_context_protocol/2024-11-05/sse`
- `http://localhost:39300/model_context_protocol/2024-11-05/messages`

Do not lock these in stone.

Match host, port, and protocol path to your actual Pieces server.

## Environment variables

- `PIECES_MCP_HOST` (default `127.0.0.1`)
- `PIECES_MCP_PORT` (default `39300`)
- `PIECES_MCP_VERSION` (default `2024-11-05`)
- `PIECES_MCP_CHAT_LLM` (optional)

## Query and write contract

- Retrieval target: `ask_pieces_ltm`.
- Optional write target: `create_pieces_memory`.
- Required payload field: `question`.
- Usually keep `chat_llm` set explicitly.
- Use optional controls only when needed:
  - `time_window`
  - `application_sources`
  - `topics`
  - `related_questions`
  - `connected_client`

## MCP host examples

### Local host (VS Code / Copilot)

```json
{
  "mcpServers": {
    "Pieces": {
      "url": "http://localhost:39300/model_context_protocol/2024-11-05/sse"
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
mcporter config add pieces http://<host>:<port>/model_context_protocol/<version>/sse --allow-http
mcporter list
mcporter call pieces.ask_pieces_ltm --args '{"question":"what did I work on?","chat_llm":"gemini-2.5-flash"}' --output json
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
- endpoints discoverable,
- tool list returns,
- ask/create calls execute where available.

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
  "time_window": "yesterday afternoon",
  "application_sources": ["Visual Studio Code", "Terminal", "Warp"],
  "topics": ["cache", "ttl", "race condition", "incident"]
}
```

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
  "summary": "Standup summary — 2026-01-01",
  "summary_description": "- Focused on cache TTL race in API path\n- Added jitter and singleflight guard\n- Added follow-up validation checks\n- Next: add regression coverage",
  "tags": ["standup", "cache", "api", "ABC-456"],
  "source_hint": "Derived from LTM retrieval via Pieces MCP"
}
```

## Troubleshooting

- Confirm PiecesOS and LTM are running.
- Confirm host, versioned path, and port.
- Confirm endpoint response with `pieces_mcp_scan.py`.
- Confirm tool surface with `pieces_mcp_rpc.py --list-tools`.
- Run `pieces_mcp_smoke_test.py` only after those checks pass.

## Optional low-level check

For SSE/Messages-level validation, open `/sse` and post JSON-RPC to `/messages`.

Use `references/MCP_ENDPOINTS.md` for command examples.

## Security and reliability

- Do not put secrets in payloads.
- Keep errors with context and no sensitive traces.
- Treat retrieval errors as recoverable state.
- Keep memory writes concise and structured.

## License

MIT (`LICENSE`).
