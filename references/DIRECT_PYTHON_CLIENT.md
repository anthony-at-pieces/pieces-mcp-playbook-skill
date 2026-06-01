     1|# Direct Python StreamableHTTP Client
     2|
     3|When the Hermes native MCP client fails to connect to a StreamableHTTP MCP
     4|server (e.g., Pieces MCP), call tools directly from Python using `urllib.request`.
     5|Useful inside `execute_code` blocks, cron scripts, or programmatic contexts.
     6|
     7|## Why this exists
     8|
     9|The Pieces MCP server at `/model_context_protocol/2025-03-26/mcp` uses
    10|StreamableHTTP transport with three non-obvious requirements:
    11|
    12|1. Every request must include `Accept: application/json, text/event-stream`.
    13|   Without it the server returns HTTP 406 or JSON-RPC error -32000.
    14|2. After the `initialize` call, capture the `mcp-session-id` header from the
    15|   response -- every subsequent request must include that header.
    16|3. The session ID persists for the lifetime of the process. Reuse across calls.
    17|
    18|## Working pattern (urllib, stdlib only)
    19|
    20|```python
    21|import json, urllib.request
    22|
    23|BASE = "http://localhost:39300/model_context_protocol/2025-03-26/mcp"
    24|
    25|def mcp(session_id, method, params, req_id, timeout=60):
    26|    body = json.dumps({
    27|        "jsonrpc": "2.0", "method": method,
    28|        "params": params, "id": req_id
    29|    }).encode()
    30|    headers = {
    31|        "Content-Type": "application/json",
    32|        "Accept": "application/json, text/event-stream",
    33|    }
    34|    if session_id:
    35|        headers["mcp-session-id"] = session_id
    36|    req = urllib.request.Request(BASE, data=body, headers=headers)
    37|    with urllib.request.urlopen(req, timeout=timeout) as resp:
    38|        sid = resp.headers.get("mcp-session-id") or session_id
    39|        return sid, json.loads(resp.read())
    40|
    41|# Initialize, capture session ID
    42|sid, _ = mcp(None, "initialize", {
    43|    "protocolVersion": "2025-03-26", "capabilities": {},
    44|    "clientInfo": {"name": "my-agent", "version": "1.0"}
    45|}, 1)
    46|
    47|# Call tools with session ID
    48|_, result = mcp(sid, "tools/call", {
    49|    "name": "workstream_summaries_full_text_search",
    50|    "arguments": {"query": "pieces", "limit": 5}
    51|}, 2)
    52|
    53|text = result.get("result", {}).get("content", [{}])[0].get("text", "")
    54|data = json.loads(text)  # JSON is nested inside the text string
    55|```
    56|
    57|## Pitfalls
    58|
    59|- **JSON-RPC `id`**: use integers, not strings. String IDs may misbehave.
    60|- **Response parsing**: `result.content[].text` contains JSON-encoded data --
    61|  always `json.loads()` the text field.
    62|- **`ask_pieces_ltm` is slow** (~10-15s, embedding search). Use full-text
    63|  search tools for fast keyword lookup (~200ms).
    64|- **`extract_temporal_range` is picky**: "the past month" doesn't work; use
    65|  "last month" or explicit date filters on the search tools directly.
    66|- **Timeouts**: set `timeout=90` for `ask_pieces_ltm`, `timeout=30` for
    67|  full-text searches. Omitting urllib timeout hangs indefinitely on dead sockets.
    68|- **Parallel queries**: each script gets its own session. Reuse the session ID
    69|  across calls within one script; don't re-initialize per call.
    70|
    71|## When to use this vs native `mcp_pieces_*` tools
    72|
    73|- Native tools: when `hermes mcp list` shows pieces as connected.
    74|- This pattern: when native client fails, when batch processing many calls,
    75|  when inside `execute_code`, or in cron jobs querying Pieces.
    76|