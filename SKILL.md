---
name: pieces-mcp-playbook
description: Connect to the Pieces MCP server (StreamableHTTP or SSE) and interact with the full Pieces data plane -- work-history retrieval via search_memory/ask_memory/ask_pieces_ltm, targeted full-text and vector search across workstream events/summaries/conversations/annotations/tags/websites, batch snapshot retrieval, browser history, filesystem search, Google Calendar, and memory creation. Also covers the remote Pieces Docs MCP for querying official documentation. Verified against PiecesOS 12.5.0 (69 tools).
license: MIT
compatibility: Any Agent Skills host that can call MCP tools and/or run local scripts; assumes PiecesOS exposes MCP on localhost or LAN (commonly port 39300) via StreamableHTTP or SSE endpoints. Also supports remote Pieces Docs MCP for documentation queries.
metadata:
  author: anthony-at-pieces
  version: "4.0.0"
  hermes:
    tags: [Pieces, MCP, LTM, StreamableHTTP, SSE, memory, workflow]
    related_skills: [native-mcp]
---

# Pieces MCP Playbook

Use this skill when you need to interact with **Pieces** through its **MCP server** -- whether that's querying Long-Term Memory (LTM), doing targeted searches across workstream events, conversations, annotations, tags, websites, browser history, or the local filesystem, managing Google Calendar events, or writing back curated memories.

Pieces MCP exposes **69 tools** organized into nine categories (see Tool Catalog below). The high-level memory tools (`search_memory`, `ask_memory`, `ask_pieces_ltm`, `create_pieces_memory`) handle most use cases, but the granular search + snapshot tools give you precise control over what you retrieve.

## What this skill assumes

- PiecesOS is installed + running and LTM is enabled (see `references/PREREQS.md`).
- Your MCP host is pointed at a Pieces MCP URL. Three connectivity modes are supported:
  - **Local/LAN (StreamableHTTP -- recommended):** `http://<host>:39300/model_context_protocol/2025-03-26/mcp`. Short-lived HTTP requests instead of long-lived SSE connections. Releases ephemeral ports immediately. Prefer this whenever your client supports it.
  - **Local/LAN (SSE -- legacy):** `http://<host>:39300/model_context_protocol/2025-03-26/sse` (the `2024-11-05` path also works). Requires the endpoint-event handshake described below.
  - **Cloud/remote (StreamableHTTP only, no SSE):** `<tunnel-url>/model_context_protocol/2025-03-26/mcp` -- use this when PiecesOS is on a different network, exposed via ngrok or any HTTPS tunnel. See `references/CLOUD_CONNECTIVITY.md` for full setup.
- **Network note (LAN):** Pieces MCP binds to **127.0.0.1 only**. If connecting from another machine on the same LAN, a Windows port proxy is required on the Pieces host:
  ```powershell
  netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=39300 connectaddress=127.0.0.1 connectport=39300
  ```
- **Network note (cloud):** If PiecesOS is on a different network entirely, use an HTTPS tunnel (ngrok, custom tunnel, any HTTPS proxy forwarding to localhost:39300). The endpoint path is `/mcp` (not `/sse`). See `references/CLOUD_CONNECTIVITY.md`.
- Your environment provides some way to call MCP tools -- either directly or via the included scripts.

If you are unsure what tools exist, run: `python scripts/pieces_mcp_rpc.py --list-tools`

---

## Connectivity Modes

### Mode 1: Local/LAN (StreamableHTTP -- recommended)
Uses the `/mcp` endpoint with short-lived HTTP requests. No long-lived SSE connections, so no ephemeral port exhaustion risk. Session management via the `mcp-session-id` header.

**Protocol flow (3 steps):**
1. **Initialize** -- POST with `method: "initialize"`. No session header is needed on this first request; the server assigns a session and returns it in the `mcp-session-id` response header.
2. **Initialized notification** -- POST with `method: "notifications/initialized"` and the `mcp-session-id` header. Returns HTTP 202.
3. **Call tools** -- POST `tools/list` / `tools/call` requests with the `mcp-session-id` header.

Every request must send both headers: `Content-Type: application/json` and `Accept: application/json, text/event-stream`. The Accept header is a HARD requirement -- without it the server returns HTTP 406 or JSON-RPC error -32000 "Not Acceptable".

### Mode 2: Local/LAN (SSE -- legacy)
PiecesOS and the MCP client are on the same network (or same machine). Uses the `/sse` endpoint plus a companion `/messages` endpoint.

**Protocol flow -- the endpoint event is mandatory:**
1. **Open the SSE stream** (GET `/sse` with `Accept: text/event-stream`). The server's first event is `endpoint`; its data is the POST URL, including per-connection `sessionId` and `token` query parameters.
2. **POST JSON-RPC requests to that exact URL.** Never hand-build a `/messages` URL -- a bare POST without the query parameters returns HTTP 400 `"Missing sessionId query parameter"`.
3. **Read responses from the SSE stream.** The POST itself returns only "Message processed".

**JSON-RPC id quirk (verified on 12.5.0):** the SSE `/messages` endpoint requires **integer** ids. String ids (`"id": "1"`) are rejected with `-32700 Parse error`. The StreamableHTTP `/mcp` endpoint accepts both (string ids are recommended over tunnels).

### Mode 3: Cloud/Remote via HTTPS Tunnel (StreamableHTTP only)
PiecesOS runs on a remote machine (different network). An HTTPS tunnel (ngrok, Cloudflare Tunnel, etc.) exposes port 39300. The client connects over the public internet using the `/mcp` endpoint (NOT `/sse`).

**Key distinction:** `/mcp` is a request/response JSON-RPC endpoint. `/sse` requires a long-lived Server-Sent Events connection which does not tunnel well through HTTPS proxies. Always use `/mcp` for cloud/remote connections.

**Quick ngrok setup on the PiecesOS machine:**
```bash
ngrok http 39300
```
Then use the forwarding URL: `https://SOMETHING.ngrok-free.dev/model_context_protocol/2025-03-26/mcp`

For full cloud setup instructions, session management, and troubleshooting, see `references/CLOUD_CONNECTIVITY.md`.

### Hermes Agent Configuration

```yaml
# ~/.hermes/config.yaml
mcp_servers:
  pieces:
    url: "http://<pieces-host>:39300/model_context_protocol/2025-03-26/mcp"
```

Test: `hermes mcp test pieces`
Reload: `/reload-mcp` (in-session slash command)

**Known false-negative warning:** `hermes mcp test pieces` may return **400 Bad Request** even when the Pieces MCP server is working. The runtime connection is fine -- all 69 tools are available in agent sessions. Verify with a live session if unsure. The test command and the actual runtime connection use different header paths.

**Using tools natively from Hermes:**
Once connected, all Pieces tools are available as native Hermes tools prefixed with `mcp_pieces_*`:
```
mcp_pieces_ask_pieces_ltm(question="What did I work on yesterday?")
mcp_pieces_workstream_summaries_full_text_search(query="bug fix", limit=10)
```

For contexts where native MCP tools aren't available (cron jobs, batch `execute_code`), use the curl or Python urllib patterns in `references/DIRECT_PYTHON_CLIENT.md` and `references/pieces-mcp-curl-patterns.md`, or import `scripts/pieces_mcp_client.py`.

### Other Agent Hosts
For GitHub Copilot, Claude Desktop, Cursor, etc., see `references/PREREQS.md` and `references/MCP_ENDPOINTS.md`. The `mcporter` CLI (`mcporter config add pieces <url> --allow-http`) remains a viable bridge for setups without native MCP client support.

---

## Pieces Docs MCP (Remote)

Pieces publishes a **remote MCP server** for querying official documentation. This is separate from the local PiecesOS MCP server (which serves LTM data). Use it to look up setup guides, feature docs, and troubleshooting steps from docs.pieces.app.

### Configuration

```json
{
  "mcpServers": {
    "Pieces Docs": {
      "url": "https://docs.pieces.app/api/mcp",
      "headers": {}
    }
  }
}
```

### Available tools

- **`search_docs`** -- keyword search across all documentation. Input: `{"query": "..."}`.
- **`read_page`** -- read full content of a specific docs page. Input: `{"path": "/products/mcp"}`.
- **`list_sections`** -- list all documentation sections and their pages.
- **`get_started`** -- quickstart info for new Pieces users.

### When to use it

- To look up the latest Pieces MCP configuration instructions (endpoint URLs, port discovery, supported transports).
- To verify current docs match what this skill documents (the skill may lag behind product changes).
- To help users troubleshoot setup issues by searching docs for error messages or feature names.

---

## Core concepts (don't skip)

### 1) Retrieval is *not* the answer
Pieces MCP retrieval returns **context artifacts**, often as **JSON designed for an LLM to process**, not to show to a human verbatim. Your job is to:
1. retrieve relevant artifacts
2. summarize them into a user-facing answer
3. optionally persist *curated* summaries back to memory

### 2) Start minimal, then constrain
Over-filtering is a common cause of "no results" or poor results. The most stable pattern is:

1. **Minimal query** (just the question)
2. **Add one constraint at a time** (time window -> app sources -> topics)
3. **Ask a follow-up query** based on what you saw returned

### 3) Summaries are shells
Workstream summaries are SHELL data structures -- metadata plus references to annotations. The actual narrative content lives in the associated annotations. When a summary looks thin, hydrate its annotations (via `annotations_batch_snapshot`) to get the real text.

---

## Tool Catalog (PiecesOS 12.5.0 -- 69 tools)

### Category 1: High-Level Memory Tools (5)
These are the primary tools for most workflows.

| Tool | Required Params | Description |
|------|----------------|-------------|
| `search_memory` | (none) | **The primary tool for work-history questions.** Retrieves ranked evidence from the LTM memory graph. Filters: `persons[]` (any person name or email goes HERE, never in hints), `hints[]` (non-person topical keywords, 1-3 words each), `sources[]` (action keywords or exact app names), `modalities[]` (clipboard, audio, vision, browser, google_calendar), `created`/`updated` ranges, `cursor`/`page_size` pagination, `mode` (standard or lean) |
| `ask_memory` | (none, but always pass `question` + `time_ranges`) | LTM question answering with explicit UTC `time_ranges[]` filters (the description marks them REQUIRED -- always derive at least one range from the user's query). Also: `topics[]`, `application_sources[]`, `open_files[]`, `chat_llm`, `related_questions[]`, `cursor`, `page_size` |
| `ask_pieces_ltm` | `question` | Semantic query across all LTM data (workstream events + summaries). Optional: `chat_llm` (fits returned context to the model's token limit), `topics[]`, `application_sources[]`, `open_files[]`, `related_questions[]` |
| `create_pieces_memory` | `summary_description`, `summary` | Write a never-forgotten memory. `summary_description` = short title (1-2 sentences); `summary` = detailed markdown narrative. Optional: `files[]` (absolute paths), `externalLinks[]` (URLs), `project` (absolute path), `connected_client` |
| `get_user_persona` | (none) | AI-generated hierarchical profile of the user: role, expertise, preferences, communication style |

### Category 2: Full-Text Search Tools (13)
Targeted keyword search across specific Pieces data types. Each accepts `query` (required), `limit`, and optional `created`/`updated` timestamp filters (`{from, to}` in ISO 8601). Results include UUIDs for snapshot retrieval.

| Tool | Searches Over |
|------|--------------|
| `workstream_summaries_full_text_search` | AI-generated work session summaries (shells; hydrate annotations for narrative) |
| `workstream_events_full_text_search` | Lowest-level captures (~every 2 seconds): clipboard, screenshots/OCR, audio transcriptions, app focus |
| `conversations_full_text_search` | Copilot chat history (messages, summaries, annotations) |
| `conversation_messages_full_text_search` | Individual messages within Copilot conversations |
| `annotations_full_text_search` | The primary TEXT CONTENT layer: notes, summaries, descriptions, comments. Filterable by `annotation_type` |
| `anchors_full_text_search` | Codebase reference points (named bookmarks linking to file paths) |
| `connectors_full_text_search` | External service integrations (GCAL, GMAIL) and their connection status |
| `tags_full_text_search` | User-created labels for organizing content |
| `persons_full_text_search` | Contacts by email, name, username |
| `websites_full_text_search` | Saved URLs and their metadata |
| `wpe_source_windows_full_text_search` | Window contexts (app window titles) extracted during event aggregation |
| `wpe_sources_full_text_search` | Identified applications (readable name, bundle ID, filter status) |
| `hints_full_text_search` | AI-generated suggested follow-up questions |

### Category 3: Vector Search Tools (6)
Semantic/embedding-based search. Same interface as full-text (`query` required) but matches meaning instead of keywords.

| Tool | Searches Over | Notes |
|------|--------------|-------|
| `workstream_summaries_vector_search` | Workstream summaries | |
| `workstream_events_vector_search` | Raw activity events | |
| `materials_vector_search` | Saved materials/snippets | Also requires `material_type` |
| `signals_vector_search` | Real-time notifications and event triggers | |
| `tags_vector_search` | Tags | |
| `hints_vector_search` | AI follow-up suggestions | |

### Category 4: Batch Snapshot Tools (15)
Retrieve full details by UUID. Accept `identifiers[]` (1-100 UUIDs). Return found items + `missing_ids` list. Use after search tools to get complete records.

`anchor_points_batch_snapshot`, `anchors_batch_snapshot`, `annotations_batch_snapshot`, `connectors_batch_snapshot`, `conversation_messages_batch_snapshot`, `conversations_batch_snapshot`, `hints_batch_snapshot`, `persons_batch_snapshot`, `ranges_batch_snapshot`, `tags_batch_snapshot`, `websites_batch_snapshot`, `workstream_events_batch_snapshot`, `workstream_summaries_batch_snapshot`, `wpe_source_windows_batch_snapshot`, `wpe_sources_batch_snapshot`

### Category 5: Single Snapshot Tools (15)
Same as batch snapshots but for one record: each takes `identifier` (a single UUID). One exists for every batch type:

`anchor_point_snapshot`, `anchor_snapshot`, `annotation_snapshot`, `connector_snapshot`, `conversation_message_snapshot`, `conversation_snapshot`, `hint_snapshot`, `person_snapshot`, `range_snapshot`, `tag_snapshot`, `website_snapshot`, `workstream_event_snapshot`, `workstream_summary_snapshot`, `wpe_source_snapshot`, `wpe_source_window_snapshot`

### Category 6: Browser Tools (2)

| Tool | Required Params | Description |
|------|----------------|-------------|
| `browser_activity` | (none) | Browser activity over a time range: history, engagement metadata, search terms, downloads, bookmarks. Supports Chrome, Chromium, Brave, Firefox, Safari (macOS), Edge (Windows) |
| `browser_lookup` | `query` | URL/topic match: fans out across history, search terms, bookmarks, favicons in parallel with fuzzy matching |

### Category 7: Filesystem Tools (3)

| Tool | Required Params | Description |
|------|----------------|-------------|
| `filesystem_search_paths` | `query` | Fuzzy path matching: finds files from partial, garbled, or OCR-mangled names |
| `filesystem_search_text` | `pattern` | grep-style content search (literal or regex) with context lines; respects .gitignore |
| `filesystem_read_chunk` | `path` | Paginated file reading at a byte offset for files too large for one response |

### Category 8: Google Calendar Tools (6)
Require a connected Google Calendar connector (check with `list_gcal_connectors`).

| Tool | Required Params | Description |
|------|----------------|-------------|
| `list_gcal_connectors` | (none) | List connected Google Calendar accounts |
| `get_gcal_events` | `time_min`, `time_max` | Fetch events in a time range (title, times, location, attendees, organizer) |
| `get_gcal_event` | `event_id` | Fetch one event |
| `create_gcal_event` | (none) | Create an event |
| `patch_gcal_event` | `event_id` | Update an event |
| `delete_gcal_event` | `event_id` | Delete an event |

### Category 9: Utility Tools (4)

| Tool | Required Params | Description |
|------|----------------|-------------|
| `extract_temporal_range` | `query` | Convert natural language ("yesterday", "last week") into precise UTC timestamp ranges. Use before time-filtered searches |
| `time_compute` | `operation` | Deterministic time utility: now, parse, add/subtract, convert |
| `web_search` | `query` | AI-powered web search (Perplexity) with source citations |
| `material_identifiers` | `material_type` | Filter-based listing of material UUIDs (no search query) |

### Removed tools
`models_full_text_search`, `entities_full_text_search`, `models_batch_snapshot`, and `entities_batch_snapshot` existed in Pieces 12.3.x but are no longer exposed as of 12.5.0. Do not call them.

### Common search parameters (all search tools)

```json
{
  "query": "search terms (required)",
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

Timestamp filters are AND'd with the text query. `from` and `to` are each optional. Use `extract_temporal_range` to turn phrases like "yesterday afternoon" into these UTC ranges.

---

## Recommended payload schemas

### search_memory payload (primary work-history tool)
```json
{
  "persons": ["Jane Smith"],
  "hints": ["caching", "redis", "api layer"],
  "sources": ["Visual Studio Code", "meeting"],
  "modalities": ["clipboard", "vision"],
  "created": { "from": "2026-01-15T00:00:00Z", "to": "2026-01-16T00:00:00Z" },
  "mode": "standard"
}
```
All fields optional. Person names/emails go in `persons` only -- never in `hints`.

### ask_pieces_ltm payload
```json
{
  "question": "What did I work on yesterday?",
  "chat_llm": "gemini-2.5-flash",
  "topics": ["cache", "redis"],
  "application_sources": ["Visual Studio Code", "Google Chrome"],
  "related_questions": ["What debugging did I do?"]
}
```
Only `question` is required. `chat_llm` is optional but recommended -- it lets Pieces fit the returned context to your model's token limit.

### create_pieces_memory payload
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
Only `summary_description` and `summary` are required. `summary` should be markdown-formatted and as detailed as possible. There is no `tags` parameter -- weave key terms into the summary text instead so search can find them.

---

## The reliable workflow

### Step 0 -- Choose your approach

**Work-history question?** Start with `search_memory` -- it is the server's designated primary tool for "what did I work on", "who did I talk to", and time-range questions.

**Quick semantic question?** Use `ask_pieces_ltm` (or `ask_memory` with explicit time ranges).

**Targeted retrieval?** Use the specific search tools for precision:
- "What did I work on?" -> `workstream_summaries_full_text_search` (then hydrate annotations)
- "What was I copying/pasting?" -> `workstream_events_full_text_search`
- "What did I chat with the AI about?" -> `conversations_full_text_search`
- "Find notes I made about X" -> `annotations_full_text_search`
- "What websites was I on?" -> `browser_lookup` or `websites_full_text_search`
- "What apps was I using?" -> `wpe_sources_full_text_search`
- "Where is that file?" -> `filesystem_search_paths`
- "What is on my calendar?" -> `get_gcal_events`

**Need full details?** Search first to get UUIDs, then `*_batch_snapshot` (or the singular `*_snapshot`) to retrieve complete records.

**Time-scoped anything?** Run `extract_temporal_range` first to convert the user's phrasing into UTC ranges, then pass them as `created` filters.

### Step 1 -- Search (minimal first)
Start with a minimal query, add filters only if results are too broad.

```
# Work-history query
search_memory({ hints: ["caching bug"] })

# Quick LTM query
ask_pieces_ltm({ question: "What did I work on yesterday?" })

# Targeted search
workstream_summaries_full_text_search({ query: "caching bug" })
```

### Step 2 -- Validate the retrieval (sanity checks)
Before you synthesize, verify:
- Are the returned items actually about the time range?
- Are they from the expected sources (IDE/terminal/browser)?
- Do you see the expected entities (repo name, filenames, issue id)?

If not, do **one** of:
- broaden the time window or remove a filter
- add a missing entity to `hints`/`topics` or refine `query`
- try a different search tool (e.g., `workstream_events` instead of `workstream_summaries`)
- use vector search instead of full-text for semantic matching

### Step 3 -- Snapshot (if needed)
If search returned UUIDs and you need full details:

```
workstream_summaries_batch_snapshot({ identifiers: ["uuid-1", "uuid-2", "uuid-3"] })
```

### Step 4 -- Synthesize the answer (user-facing)
Rules:
- Prefer **structured output** (bullets, headings) for "what did I do"
- Include **concrete artifacts**: filenames, commands, PR/issue ids, decisions
- Clearly mark **uncertainty** ("likely", "appears to") when the retrieval is thin

### Step 5 (optional) -- Write back a curated memory
Only write back if it adds future value. Good write-backs:
- daily standup summary
- incident timeline + root cause
- decision record + rationale
- "how I fixed it" runbook

```
create_pieces_memory({
  summary_description: "Standup summary -- 2026-01-01",
  summary: "## Standup\n- Main focus: caching bug in API layer\n- Changes: adjusted TTL handling and added logging\n- Next: add regression test for race condition\n- Links: PR #123, ticket ABC-456"
})
```

---

## Troubleshooting (fast path)

When something fails, do this in order:

1. **Confirm PiecesOS is running and LTM is enabled** (see `references/PREREQS.md`). If you get an `ECONNRESET`, this is the likely culprit. Check `http://localhost:39300/.well-known/version` -- it returns the PiecesOS version as plain text.
2. **HTTP 400 "Missing sessionId query parameter" on POST to /messages** -- you are POSTing to a hand-built `/messages` URL. The SSE transport requires you to open `/sse` first and POST to the exact URL delivered in the `endpoint` event (it carries per-connection `sessionId` and `token` query parameters). The bundled scripts (v4.0.0+) do this automatically; older script versions did not and always fail with this error on current PiecesOS builds.
3. **HTTP 400 -32700 "Parse error" on POST to /messages** -- you are sending string JSON-RPC ids over SSE. The SSE endpoint requires integer ids (`"id": 1`, not `"id": "1"`).
4. **Pieces MCP binds to 127.0.0.1 only** (not 0.0.0.0). If connecting from another machine on the LAN, you need a port proxy on the Pieces host:
    ```powershell
    # Elevated PowerShell on the Windows host running Pieces
    netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=39300 connectaddress=127.0.0.1 connectport=39300
    ```
    Then `mcporter config add pieces http://<lan-ip>:39300/model_context_protocol/2025-03-26/mcp --allow-http` will work. Without the portproxy, only localhost connections succeed.
5. **Confirm the URL** is correct, including the versioned path (`.../model_context_protocol/2025-03-26/mcp` or `.../sse`). Run `python scripts/pieces_mcp_scan.py` to discover live endpoints and the PiecesOS version.
6. **List tools** via `hermes mcp list`, `mcporter list`, or `python scripts/pieces_mcp_rpc.py --list-tools`.
7. **Hermes MCP client fails but server is reachable.** If `hermes mcp test pieces` fails with 400 but the curl verification succeeds, the runtime connection is actually fine -- all 69 tools are available in sessions. This is a known false negative in the test command's header path. Verify with `hermes mcp list` (should show pieces as enabled with a tool count). See `references/TROUBLESHOOTING.md` section 13.
8. **Cloud/tunnel connectivity issues** -- if connecting via ngrok or another HTTPS tunnel:
    - **Sanity check:** `curl -i "<tunnel-url>/model_context_protocol/2025-03-26/mcp"` should return HTTP 400 with a session-related error. This 400 is GOOD -- it means the route exists and the MCP server is alive.
    - **If you get 404/502/HTML/timeout:** The tunnel is down or PiecesOS is not running. Ask the human to restart both.
    - **If you get HTTP 500 on initialize:** Ensure you're using file-based JSON (`--data-binary @file.json`), string JSON-RPC IDs (`"id": "1"`), and both `Content-Type: application/json` and `Accept: application/json, text/event-stream` headers.
    - **If tools seem missing:** Confirm the MCP URL uses `/mcp` not `/sse`. For MCPorter/mcp-remote setups, ensure `mcp-remote` is installed and the gateway was restarted after config changes.
    - See `references/CLOUD_CONNECTIVITY.md` Section 9 for the full troubleshooting matrix.
9. **Port/socket exhaustion (real incident: May 11, 2026).** Each SSE connection to the Pieces MCP server holds a TCP port open for the entire session lifetime. If you are also running `netsh interface portproxy` rules (e.g., forwarding a port for RDP), those proxies consume additional sockets. Combined with multiple SSE-based agent sessions, this can exhaust the Windows ephemeral port range. This is an **environmental issue, not a Pieces regression**.

    **Symptoms:** `connect ECONNREFUSED` despite PiecesOS running, persistent disconnects from Pieces OS and Claude Desktop, new connections failing while existing ones still work.

    **Diagnosis (run from PowerShell):**
    ```powershell
    # Check how many connections to the MCP port are open
    netstat -ano | Select-String ":39300" | Measure-Object
    # Check the dynamic port range
    netsh int ipv4 show dynamicport tcp
    # List all portproxy rules (look for stale ones)
    netsh interface portproxy show all
    ```

    **Fixes (in priority order):**
    ```powershell
    # 1. Remove any portproxy rules you no longer need
    netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=39301
    # 2. Widen the dynamic port range (elevated PowerShell; reboot to take full effect)
    netsh int ipv4 set dynamicport tcp start=10000 num=55535
    ```
    Then: extend request timeouts (10 -> 15 minutes), **prefer StreamableHTTP over SSE** (releases ports immediately), and reuse sessions rather than opening a new SSE connection per tool call.

This skill includes known failure patterns reported publicly (e.g., retrieval tool failing while memory creation works) to help you design graceful degradation. See `references/TROUBLESHOOTING.md`.

---

## Files in this skill

### References (read when needed)
- `references/PREREQS.md` -- enabling LTM + basic host setup
- `references/MCP_ENDPOINTS.md` -- endpoints, message flow, transport quirks, and port discovery
- `references/CLOUD_CONNECTIVITY.md` -- ngrok/tunnel setup, MCP-only endpoint, session management, and remote troubleshooting
- `references/QUERY_PLAYBOOK.md` -- query shaping patterns + examples
- `references/WRITE_PLAYBOOK.md` -- write-back patterns + memory templates
- `references/TROUBLESHOOTING.md` -- failure modes + how to surface actionable errors
- `references/DIRECT_PYTHON_CLIENT.md` -- minimal urllib StreamableHTTP pattern for `execute_code`/cron contexts
- `references/pieces-mcp-curl-patterns.md` -- copy-pasteable curl flows for the `/mcp` endpoint
- `references/pieces-mcp-tools-catalog.md` -- the full tool catalog as a standalone reference
- `references/VECTOR_SEARCH_WITH_COUCHDB.md` -- how a CouchDB-backed product usually handles vector search

### Scripts (run when needed)
- `scripts/pieces_mcp_client.py` -- shared MCP client library (StreamableHTTP + SSE transports); import it for custom tooling
- `scripts/pieces_mcp_scan.py` -- find a working Pieces MCP port and report both transport URLs + PiecesOS version
- `scripts/pieces_mcp_rpc.py` -- list tools, call tools, and capture raw responses over either transport
- `scripts/pieces_mcp_smoke_test.py` -- connectivity + tools/list check; `--ask` and `--write` flags exercise retrieval and memory creation

### Additional MCP servers
- **Pieces Docs MCP** -- remote MCP at `https://docs.pieces.app/api/mcp`. Provides `search_docs`, `read_page`, `list_sections`, `get_started`. Use for documentation lookup, not LTM queries.
