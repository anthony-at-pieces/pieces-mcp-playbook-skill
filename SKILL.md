---
name: pieces-mcp-playbook
description: Connect to the Pieces MCP server (StreamableHTTP or SSE) and interact with the full Pieces data plane -- LTM queries, targeted full-text and vector search across workstream events/summaries/conversations/annotations/tags/websites, batch snapshot retrieval, and memory creation. Also covers the remote Pieces Docs MCP for querying official documentation. 68 tools. Verified against Pieces 12.3.11.
license: MIT
compatibility: Any Agent Skills host that can call MCP tools and/or run local scripts; assumes PiecesOS exposes MCP on localhost or LAN (commonly port 39300). Both StreamableHTTP (/mcp) and SSE (/sse) endpoints supported. Also supports remote Pieces Docs MCP at docs.pieces.app.
metadata:
  author: Anthony Maio (anthony-at-pieces)
  version: "4.0"
  hermes:
    tags: [Pieces, MCP, LTM, StreamableHTTP, SSE, memory, workflow]
    related_skills: [native-mcp]
---

# Pieces MCP Playbook

Use this skill when you need to interact with **Pieces** through its **MCP server** -- whether that's querying Long-Term Memory (LTM), doing targeted searches across workstream events, conversations, annotations, tags, websites, or writing back curated memories.

Pieces MCP exposes **68 tools** (as of Pieces 12.3.11+) organized into six categories (see Tool Catalog below). The two highest-level tools (`ask_pieces_ltm` and `create_pieces_memory`) handle most use cases, but the granular search + batch snapshot tools give you precise control over what you retrieve.

## What this skill assumes

- PiecesOS is installed + running and LTM is enabled (see `references/PREREQS.md`).
- Your MCP host is pointed at a Pieces MCP URL. Three connectivity modes are supported:
  - **Local/LAN** (StreamableHTTP -- **preferred**): `http://<host>:39300/model_context_protocol/2025-03-26/mcp`. Uses short-lived HTTP requests, no ephemeral port exhaustion.
  - **Local/LAN** (SSE -- legacy): `.../2025-03-26/sse` (or `.../2024-11-05/sse` on older versions). Long-lived connection, avoid on port-constrained hosts.
  - **Cloud/remote** (MCP-only): `<tunnel-url>/.../mcp`. Use when PiecesOS is on a different network.
- **Network note (LAN):** Pieces MCP binds to **127.0.0.1 only**. If connecting from another machine on the same LAN (e.g., WSSL to your Pieces host), a Windows port proxy is required on the Pieces host:
  ```powershell
  netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=39300 connectaddress=127.0.0.1 connectport=39300
  ```
- **Network note (cloud):** Use an HTTPS tunnel (ngrok, Cloudflare Tunnel). The endpoint path is `/mcp` (not `/sse`). See `references/CLOUD_CONNECTIVITY.md`.

If you are unsure what tools exist: `python scripts/pieces_mcp_rpc.py --host <host> --mcp-version 2025-03-26 --list-tools`

---

## Connectivity Modes

### Mode 1: StreamableHTTP (recommended)

Same network setup as legacy SSE, but uses the `/mcp` endpoint with short-lived HTTP requests. No long-lived connections, no ephemeral port exhaustion. Sessions managed via `mcp-session-id` header.

**Protocol flow (3 steps + critical header):**
1. **Initialize** — POST with `method: "initialize"`, capture `mcp-session-id` from response headers. **Must include `Accept: application/json, text/event-stream`** on every request. Without it, the server returns HTTP 406 or JSON-RPC error -32000.
2. **Initialized notification** — POST with `method: "notifications/initialized"` using the session ID. (Some servers skip this step.)
3. **Call tools** — POST with `method: "tools/call"` using the session ID.

**Quick curl verification:**
```bash
# Step 1: Initialize (capture mcp-session-id from response header)
curl -s -D- -X POST "http://<host>:39300/model_context_protocol/2025-03-26/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":"1","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'

# Step 2: List tools with session ID
SESSION="<session-id-from-step-1>"
curl -s -X POST "http://<host>:39300/model_context_protocol/2025-03-26/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: $SESSION" \
  -d '{"jsonrpc":"2.0","id":"2","method":"tools/list","params":{}}'

# Step 3: Call a tool
curl -s -X POST "http://<host>:39300/model_context_protocol/2025-03-26/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: $SESSION" \
  -d '{"jsonrpc":"2.0","id":"3","method":"tools/call","params":{"name":"workstream_summaries_full_text_search","arguments":{"query":"test","limit":3}}}'
```

See `references/DIRECT_PYTHON_CLIENT.md` for the stdlib-only Python `urllib` pattern (recommended for `execute_code` blocks, cron jobs, and batch processing).

### Mode 2: SSE (legacy)
The `/sse` endpoint uses a long-lived Server-Sent Events connection. Works when your client only supports SSE, but each connection holds a TCP port open for its entire session lifetime. **Prefer StreamableHTTP** unless SSE is your only option.

### Mode 3: Cloud/Remote via HTTPS Tunnel
PiecesOS runs on a remote machine. HTTPS tunnel (ngrok, Cloudflare Tunnel, custom) exposes port 39300 over the public internet using `/mcp` (NOT `/sse`). See `references/CLOUD_CONNECTIVITY.md`.

```bash
# Quick ngrok setup on the PiecesOS machine
ngrok http 39300
# Use the forwarding URL:
# https://SOMETHING.ngrok-free.dev/model_context_protocol/2025-03-26/mcp
```

### Hermes Agent Configuration

```yaml
# ~/.hermes/config.yaml
mcp_servers:
  pieces:
    url: "http://<pieces-host>:39300/model_context_protocol/2025-03-26/mcp"
```

Test: `hermes mcp test pieces`
Reload: `/reload-mcp` (in-session slash command)

**Known false-negative warning:** `hermes mcp test pieces` may return **400 Bad Request** even when the Pieces MCP server is working. The runtime connection is fine — all 68 tools are available in agent sessions. Verify with a live session if unsure. The test command and the actual runtime connection use different header paths.

**Using tools natively from Hermes:**
Once connected, all Pieces tools are available as native Hermes tools prefixed with `mcp_pieces_*`:
```
mcp_pieces_ask_pieces_ltm(question="What did I work on yesterday?")
mcp_pieces_workstream_summaries_full_text_search(query="bug fix", limit=10)
```

For contexts where native MCP tools aren't available (cron jobs, batch `execute_code`), use the curl or Python urllib patterns in `references/DIRECT_PYTHON_CLIENT.md` and `references/pieces-mcp-curl-patterns.md`.

### Other Agent Hosts
For GitHub Copilot, Claude Desktop, Cursor, etc., see `references/PREREQS.md` and `references/MCP_ENDPOINTS.md`. The `mcporter` CLI (`mcporter config add pieces <url> --allow-http`) remains a viable bridge for setups without native MCP client support.

---

## Pieces Docs MCP (Remote)

Pieces publishes a **remote MCP server** for querying official documentation at `https://docs.pieces.app/api/mcp`. This is **separate** from the local PiecesOS MCP server (which serves LTM data).

**Available tools:** `search_docs`, `read_page`, `list_sections`, `get_started`. Use to look up the latest Pieces configuration instructions, verify current docs match this skill, or help users troubleshoot setup issues by searching docs for error messages.

---

## Core concepts (don't skip)

### 1) Retrieval is *not* the answer
Pieces MCP retrieval returns **context artifacts**, often as **JSON designed for an LLM to process**, not to show to a human verbatim. Your job is to:
1. Retrieve relevant artifacts
2. Summarize them into a user-facing answer
3. Optionally persist *curated* summaries back to memory

### 2) Start minimal, then constrain
Over-filtering is the most common cause of "no results" or poor results. The stable pattern is:
1. **Minimal query** (just the question)
2. **Add one constraint at a time** (time window → app sources → topics)
3. **Ask a follow-up query** based on what you saw returned

### 3) Summaries are shells
`workstream_summaries_full_text_search` returns summary metadata only. The actual narrative content lives in annotations (type=SUMMARY) — fetch via `annotations_batch_snapshot` with the annotation UUIDs from the `annotations.indices` field.

---

## Application Sources

Pieces captures activity across multiple channels, each surfaced via workstream events:
- **clipboard** — copy/paste operations with full text
- **vision** — screenshots with OCR text extraction
- **audio_output** — audio captures with transcription (meeting transcripts, voice notes)
- **browser** — URLs and page content from Chrome/Edge

Filter `ask_pieces_ltm` by `application_sources: ["Visual Studio Code", "Google Chrome", "Discord", ...]` to scope queries to specific apps.

---

## Tool Catalog (Pieces 12.3.11+ -- 68 tools)

Full catalog: `references/pieces-mcp-tools-catalog.md`. Summary below.

### Category 1: High-Level LTM Tools
| Tool | Required | Description |
|------|----------|-------------|
| `ask_pieces_ltm` | `question` | Semantic query across all LTM data. Optional but recommended: `chat_llm`, `topics[]`, `application_sources[]`, `open_files[]`, `related_questions[]`, `connected_client`. **Slower (~10-15s)** — embedding search. Use for natural language questions. |
| `create_pieces_memory` | `summary_description`, `summary` | Write a persistent memory (markdown). Optional: `files[]` (absolute paths), `externalLinks[]` (URLs), `project` (abs path), `connected_client` |
| `extract_temporal_range` | `query` | Convert "yesterday"/"last week" → ISO timestamps. **Picky**: rejects "the past month", accepts "yesterday". For reliable filtering, compute ISO dates in code. |

### Category 2: Full-Text Search Tools (fast, ~200ms)
Keyword-based search. Use **short, specific keywords** — not natural language phrases. Good: `"auth login"`, `"bug fix"`, `"meeting notes"`. Bad: `"What did I work on yesterday?"`. **Wildcards (`*`) do NOT work**.

All accept: `query` (required), `limit`, optional `created`/`updated` timestamp filters (`{from, to}` ISO 8601).

| Tool | Searches Over | Limit Max |
|------|---------------|-----------|
| `workstream_summaries_full_text_search` | AI-generated work session summaries | 100 |
| `conversations_full_text_search` | Copilot chat history | 50 |
| `conversation_messages_full_text_search` | Individual messages within conversations | -- |
| `annotations_full_text_search` | Notes, summaries, descriptions (filterable by `type`: SUMMARY, COMMENT, DESCRIPTION, etc.) | 200 |
| `assets_full_text_search` | Saved code snippets and documents | -- |
| `tags_full_text_search` | User-created labels | 100 |
| `workstream_events_full_text_search` | Raw activity (clipboard, screenshots/OCR, audio, app focus) | 100 |
| `connectors_full_text_search` | External service integrations (GCAL, GMAIL) | -- |
| `websites_full_text_search` | Saved URLs and metadata | 100 |
| `persons_full_text_search` | Identity records (email, name, username) | 100 |
| `wpe_sources_full_text_search` | Identified applications (readable name, bundle ID) | 100 |
| `wpe_source_windows_full_text_search` | Window contexts/titles | 100 |
| `models_full_text_search` | AI models: cloud + local | 100 |
| `entities_full_text_search` | Organizations and teams | 100 |
| `hints_full_text_search` | AI-generated follow-up questions | 100 |

### Category 3: Vector Search Tools (semantic, slower)
Embedding-based similarity. Same entity types as FTS but better for natural language queries:
`workstream_summaries_vector_search`, `conversations_vector_search`, `conversation_messages_vector_search`, `assets_vector_search`, `annotations_vector_search`, `tags_vector_search`, `workstream_events_vector_search`, `hints_vector_search`, `websites_vector_search`

### Category 4: Batch Snapshot Tools (detail retrieval)
Accept `identifiers[]` (1-100 UUIDs). Use after search to get complete records.
`workstream_summaries_batch_snapshot`, `conversations_batch_snapshot`, `annotations_batch_snapshot`, `persons_batch_snapshot`, `websites_batch_snapshot`, `tags_batch_snapshot`, `workstream_events_batch_snapshot`, `wpe_source_windows_batch_snapshot`, `wpe_sources_batch_snapshot`, `models_batch_snapshot`, `entities_batch_snapshot`, `ranges_batch_snapshot`, `hints_batch_snapshot`

### Category 5: Single-Entity Snapshot Tools
Same as batch but for a single UUID. Useful when you have exactly one ID.
`workstream_summary_snapshot`, `conversation_snapshot`, `conversation_message_snapshot`, `annotation_snapshot`, `asset_snapshot`, `person_snapshot`, `website_snapshot`, `tag_snapshot`, `workstream_event_snapshot`, `wpe_source_snapshot`, `wpe_source_window_snapshot`, `hint_snapshot`, `range_snapshot`

### Category 6: Connector Tools
`connectors_full_text_search` — Google Calendar/Gmail integration status (UNKNOWN/CONNECTED/DISCONNECTED/FAILED/REQUIRES_AUTHENTICATION).

---

## Recommended payload schemas

### ask_pieces_ltm
```json
{
  "question": "What did I work on yesterday?",
  "chat_llm": "gemini-2.5-flash",
  "topics": ["cache", "redis"],
  "application_sources": ["Visual Studio Code", "Google Chrome"],
  "related_questions": ["What debugging did I do?"],
  "open_files": ["/path/to/current/file.py"],
  "connected_client": "Hermes"
}
```
Only `question` is required. `chat_llm` is recommended but not strictly required. `application_sources` accepts specific app names.

### create_pieces_memory
```json
{
  "summary_description": "Short title (1-2 sentences)",
  "summary": "## Detailed markdown narrative\n- Background, thought process, what worked/failed\n- Code snippets, errors, references\n- Decisions and rationale",
  "files": ["/absolute/path/to/file.py"],
  "externalLinks": ["https://github.com/repo/pull/123"],
  "project": "/absolute/path/to/project",
  "connected_client": "Hermes"
}
```
Only `summary_description` and `summary` are required. `summary` should be markdown-formatted and as detailed as possible.

### Common search parameters (all search tools)
```json
{
  "query": "search terms",
  "limit": 10,
  "created": {
    "from": "2026-01-15T10:30:00Z",
    "to": "2026-01-20T10:30:00Z"
  },
  "updated": {
    "from": "2026-01-15T10:30:00Z"
  }
}
```
Timestamp filters are AND'd with the text query. `from` and `to` are each optional.

---

## The reliable workflow

### Step 0 — Choose your approach

**Quick question?** Use `ask_pieces_ltm` — searches across all data types semantically.

**Targeted retrieval?** Use the specific search tools:
- "What did I work on?" → `workstream_summaries_full_text_search`
- "What was I copying/pasting?" → `workstream_events_full_text_search`
- "What did I chat with the AI about?" → `conversations_full_text_search`
- "Find notes I made about X" → `annotations_full_text_search` (filter by type COMMENT)
- "What websites was I on?" → `websites_full_text_search`
- "What apps was I using?" → `wpe_sources_full_text_search`

**Need full details?** Search first to get UUIDs, then `*_batch_snapshot` to retrieve complete records.

**Broad activity scan (no specific keywords)?** Run multiple FTS queries with different domain keywords, combine and deduplicate:
`pieces`, `NAE`, `PR code`, `article writing`, `legal`, `meeting call`, `automation script`, `email discord`, `standup`

Or just use `ask_pieces_ltm` with a broad question.

### Step 1 — Search (minimal first)
```
# Quick LTM query
ask_pieces_ltm({ question: "What did I work on yesterday?", chat_llm: "gemini-2.5-flash" })

# Targeted keyword search
workstream_summaries_full_text_search({ query: "caching bug" })
```

### Step 2 — Validate the retrieval
Before you synthesize, verify:
- Are the returned items actually about the time range?
- Are they from the expected sources (IDE/terminal/browser)?
- Do you see the expected entities (repo name, filenames, issue id)?

If not, do **one** of:
- Broaden the time window or remove a filter
- Add a missing entity to `topics` or refine `query`
- Try a different search tool (e.g., `workstream_events` instead of `workstream_summaries`)
- Use vector search instead of full-text for semantic matching

### Step 3 — Batch snapshot (if needed)
```
workstream_summaries_batch_snapshot({ identifiers: ["uuid-1", "uuid-2", "uuid-3"] })
```

### Step 4 — Synthesize the answer (user-facing)
- Prefer **structured output** (bullets, headings) for "what did I do"
- Include **concrete artifacts**: filenames, commands, PR/issue ids, decisions
- Clearly mark **uncertainty** ("likely", "appears to") when the retrieval is thin

### Step 5 (optional) — Write back a curated memory
Only write back if it adds future value. Good write-backs:
- Daily standup summary
- Incident timeline + root cause
- Decision record + rationale
- "How I fixed it" runbook

```
create_pieces_memory({
  summary_description: "Standup summary -- 2026-01-01",
  summary: "## Standup\n- Main focus: caching bug in API layer\n- Changes: adjusted TTL handling and added logging\n- Next: add regression test for race condition\n- Links: PR #123, ticket ABC-456"
})
```

---

## Cron Job Patterns

For cron jobs querying Pieces MCP where native tools may not be pre-loaded:
- Use `enabled_toolsets: ["terminal", "web"]` in the cron job config
- In the cron prompt, inline the curl/python session init pattern or reference `references/DIRECT_PYTHON_CLIENT.md`
- Prefer the Python `execute_code` + `urllib` pattern for jobs needing multiple sequential MCP calls
- Each MCP session requires fresh `initialize` — sessions don't persist across cron runs

See `references/pieces-mcp-curl-patterns.md` for copy-paste bash patterns.

---

## Troubleshooting (fast path)

When something fails, do this in order:

1. **Confirm PiecesOS is running and LTM is enabled** (see `references/PREREQS.md`). An `ECONNRESET` is the likely symptom.

2. **Pieces MCP binds to 127.0.0.1 only**. If connecting from another machine on the LAN, you need a port proxy on the Pieces host:
   ```powershell
   # Elevated PowerShell on the Windows host running Pieces
   netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=39300 connectaddress=127.0.0.1 connectport=39300
   ```

3. **Confirm the endpoint URL** is correct, including the versioned path (`.../model_context_protocol/2025-03-26/mcp` for StreamableHTTP or `.../2025-03-26/sse` for SSE mode).

4. **List tools** via `hermes mcp list`, `mcporter list`, or `python scripts/pieces_mcp_rpc.py --list-tools`.

5. **Hermes MCP client fails but server is reachable.** If `hermes mcp test pieces` fails with 400 but the curl verification (above) succeeds, the runtime connection is actually fine — all 68 tools are available in sessions. This is a known false negative in the test command's header path. Verify:
   ```bash
   hermes mcp list  # should show pieces as enabled with tool count
   ```

6. **Cloud/tunnel connectivity issues:**
   - **Sanity check:** `curl -i "<tunnel-url>/.../mcp"` should return HTTP 400 with "mcp-session-id header or sessionId query parameter is required". This 400 is GOOD — it means the route exists.
   - **If 404/502/HTML/timeout:** The tunnel is down or PiecesOS is not running.
   - **If HTTP 500 on initialize:** Use file-based JSON (`--data-binary @file.json`), string JSON-RPC IDs (`"id": "1"` not `"id": 1`), and both `Content-Type` and `Accept` headers.
   - See `references/CLOUD_CONNECTIVITY.md` Section 9 for the full troubleshooting matrix.

7. **Port/socket exhaustion (real incident: May 11, 2026).** Each SSE connection holds a TCP port open for the session lifetime. Combined with `netsh` portproxy rules and multiple agent sessions, this can exhaust the Windows ephemeral port range. **Environment issue, not a Pieces regression.**
   - **Diagnose:** `netstat -ano | Select-String ":39300" | Measure-Object` and `netsh int ipv4 show dynamicport tcp`
   - **Fix stale proxies:** `netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=39301`
   - **Widen port range:** `netsh int ipv4 set dynamicport tcp start=10000 num=55535` (+ reboot)
   - **Prevent:** Prefer StreamableHTTP over SSE (releases ports immediately).

---

## Known Issues

- `extract_temporal_range` is picky about natural language — rejects "the past month" but accepts "yesterday" and "last week". Compute ISO timestamps in code for reliable filtering.
- `tags_full_text_search` with `"*"` returns 0 results — no wildcard support, use specific terms.
- FTS tools with empty or natural-language queries silently return no results — use short keywords.
- `ask_pieces_ltm` is slow (~10-15s per call). Use FTS for fast loops.
- `ask_pieces_ltm` can return large responses (27K+ chars) — truncate/parse before passing to another LLM call.
- Users' Pieces data may have zero tags — entirely keyword-search based.
- JSON-RPC `id` field — use integers, not strings. String IDs may misbehave on some servers.
- Response parsing: `result.content[].text` in MCP response contains JSON-encoded data — always `json.loads()` the text field.

---

## Files in this skill

### References (read when needed)
- `references/PREREQS.md` — enabling LTM + basic host setup
- `references/MCP_ENDPOINTS.md` — endpoints, message flow, and port discovery
- `references/CLOUD_CONNECTIVITY.md` — ngrok/tunnel setup, remote session management, troubleshooting
- `references/QUERY_PLAYBOOK.md` — query shaping patterns + examples
- `references/WRITE_PLAYBOOK.md` — write-back patterns + memory templates
- `references/TROUBLESHOOTING.md` — failure modes + how to surface actionable errors
- `references/VECTOR_SEARCH_WITH_COUCHDB.md` — how CouchDB-backed products handle vector search
- `references/DIRECT_PYTHON_CLIENT.md` — stdlib Python urllib pattern for StreamableHTTP calls
- `references/pieces-mcp-curl-patterns.md` — copy-paste bash curl patterns
- `references/pieces-mcp-tools-catalog.md` — full annotated catalog of all 68 tools with schemas

### Scripts (run when needed)
- `scripts/pieces_mcp_rpc.py` — list tools, call tools, capture raw responses
- `scripts/pieces_mcp_scan.py` — find a working Pieces MCP port on localhost
- `scripts/pieces_mcp_smoke_test.py` — end-to-end "list tools → retrieve → write" test

### Additional MCP servers
- **Pieces Docs MCP** — remote at `https://docs.pieces.app/api/mcp`. `search_docs`, `read_page`, `list_sections`, `get_started`.
