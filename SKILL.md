---
name: pieces-mcp-playbook
description: Connect to the Pieces MCP server (SSE or StreamableHTTP) and interact with the full Pieces data plane -- LTM queries, targeted full-text and vector search across workstream events/summaries/conversations/annotations/tags/websites, batch snapshot retrieval, and memory creation. Also covers the remote Pieces Docs MCP for querying official documentation. Verified against Pieces 12.3.11.
license: MIT
compatibility: Any Agent Skills host that can call MCP tools and/or run local scripts; assumes PiecesOS exposes MCP on localhost or LAN (commonly port 39300) via SSE or StreamableHTTP endpoints. Also supports remote Pieces Docs MCP for documentation queries.
metadata:
  author: anthony-demo
  version: "3.1"
---

# Pieces MCP Playbook

Use this skill when you need to interact with **Pieces** through its **MCP server** -- whether that's querying Long-Term Memory (LTM), doing targeted searches across workstream events, conversations, annotations, tags, websites, or writing back curated memories.

Pieces MCP exposes **30+ tools** organized into five categories (see Tool Catalog below). The two highest-level tools (`ask_pieces_ltm` and `create_pieces_memory`) handle most use cases, but the granular search + batch snapshot tools give you precise control over what you retrieve.

## What this skill assumes

- PiecesOS is installed + running and LTM is enabled (see `references/PREREQS.md`).
- Your MCP host is pointed at a Pieces MCP URL. Three connectivity modes are supported:
  - **Local/LAN** (SSE endpoint): `http://<host>:39300/model_context_protocol/2025-03-26/sse` (Pieces 12.3.11) or `.../2024-11-05/sse` (older versions).
  - **Local/LAN** (StreamableHTTP -- recommended over SSE): `http://<host>:39300/model_context_protocol/2025-03-26/mcp`. Uses short-lived HTTP requests instead of long-lived SSE connections. Releases ephemeral ports immediately. Prefer this when your client supports it.
  - **Cloud/remote** (MCP-only, no SSE): `<tunnel-url>/model_context_protocol/2025-03-26/mcp` -- use this when PiecesOS is on a different network, exposed via ngrok or any HTTPS tunnel. See `references/CLOUD_CONNECTIVITY.md` for full setup.
- **Network note (LAN):** Pieces MCP binds to **127.0.0.1 only**. If connecting from another machine on the same LAN (e.g., WSL to Aurora at 192.168.86.34), a Windows port proxy is required on the Pieces host:
  ```powershell
  netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=39300 connectaddress=127.0.0.1 connectport=39300
  ```
- **Network note (cloud):** If PiecesOS is on a different network entirely, use an HTTPS tunnel (ngrok, custom tunnel, any HTTPS proxy forwarding to localhost:39300). The endpoint path is `/mcp` (not `/sse`). See `references/CLOUD_CONNECTIVITY.md`.
- Your environment provides some way to call MCP tools -- either directly or via the included RPC script.

If you are unsure what tools exist, run: `python scripts/pieces_mcp_rpc.py --host <host> --mcp-version 2025-03-26 --list-tools`

---

## Connectivity Modes

### Mode 1: Local/LAN (SSE)
The default mode. PiecesOS and the MCP client are on the same network (or same machine). Uses the `/sse` endpoint. Covered by the existing workflow below.

### Mode 2: Local/LAN (StreamableHTTP -- recommended)
Same network setup as Mode 1, but uses the `/mcp` endpoint with short-lived HTTP requests. No long-lived SSE connections, so no ephemeral port exhaustion risk. Uses session management via `mcp-session-id` header. Prefer this over SSE when your client supports it.

**Protocol flow (3 steps + critical header):**
1. **Initialize** — POST with `method: "initialize"`, capture `mcp-session-id` from response headers. **Must include `Accept: application/json, text/event-stream`** on every request — the server rejects requests missing this header with error -32000 "Not Acceptable."
2. **Initialized notification** — POST with `method: "notifications/initialized"` using the session ID.
3. **Call tools** — POST with `method: "tools/call"` using the session ID.

**Quick curl verification (from WSL or any client):**
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

### Mode 3: Cloud/Remote via HTTPS Tunnel (MCP-only)
PiecesOS runs on a remote machine (different network). An HTTPS tunnel (ngrok, Cloudflare Tunnel, etc.) exposes port 39300. The client connects over the public internet using the `/mcp` endpoint (NOT `/sse`).

**Key distinction:** `/mcp` is a direct JSON-RPC endpoint. `/sse` requires a long-lived Server-Sent Events connection which does not tunnel well through HTTPS proxies. Always use `/mcp` for cloud/remote connections.

**Quick ngrok setup on the PiecesOS machine:**
```bash
ngrok http 39300
```
Then use the forwarding URL: `https://SOMETHING.ngrok-free.dev/model_context_protocol/2025-03-26/mcp`

For full cloud setup instructions, session management, and troubleshooting, see `references/CLOUD_CONNECTIVITY.md`.

### Hermes Agent Configuration

When using **Hermes Agent** (the AI agent framework by Nous Research), configure Pieces MCP in `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  pieces:
    url: "http://aurora:39300/model_context_protocol/2025-03-26/mcp"
```

**Known compatibility note (Hermes v0.13.0 and earlier):** Hermes' native HTTP MCP client may fail to connect to Pieces' StreamableHTTP endpoint because:
1. It may not send the required `Accept: application/json, text/event-stream` header (the server responds with error -32000 "Not Acceptable" without it).
2. Session management via `mcp-session-id` response header must be handled.

**If Hermes fails to connect**, the Pieces MCP server is likely working — verify independently with the curl flow above. If the curl flow succeeds, the issue is in the MCP client, not the server. Fixed in newer Hermes builds (check `hermes --version`).

**Test connection:**
```bash
hermes mcp test pieces
```

**Reload MCP servers after config changes:**
```bash
# In-session slash command
/reload-mcp
```

For other agent hosts (GitHub Copilot, Claude Desktop, Cursor), see `references/PREREQS.md` and `references/MCP_ENDPOINTS.md`.

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

- **`search_docs`** — keyword search across all documentation. Input: `{"query": "..."}`.
- **`read_page`** — read full content of a specific docs page. Input: `{"path": "/products/mcp"}`.
- **`list_sections`** — list all documentation sections and their pages.
- **`get_started`** — quickstart info for new Pieces users.

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
Over‑filtering is a common cause of “no results” or poor results. The most stable pattern is:

1. **Minimal query** (just the question)
2. **Add one constraint at a time** (time window → app sources → topics)
3. **Ask a follow‑up query** based on what you saw returned

---

## Tool Catalog (Pieces 12.3.11 -- 30 tools)

### Category 1: High-Level LTM Tools
These are the primary tools for most workflows. `ask_pieces_ltm` is a semantic query over all LTM data; `create_pieces_memory` writes curated memories.

| Tool | Required Params | Description |
|------|----------------|-------------|
| `ask_pieces_ltm` | `question` | Ask Pieces a question to retrieve historical/contextual info from the user's environment. Optional but recommended: `chat_llm`, `topics[]`, `application_sources[]`, `open_files[]`, `related_questions[]`, `connected_client` |
| `create_pieces_memory` | `summary_description`, `summary` | Write a never-forgotten memory. Optional: `files[]` (absolute paths), `externalLinks[]` (URLs), `project` (abs path), `connected_client` |

### Category 2: Full-Text Search Tools
Targeted search across specific Pieces data types. Each accepts `query` (required), `limit`, and optional `created`/`updated` timestamp filters (`{from, to}` in ISO 8601). Results include UUIDs for batch snapshot retrieval.

| Tool | Searches Over | Limit Range |
|------|--------------|-------------|
| `workstream_summaries_full_text_search` | AI-generated work session summaries (tasks, decisions, docs, next steps) | 1-100 |
| `conversations_full_text_search` | Copilot chat history (messages, summaries, annotations) | 1-50 |
| `annotations_full_text_search` | Notes, summaries, descriptions, comments. Filterable by `annotation_type`: SUMMARY, COMMENT, DESCRIPTION, DOCUMENTATION, EXPLANATION, GIT_COMMIT, KNOWLEDGE_GRAPH, and hierarchical summary types | 1-200 |
| `tags_full_text_search` | User-created labels for organizing content | 1-100 |
| `persons_full_text_search` | Contacts by email, name, username (6 fields) | 1-100 |
| `websites_full_text_search` | Saved URLs and their metadata | 1-100 |
| `workstream_events_full_text_search` | Raw activity captures: clipboard, screenshots/OCR, audio transcriptions, app focus changes | 1-100 |
| `wpe_source_windows_full_text_search` | Window contexts (app window titles) extracted during event aggregation | 1-100 |
| `wpe_sources_full_text_search` | Identified applications (readable name, bundle ID, filter status) | 1-100 |
| `models_full_text_search` | AI models: cloud (OpenAI, Anthropic, Google), local (Ollama), custom | 1-100 |
| `entities_full_text_search` | Organizations and teams | 1-100 |
| `hints_full_text_search` | AI-generated suggested follow-up questions | 1-100 |

### Category 3: Vector Search Tools
Semantic/embedding-based search. Same interface as full-text but uses vector similarity instead of exact text matching.

| Tool | Searches Over |
|------|--------------|
| `workstream_summaries_vector_search` | Workstream summaries |
| `workstream_events_vector_search` | Raw activity events |
| `tags_vector_search` | Tags |
| `hints_vector_search` | AI follow-up suggestions |

### Category 4: Batch Snapshot Tools
Retrieve full details by UUID. Accept `identifiers[]` (1-100 UUIDs). Return found items + `missing_ids` list. Use after search tools to get complete records.

| Tool | Retrieves |
|------|-----------|
| `workstream_summaries_batch_snapshot` | Summary name, description, annotations, application context |
| `conversations_batch_snapshot` | Full message history + annotations |
| `annotations_batch_snapshot` | Full annotation text, type, associations |
| `persons_batch_snapshot` | Email, name, username (platform + basic) |
| `websites_batch_snapshot` | URL, name, text content |
| `tags_batch_snapshot` | Tag text and metadata |
| `workstream_events_batch_snapshot` | Event type, clipboard/vision/audio content, app name, window title, URL |
| `wpe_source_windows_batch_snapshot` | Window name/title |
| `wpe_sources_batch_snapshot` | Readable app name, raw context, filter status |
| `models_batch_snapshot` | Model name, provider, foundation, usage type, cloud/local status |
| `entities_batch_snapshot` | Entity name, type (org/team), distribution model |
| `ranges_batch_snapshot` | Temporal ranges (from/to timestamps) |
| `hints_batch_snapshot` | Suggested question text, type, model reference |

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

Timestamp filters are AND'd with the text query. `from` and `to` are each optional.

---

## Recommended payload schemas

### ask_pieces_ltm payload
```json
{
  "question": "What did I work on yesterday?",
  "chat_llm": "gemini-2.5-flash",
  "topics": ["cache", "redis"],
  "application_sources": ["Visual Studio Code", "Google Chrome"],
  "related_questions": ["What debugging did I do?"],
  "connected_client": "Hermes"
}
```
Only `question` is required. `chat_llm` is optional but recommended for optimal context fitting. `application_sources` accepts specific app names from the Pieces source list.

### create_pieces_memory payload
```json
{
  "summary_description": "Short title (1-2 sentences)",
  "summary": "## Detailed markdown narrative\\n- Background, thought process, what worked/failed\\n- Code snippets, errors, references\\n- Decisions and rationale",
  "files": ["/absolute/path/to/file.py"],
  "externalLinks": ["https://github.com/repo/pull/123"],
  "project": "/absolute/path/to/project",
  "connected_client": "Hermes"
}
```
Only `summary_description` and `summary` are required. `summary` should be markdown-formatted and as detailed as possible.

---

## The reliable workflow

### Step 0 — Choose your approach

**Quick question?** Use `ask_pieces_ltm` -- it searches across all data types semantically.

**Targeted retrieval?** Use the specific search tools for precision:
- "What did I work on?" -> `workstream_summaries_full_text_search`
- "What was I copying/pasting?" -> `workstream_events_full_text_search`
- "What did I chat with the AI about?" -> `conversations_full_text_search`
- "Find notes I made about X" -> `annotations_full_text_search` (filter by type COMMENT)
- "What websites was I on?" -> `websites_full_text_search`
- "What apps was I using?" -> `wpe_sources_full_text_search`

**Need full details?** Search first to get UUIDs, then `*_batch_snapshot` to retrieve complete records.

### Step 1 — Search (minimal first)
Start with a minimal query, add filters only if results are too broad.

```
# Quick LTM query
ask_pieces_ltm({ question: "What did I work on yesterday?", chat_llm: "gemini-2.5-flash" })

# Targeted search
workstream_summaries_full_text_search({ query: "caching bug" })
```

### Step 2 — Validate the retrieval (sanity checks)
Before you synthesize, verify:
- Are the returned items actually about the time range?
- Are they from the expected sources (IDE/terminal/browser)?
- Do you see the expected entities (repo name, filenames, issue id)?

If not, do **one** of:
- broaden the time window or remove a filter
- add a missing entity to `topics` or refine `query`
- try a different search tool (e.g., `workstream_events` instead of `workstream_summaries`)
- use vector search instead of full-text for semantic matching

### Step 3 — Batch snapshot (if needed)
If search returned UUIDs and you need full details:

```
workstream_summaries_batch_snapshot({ identifiers: ["uuid-1", "uuid-2", "uuid-3"] })
```

### Step 4 — Synthesize the answer (user-facing)
Rules:
- Prefer **structured output** (bullets, headings) for "what did I do"
- Include **concrete artifacts**: filenames, commands, PR/issue ids, decisions
- Clearly mark **uncertainty** ("likely", "appears to") when the retrieval is thin

### Step 5 (optional) — Write back a curated memory
Only write back if it adds future value. Good write-backs:
- daily standup summary
- incident timeline + root cause
- decision record + rationale
- "how I fixed it" runbook

```
create_pieces_memory({
  summary_description: "Standup summary -- 2026-01-01",
  summary: "## Standup\\n- Main focus: caching bug in API layer\\n- Changes: adjusted TTL handling and added logging\\n- Next: add regression test for race condition\\n- Links: PR #123, ticket ABC-456"
})
```

---

## Troubleshooting (fast path)

When something fails, do this in order:

1.  **Confirm PiecesOS is running and LTM is enabled** (see `references/PREREQS.md`). If you get an `ECONNRESET`, this is the likely culprit.
2.  **Pieces MCP binds to 127.0.0.1 only** (not 0.0.0.0). If connecting from another machine on the LAN (e.g., WSL to Aurora at 192.168.86.34), you need a port proxy on the Pieces host:
    ```powershell
    # Elevated PowerShell on the Windows host running Pieces
    netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=39300 connectaddress=127.0.0.1 connectport=39300
    ```
    Then `mcporter config add pieces http://192.168.86.34:39300/model_context_protocol/2025-03-26/mcp --allow-http` will work. Without the portproxy, only localhost connections succeed.
3.  Confirm the **endpoint URL** is correct, including the versioned path (`.../model_context_protocol/2025-03-26/sse` for SSE mode or `.../model_context_protocol/2025-03-26/mcp` for StreamableHTTP mode).
4.  **List tools** via `mcporter list`, `hermes mcp list`, or `python scripts/pieces_mcp_rpc.py --list-tools`.

4b. **Hermes MCP client fails but server is reachable.** If `hermes mcp test pieces` fails but the curl verification (above) succeeds, the issue is likely:
    - Hermes' HTTP MCP client not sending the required `Accept: application/json, text/event-stream` header.
    - Verify with `hermes --version` — this was fixed after v0.13.0. Update with `hermes update`.
    - As a workaround, you can call Pieces MCP tools via the terminal using curl or the scripts in this skill.


This skill includes known failure patterns reported publicly (e.g., retrieval tool failing while memory creation works) to help you design graceful degradation.

5. **Cloud/tunnel connectivity issues** -- if connecting via ngrok or another HTTPS tunnel:
    - **Sanity check:** `curl -i "<tunnel-url>/model_context_protocol/2025-03-26/mcp"` should return HTTP 400 with `"mcp-session-id header or sessionId query parameter is required"`. This 400 is GOOD -- it means the route exists and the MCP server is alive.
    - **If you get 404/502/HTML/timeout:** The tunnel is down or PiecesOS is not running. Ask the human to restart both.
    - **If you get HTTP 500 on initialize:** Ensure you're using file-based JSON (`--data-binary @file.json`), string JSON-RPC IDs (`"id": "1"` not `"id": 1`), and both `Content-Type: application/json` and `Accept: application/json, text/event-stream` headers.
    - **If tools seem missing:** Confirm the MCP URL uses `/mcp` not `/sse`. For MCPorter/mcp-remote setups, ensure `mcp-remote` is installed (`npm install -g mcp-remote@0.1.38`) and the gateway was restarted after config changes.
    - See `references/CLOUD_CONNECTIVITY.md` Section 9 for the full troubleshooting matrix.

6. **Port/socket exhaustion (real incident: May 11, 2026).** Each SSE connection to the Pieces MCP server holds a TCP port open for the entire session lifetime. If you are also running `netsh interface portproxy` rules (e.g., forwarding a port for RDP), those proxies consume additional sockets. Combined with multiple SSE-based agent sessions, this can exhaust the Windows ephemeral port range. This is an **environmental issue, not a Pieces regression**.

    **Symptoms:** `connect ECONNREFUSED` despite PiecesOS running, persistent disconnects from Pieces OS and Claude Desktop, new connections failing while existing ones still work.

    **Root cause (confirmed):** A `netsh` port-proxy forwarding port `39301` to `39334` for an RDP window was consuming sockets alongside long-lived SSE connections. Each SSE session held a port open for its full lifetime, and the proxy rules added more. The default Windows dynamic port range was too narrow to sustain both.

    **Diagnosis (run from PowerShell):**
    ```powershell
    # Check how many connections to the MCP port are open
    netstat -ano | Select-String ":39300" | Measure-Object
    # Check the dynamic port range
    netsh int ipv4 show dynamicport tcp
    # List all portproxy rules (look for stale ones)
    netsh interface portproxy show all
    ```

    **Fix — clean up stale proxy rules:**
    ```powershell
    # Remove any portproxy rules you no longer need
    netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=39301
    ```

    **Fix — widen the dynamic port range:**
    ```powershell
    # Requires elevated PowerShell
    netsh int ipv4 set dynamicport tcp start=10000 num=55535
    # Reboot or restart networking for it to take full effect
    ```

    **Fix — extend request timeout.** Increase the request timeout threshold from 10 to 15 minutes to provide buffer for lengthy processes without needing to open additional connections.

    **Fix — prefer StreamableHTTP over SSE.** The StreamableHTTP endpoint (`/model_context_protocol/2025-03-26/mcp`) uses short-lived request-response connections that release ports immediately. If your client supports it, prefer StreamableHTTP to avoid port exhaustion entirely.

    **Fix — reuse sessions.** Rather than opening a new SSE connection per tool call, maintain a single long-lived session and multiplex tool calls over it.

---

## Files in this skill

### References (read when needed)
- `references/PREREQS.md` — enabling LTM + basic host setup
- `references/MCP_ENDPOINTS.md` — endpoints, message flow, and port discovery
- `references/CLOUD_CONNECTIVITY.md` — ngrok/tunnel setup, MCP-only endpoint, session management, and remote troubleshooting
- `references/QUERY_PLAYBOOK.md` — query shaping patterns + examples
- `references/WRITE_PLAYBOOK.md` — write-back patterns + memory templates
- `references/TROUBLESHOOTING.md` — failure modes + how to surface actionable errors
- `references/VECTOR_SEARCH_WITH_COUCHDB.md` — how a CouchDB-backed product usually handles vector search

### Scripts (run when needed)
- `scripts/pieces_mcp_rpc.py` — list tools, call tools, and capture raw responses over SSE
- `scripts/pieces_mcp_scan.py` — find a working Pieces MCP port on localhost
- `scripts/pieces_mcp_smoke_test.py` — end-to-end "list tools -> retrieve -> write" test (when tools are available)

### Additional MCP servers
- **Pieces Docs MCP** — remote MCP at `https://docs.pieces.app/api/mcp`. Provides `search_docs`, `read_page`, `list_sections`, `get_started`. Use for documentation lookup, not LTM queries.
