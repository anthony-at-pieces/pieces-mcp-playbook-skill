---
name: pieces-mcp-playbook
description: Connect to the Pieces MCP server (SSE) and interact with the full Pieces data plane -- LTM queries, targeted full-text and vector search across workstream events/summaries/conversations/annotations/tags/websites, batch snapshot retrieval, and memory creation. Verified against Pieces 12.3.11.
license: MIT
compatibility: Any Agent Skills host that can call MCP tools and/or run local scripts; assumes PiecesOS exposes MCP on localhost or LAN (commonly port 39300) via an SSE endpoint.
metadata:
  author: anthony-demo
  version: "2.0"
---

# Pieces MCP Playbook

Use this skill when you need to interact with **Pieces** through its **MCP server** -- whether that's querying Long-Term Memory (LTM), doing targeted searches across workstream events, conversations, annotations, tags, websites, or writing back curated memories.

Pieces MCP exposes **30+ tools** organized into five categories (see Tool Catalog below). The two highest-level tools (`ask_pieces_ltm` and `create_pieces_memory`) handle most use cases, but the granular search + batch snapshot tools give you precise control over what you retrieve.

## What this skill assumes

- PiecesOS is installed + running and LTM is enabled (see `references/PREREQS.md`).
- Your MCP host is pointed at a Pieces MCP SSE URL. Verified paths: `http://<host>:39300/model_context_protocol/2025-03-26/sse` (Pieces 12.3.11) or `.../2024-11-05/sse` (older versions).
- **Network note:** Pieces MCP binds to **127.0.0.1 only**. If connecting from another machine (e.g., WSL to Aurora at 192.168.86.34), a Windows port proxy is required on the Pieces host:
  ```powershell
  netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=39300 connectaddress=127.0.0.1 connectport=39300
  ```
- Your environment provides some way to call MCP tools -- either directly or via the included RPC script.

If you are unsure what tools exist, run: `python scripts/pieces_mcp_rpc.py --host <host> --mcp-version 2025-03-26 --list-tools`

---

## Core concepts (don’t skip)

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
| `ask_pieces_ltm` | `question`, `chat_llm` | Ask Pieces a question to retrieve historical/contextual info from the user's environment. Optional: `topics[]`, `application_sources[]`, `open_files[]`, `related_questions[]`, `connected_client` |
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
Only `question` and `chat_llm` are required. `application_sources` accepts specific app names from the Pieces source list.

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
3.  Confirm the **SSE URL** is correct, including the versioned path (`.../model_context_protocol/2024-11-05/sse`).
4.  **List tools** via `mcporter list` or `python scripts/pieces_mcp_rpc.py --list-tools`.


This skill includes known failure patterns reported publicly (e.g., retrieval tool failing while memory creation works) to help you design graceful degradation.

---

## Files in this skill

### References (read when needed)
- `references/PREREQS.md` — enabling LTM + basic host setup
- `references/MCP_ENDPOINTS.md` — endpoints, message flow, and port discovery
- `references/QUERY_PLAYBOOK.md` — query shaping patterns + examples
- `references/WRITE_PLAYBOOK.md` — write-back patterns + memory templates
- `references/TROUBLESHOOTING.md` — failure modes + how to surface actionable errors
- `references/VECTOR_SEARCH_WITH_COUCHDB.md` — how a CouchDB-backed product usually handles vector search

### Scripts (run when needed)
- `scripts/pieces_mcp_rpc.py` — list tools, call tools, and capture raw responses over SSE
- `scripts/pieces_mcp_scan.py` — find a working Pieces MCP port on localhost
- `scripts/pieces_mcp_smoke_test.py` — end-to-end “list tools → retrieve → write” test (when tools are available)
