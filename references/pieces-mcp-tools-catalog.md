     1|# Pieces MCP Tools Catalog
     2|
     3|All 68 tools exposed by Pieces MCP server at `http://aurora:39300/model_context_protocol/2025-03-26/mcp`.
     4|
     5|Grouped by function. Each tool accepts JSON arguments — see the full schemas in the `tools/list` response.
     6|
     7|## Full-Text Search Tools
     8|
     9|FTS uses keyword matching (not semantic). All support `limit`, `created`, and `updated` temporal filters.
    10|
    11|| Tool | Searches | Key args |
    12||------|----------|----------|
    13|| `workstream_summaries_full_text_search` | AI session summaries (shells with annotation refs) | `query`, `limit` (max 100), `created`, `updated` |
    14|| `conversations_full_text_search` | Copilot chat interactions | `query`, `limit` (max 50), `created`, `updated` |
    15|| `conversation_messages_full_text_search` | Individual messages within conversations | `query`, `limit`, `created`, `updated` |
    16|| `assets_full_text_search` | Saved code snippets and documents | `query`, `limit`, `created`, `updated` |
    17|| `annotations_full_text_search` | Annotation text (SUMMARY, DESCRIPTION, etc.) | `query`, `limit`, `created`, `updated`, `type` filter |
    18|| `tags_full_text_search` | User-created labels | `query`, `limit` (max 100) |
    19|| `workstream_events_full_text_search` | Raw clipboard/vision/audio/screenshot captures | `query`, `limit`, `created`, `updated` |
    20|| `connectors_full_text_search` | External service integrations (GCAL, GMAIL) | `query`, `limit` |
    21|| `websites_full_text_search` | Saved URLs with metadata | `query`, `limit`, `created`, `updated` |
    22|| `persons_full_text_search` | Identity records (users, contacts) | `query`, `limit`, `created`, `updated` |
    23|| `wpe_sources_full_text_search` | Application sources (Chrome, VSCode, Discord, etc.) | `query`, `limit` |
    24|| `wpe_source_windows_full_text_search` | Specific window contexts within applications | `query`, `limit` |
    25|| `hints_full_text_search` | AI-generated follow-up question suggestions | `query`, `limit` |
    26|
    27|## Vector Search Tools (Semantic)
    28|
    29|Same entity types as FTS but using embedding-based similarity. Better for natural language queries. Most have identical argument shapes to their FTS counterparts.
    30|
    31|- `workstream_summaries_vector_search`
    32|- `conversations_vector_search`
    33|- `conversation_messages_vector_search`
    34|- `assets_vector_search`
    35|- `annotations_vector_search`
    36|- `tags_vector_search`
    37|- `workstream_events_vector_search`
    38|- `hints_vector_search`
    39|- `websites_vector_search`
    40|
    41|## Snapshot Tools (Detail Retrieval)
    42|
    43|Return full entity data by UUID. Use after search to get details.
    44|
    45|| Tool | Returns |
    46||------|---------|
    47|| `workstream_summary_snapshot` | Summary metadata + annotation/source/event UUID refs |
    48|| `conversation_snapshot` | Conversation metadata + message/annotation UUID refs |
    49|| `conversation_message_snapshot` | Full message content (role, text, attachments) |
    50|| `asset_snapshot` | Full code snippet/document content + metadata |
    51|| `annotation_snapshot` | Annotation text + type (SUMMARY, DESCRIPTION, etc.) |
    52|| `annotations_batch_snapshot` | **Multiple annotations in one call** — pass array of UUIDs |
    53|| `tag_snapshot` | Tag text + associated assets/summaries |
    54|| `workstream_event_snapshot` | Raw event data (clipboard text, OCR, audio transcript, browser URL) |
    55|| `person_snapshot` | Identity info (email, name, username) |
    56|| `website_snapshot` | URL + associated assets/messages |
    57|| `hint_snapshot` | Suggested follow-up question + associations |
    58|| `range_snapshot` | Temporal span (from/to timestamps) |
    59|| `wpe_source_snapshot` | App source details (name, filter status, raw context) |
    60|| `wpe_source_window_snapshot` | Window title + associated events |
    61|
    62|## Special Tools
    63|
    64|### `ask_pieces_ltm`
    65|High-level natural language query across all Pieces LTM. Returns ranked workstream events and summaries.
    66|
    67|Required args:
    68|- `question` (string): The question to ask
    69|
    70|Optional args:
    71|- `topics` (string[]): Topical keywords for context
    72|- `application_sources` (string[]): App names if relevant
    73|- `open_files` (string[]): Currently open file paths
    74|- `chat_llm` (string): Model identifier for token budget fitting
    75|- `related_questions` (string[]): Supplementary questions
    76|
    77|### `create_pieces_memory`
    78|Save a persistent memory/checkpoint to Pieces. Think "smart commit" for your work history.
    79|
    80|Required args:
    81|- `summary_description` (string): Concise title (1-2 sentences)
    82|- `summary` (string): **Markdown** detailed narrative
    83|
    84|Optional args:
    85|- `project` (string): Absolute path to project root
    86|- `files` (string[]): Absolute file paths involved
    87|- `externalLinks` (string[]): URLs, GitHub links, docs
    88|- `connected_client` (string): Which agent/tool created this (e.g. "Hermes", "Cursor")
    89|
    90|### `extract_temporal_range`
    91|Converts natural language time expressions to UTC ISO 8601 ranges.
    92|
    93|Required arg:
    94|- `query` (string): e.g. "yesterday", "last week", "past 3 hours" (max 300 chars)
    95|
    96|**Warning**: Results are AI-generated and may be inaccurate. Compute dates yourself when possible.
    97|
    98|### `material_identifiers_full_text_search`
    99|Search across all material types (summaries, conversations, assets, etc.) by identifier. Used to locate specific items when you have partial identifiers.
   100|