     1|# Pieces MCP Curl Patterns
     2|
     3|Copy-paste patterns for querying Pieces MCP from terminal or cron jobs where native MCP tools aren't available.
     4|
     5|## Initialize Session
     6|
     7|Every interaction starts with an `initialize` call. Capture the `mcp-session-id` from the response headers -- all subsequent calls require it.
     8|
     9|```bash
    10|BASE="http://localhost:39300/model_context_protocol/2025-03-26/mcp"
    11|
    12|# Initialize and capture session ID
    13|SID=$(curl -s -D - -X POST \
    14|  -H "Content-Type: application/json" \
    15|  -H "Accept: application/json, text/event-stream" \
    16|  -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"hermes","version":"1.0"}},"id":1}' \
    17|  "$BASE" | grep -i 'mcp-session-id' | awk '{print $2}' | tr -d '\r\n')
    18|
    19|echo "Session: $SID"
    20|```
    21|
    22|## Generic Tool Call
    23|
    24|```bash
    25|curl -s -X POST \
    26|  -H "Content-Type: application/json" \
    27|  -H "Accept: application/json, text/event-stream" \
    28|  -H "mcp-session-id: $SID" \
    29|  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"TOOL_NAME","arguments":{...}},"id":2}' \
    30|  "$BASE"
    31|```
    32|
    33|## Ask LTM (Natural Language)
    34|
    35|```bash
    36|curl -s -X POST \
    37|  -H "Content-Type: application/json" \
    38|  -H "Accept: application/json, text/event-stream" \
    39|  -H "mcp-session-id: $SID" \
    40|  -d '{
    41|    "jsonrpc":"2.0",
    42|    "method":"tools/call",
    43|    "params":{
    44|      "name":"ask_pieces_ltm",
    45|      "arguments":{
    46|        "question":"What did I work on yesterday?",
    47|        "topics":["recent","work","activity"],
    48|        "chat_llm":"qwen/qwen3.7-max"
    49|      }
    50|    },
    51|    "id":3
    52|  }' \
    53|  "$BASE"
    54|```
    55|
    56|Response contains `summaries_count`, `events_count`, and `response` with combined strings of matched content.
    57|
    58|## Workstream Summary Search (FTS)
    59|
    60|```bash
    61|curl -s -X POST \
    62|  -H "Content-Type: application/json" \
    63|  -H "Accept: application/json, text/event-stream" \
    64|  -H "mcp-session-id: $SID" \
    65|  -d '{
    66|    "jsonrpc":"2.0",
    67|    "method":"tools/call",
    68|    "params":{
    69|      "name":"workstream_summaries_full_text_search",
    70|      "arguments":{
    71|        "query":"bug fix",
    72|        "limit":10,
    73|        "created":{"from":"2026-05-01T00:00:00Z"}
    74|      }
    75|    },
    76|    "id":4
    77|  }' \
    78|  "$BASE"
    79|```
    80|
    81|**Important FTS rules:**
    82|- Use short keywords, not sentences
    83|- Wildcards (`*`) don't work
    84|- For broad coverage, run multiple queries with different keywords and deduplicate results by summary ID
    85|
    86|## Conversation Search
    87|
    88|```bash
    89|curl -s -X POST \
    90|  -H "Content-Type: application/json" \
    91|  -H "Accept: application/json, text/event-stream" \
    92|  -H "mcp-session-id: $SID" \
    93|  -d '{
    94|    "jsonrpc":"2.0",
    95|    "method":"tools/call",
    96|    "params":{
    97|      "name":"conversations_full_text_search",
    98|      "arguments":{
    99|        "query":"architecture roadmap",
   100|        "limit":5
   101|      }
   102|    },
   103|    "id":5
   104|  }' \
   105|  "$BASE"
   106|```
   107|
   108|## Fetch Annotations (Read Summary Content)
   109|
   110|Summaries are shells -- the real narrative content is in annotations. After a summary search returns annotation UUIDs, fetch them:
   111|
   112|```bash
   113|curl -s -X POST \
   114|  -H "Content-Type: application/json" \
   115|  -H "Accept: application/json, text/event-stream" \
   116|  -H "mcp-session-id: $SID" \
   117|  -d '{
   118|    "jsonrpc":"2.0",
   119|    "method":"tools/call",
   120|    "params":{
   121|      "name":"annotations_batch_snapshot",
   122|      "arguments":{
   123|        "identifiers":["UUID1","UUID2","UUID3"]
   124|      }
   125|    },
   126|    "id":6
   127|  }' \
   128|  "$BASE"
   129|```
   130|
   131|Each annotation has a `type` field:
   132|- **SUMMARY**: The hierarchical narrative (TLDR, Core Tasks, Key Decisions) -- usually what you want
   133|- **DESCRIPTION**: One-paragraph overview
   134|- Other types (ATTACHMENT, INSTRUCTION, etc.) for specialized content
   135|
   136|## Extract Temporal Range
   137|
   138|```bash
   139|curl -s -X POST \
   140|  -H "Content-Type: application/json" \
   141|  -H "Accept: application/json, text/event-stream" \
   142|  -H "mcp-session-id: $SID" \
   143|  -d '{
   144|    "jsonrpc":"2.0",
   145|    "method":"tools/call",
   146|    "params":{
   147|      "name":"extract_temporal_range",
   148|      "arguments":{"query":"yesterday"}
   149|    },
   150|    "id":7
   151|  }' \
   152|  "$BASE"
   153|```
   154|
   155|Returns ISO 8601 UTC ranges. Unreliable for complex phrases -- compute dates yourself when possible:
   156|
   157|```bash
   158|# Bash: 7 days ago in ISO format
   159|FROM=$(date -u -d '7 days ago' +'%Y-%m-%dT00:00:00Z')
   160|```
   161|
   162|## Tool Discovery
   163|
   164|List all available tools and their schemas:
   165|
   166|```bash
   167|curl -s -X POST \
   168|  -H "Content-Type: application/json" \
   169|  -H "Accept: application/json, text/event-stream" \
   170|  -H "mcp-session-id: $SID" \
   171|  -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":99}' \
   172|  "$BASE" | python3 -m json.tool
   173|```
   174|
   175|## Error Handling
   176|
   177|| Error | Cause | Fix |
   178||-------|-------|-----|
   179|| 400 Bad Request (on init) | Missing/wrong headers | Ensure `Accept: application/json, text/event-stream` header |
   180|| `mcp-session-id header is required` | Forgot session header on subsequent call | Include `mcp-session-id: $SID` header |
   181|| Empty results `{"results":[]}` | Bad keyword or no temporal overlap | Try different keywords, broaden date range |
   182|| Timeout | Server slow on large queries | Add `timeout=90` to curl |
   183|