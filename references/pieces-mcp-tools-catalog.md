# Pieces MCP Tools Catalog

All 69 tools exposed by the Pieces MCP server (verified live against PiecesOS 12.5.0 at `http://localhost:39300/model_context_protocol/2025-03-26/mcp`).

Grouped by function. Each tool accepts JSON arguments -- see the full schemas in the `tools/list` response. Search tools accept `query` plus `limit` and optional `created`/`updated` ISO-8601 range filters; batch snapshots accept `identifiers[]` (1-100 UUIDs); single snapshots accept `identifier`.

Note: `models_full_text_search`, `entities_full_text_search`, `models_batch_snapshot`, `entities_batch_snapshot`, and `assets_full_text_search` appeared in older catalogs but are NOT exposed by 12.5.0.

## High-Level Memory Tools (5)

| Tool | Required | Description |
|------|----------|-------------|
| `search_memory` | (none) | This is the PRIMARY tool for answering questions about a user's work history. Start here whenever the user asks about what they worked on, who they interacted with, what... |
| `ask_memory` | (none) | Ask Pieces to retrieve historical and contextual information from the user's long-term memory (LTM). This tool searches across workstream events (screenshots, clipboard,... |
| `ask_pieces_ltm` | question | Ask Pieces to retrieve historical and contextual information from the user's long-term memory (LTM). This tool searches across workstream events (screenshots, clipboard,... |
| `create_pieces_memory` | summary_description, summary | Use this tool to capture a detailed, never-forgotten memory in Pieces. Agents and humans alikeâ€"such as Cursor, Claude, Perplexity, Goose, and ChatGPTâ€"can leverage the... |
| `get_user_persona` | (none) | Retrieves the current user's latest persona â€" an AI-generated hierarchical profile summary that captures the user's role, expertise, preferences, and communication styl... |

## Full-Text Search Tools (13)

| Tool | Required | Description |
|------|----------|-------------|
| `anchors_full_text_search` | query | Searches through Anchors are reference points marking important locations in codebases. Each anchor has a name and links to one or more anchor points (specific file paths... |
| `annotations_full_text_search` | query | Searches through annotations â€" the primary TEXT CONTENT layer in the Pieces data model. Annotations are the primary TEXT CONTENT layer in the Pieces data model. They co... |
| `connectors_full_text_search` | query | Searches through Connectors represent external service integrations with third-party providers. Available providers: GCAL (Google Calendar), GMAIL (Google Mail). Each con... |
| `conversation_messages_full_text_search` | query | Searches through Conversation messages are individual messages within Copilot conversations. They capture the back-and-forth dialog between users and AI assistants, inclu... |
| `conversations_full_text_search` | query | Searches through Conversations are chat interactions with the Pieces Copilot. Each conversation contains: the full message history (user questions and AI responses), cont... |
| `hints_full_text_search` | query | Hints are AI-generated suggested follow-up questions stored in the Pieces ecosystem. Hints help users explore their captured knowledge and workflow more deeply by suggest... |
| `persons_full_text_search` | query | Searches through Persons are identity records representing users, collaborators, and contacts. Each person contains identifying information like email, name, and username... |
| `tags_full_text_search` | query | Searches through Tags are user-created labels for organizing and categorizing content. They help users quickly find and group related topics, conversations, and other sav... |
| `websites_full_text_search` | query | Websites represent URLs and their associated metadata stored in the Pieces ecosystem. Each website contains:... |
| `workstream_events_full_text_search` | query | Searches through workstream events â€" the lowest-level memory captures in the user's workstream. Workstream events are the LOWEST-LEVEL memory captures in the user's wor... |
| `workstream_summaries_full_text_search` | query | Searches through Workstream summaries are AI-generated summaries of user work sessions and activities. Each summary is a SHELL data structure â€" it contains metadata (na... |
| `wpe_source_windows_full_text_search` | query | WPE (Workstream Pattern Engine) Source Windows represent unique window contexts extracted during workstream event aggregation. When Pieces captures workflow activity thro... |
| `wpe_sources_full_text_search` | query | WPE (Workstream Pattern Engine) Sources represent identified applications extracted during workstream event aggregation. When Pieces captures workflow activity through cl... |

## Vector Search Tools (6)

| Tool | Required | Description |
|------|----------|-------------|
| `hints_vector_search` | query | Hints are AI-generated suggested follow-up questions stored in the Pieces ecosystem. Hints help users explore their captured knowledge and workflow more deeply by suggest... |
| `materials_vector_search` | query, material_type | Performs semantic vector search across materials using AI embeddings (Potion model). Unlike full-text search which matches keywords, vector search understands meaning and... |
| `signals_vector_search` | query | Performs semantic vector search across signals. Signals represent real-time notifications and event triggers within the Pieces ecosystem. A signal captures a discrete eve... |
| `tags_vector_search` | query | Performs semantic vector search across tags using AI embeddings. Tags are user-created labels for organizing and categorizing content. They help users quickly find and gr... |
| `workstream_events_vector_search` | query | Performs semantic vector search across workstream events using AI embeddings. Workstream events are the LOWEST-LEVEL memory captures in the user's workstream, recorded ap... |
| `workstream_summaries_vector_search` | query | Performs semantic vector search across workstream summaries using AI embeddings. Workstream summaries are AI-generated summaries of user work sessions and activities. Eac... |

## Batch Snapshot Tools (15)

| Tool | Required | Description |
|------|----------|-------------|
| `anchor_points_batch_snapshot` | identifiers | Retrieves multiple anchor points by their identifiers in a single request. Anchor points are specific file path locations within anchors. Each anchor point represents an... |
| `anchors_batch_snapshot` | identifiers | Retrieves multiple anchors by their identifiers in a single request. Anchors are reference points marking important locations in codebases. Each anchor has a name and lin... |
| `annotations_batch_snapshot` | identifiers | Retrieves multiple annotations by their identifiers in a single request. Annotations are the primary TEXT CONTENT layer in the Pieces data model. They contain the actual... |
| `connectors_batch_snapshot` | identifiers | Retrieves multiple connectors by their identifiers in a single request. Connectors represent external service integrations with third-party providers. Available providers... |
| `conversation_messages_batch_snapshot` | identifiers | Retrieves multiple conversation messages by their identifiers in a single request. Conversation messages are individual messages within Copilot conversations. They captur... |
| `conversations_batch_snapshot` | identifiers | Retrieves multiple conversations by their identifiers in a single request. Conversations are chat interactions with the Pieces Copilot. Each conversation contains: the fu... |
| `hints_batch_snapshot` | identifiers | Retrieves multiple hints by their identifiers in a single request. Hints are AI-generated suggested follow-up questions stored in the Pieces ecosystem. Hints help users e... |
| `persons_batch_snapshot` | identifiers | Retrieves multiple persons by their identifiers in a single request. Persons are identity records representing users, collaborators, and contacts. Each person contains id... |
| `ranges_batch_snapshot` | identifiers | Retrieves multiple ranges by their identifiers in a single request. Ranges are temporal spans used for grounding conversations and summaries in specific time periods. The... |
| `tags_batch_snapshot` | identifiers | Retrieves multiple tags by their identifiers in a single request. Tags are user-created labels for organizing and categorizing content. They help users quickly find and g... |
| `websites_batch_snapshot` | identifiers | Retrieves multiple websites by their identifiers in a single request. Websites represent URLs and their associated metadata stored in the Pieces ecosystem. Each website c... |
| `workstream_events_batch_snapshot` | identifiers | Retrieves multiple workstream events by their identifiers in a single request. Workstream events are the LOWEST-LEVEL memory captures in the user's workstream, recorded a... |
| `workstream_summaries_batch_snapshot` | identifiers | Retrieves multiple workstream summaries by their identifiers in a single request. Workstream summaries are AI-generated summaries of user work sessions and activities. Ea... |
| `wpe_source_windows_batch_snapshot` | identifiers | Retrieves multiple WPE (Workstream Pattern Engine) source windows by their identifiers in a single request. WPE (Workstream Pattern Engine) Source Windows represent uniqu... |
| `wpe_sources_batch_snapshot` | identifiers | Retrieves multiple WPE (Workstream Pattern Engine) sources by their identifiers in a single request. WPE (Workstream Pattern Engine) Sources represent identified applicat... |

## Single Snapshot Tools (15)

| Tool | Required | Description |
|------|----------|-------------|
| `anchor_point_snapshot` | identifier | Retrieves an anchor point by its identifier. Anchor points are specific file path locations within anchors. Each anchor point represents an exact position in a codebase t... |
| `anchor_snapshot` | identifier | Retrieves an anchor by its identifier. Anchors are reference points marking important locations in codebases. Each anchor has a name and links to one or more anchor point... |
| `annotation_snapshot` | identifier | Retrieves an annotation by its identifier. Annotations are the primary TEXT CONTENT layer in the Pieces data model. They contain the actual narrative text for notes, summ... |
| `connector_snapshot` | identifier | Retrieves a connector by its identifier. Connectors represent external service integrations with third-party providers. Available providers: GCAL (Google Calendar), GMAIL... |
| `conversation_message_snapshot` | identifier | Retrieves a conversation message by its identifier. Conversation messages are individual messages within Copilot conversations. They capture the back-and-forth dialog bet... |
| `conversation_snapshot` | identifier | Retrieves a conversation by its identifier. Conversations are chat interactions with the Pieces Copilot. Each conversation contains: the full message history (user questi... |
| `hint_snapshot` | identifier | Retrieves a hint by its identifier. Hints are AI-generated suggested follow-up questions stored in the Pieces ecosystem. Hints help users explore their captured knowledge... |
| `person_snapshot` | identifier | Retrieves a person by its identifier. Persons are identity records representing users, collaborators, and contacts. Each person contains identifying information like emai... |
| `range_snapshot` | identifier | Retrieves a range by its identifier. Ranges are temporal spans used for grounding conversations and summaries in specific time periods. They define "from" and "to" timest... |
| `tag_snapshot` | identifier | Retrieves a tag by its identifier. Tags are user-created labels for organizing and categorizing content. They help users quickly find and group related topics, conversati... |
| `website_snapshot` | identifier | Retrieves a website by its identifier. Websites represent URLs and their associated metadata stored in the Pieces ecosystem. Each website contains:... |
| `workstream_event_snapshot` | identifier | Retrieves a workstream event by its identifier. Workstream events are the LOWEST-LEVEL memory captures in the user's workstream, recorded approximately every 2 seconds. T... |
| `workstream_summary_snapshot` | identifier | Retrieves a workstream summary by its identifier. Workstream summaries are AI-generated summaries of user work sessions and activities. Each summary is a SHELL data struc... |
| `wpe_source_snapshot` | identifier | WPE (Workstream Pattern Engine) Sources represent identified applications extracted during workstream event aggregation. When Pieces captures workflow activity through cl... |
| `wpe_source_window_snapshot` | identifier | WPE (Workstream Pattern Engine) Source Windows represent unique window contexts extracted during workstream event aggregation. When Pieces captures workflow activity thro... |

## Browser Tools (2)

| Tool | Required | Description |
|------|----------|-------------|
| `browser_activity` | (none) | Explore the user's browser activity over a time range. Returns browsing history, engagement metadata, search terms, downloads, and bookmarks. |
| `browser_lookup` | query | URL or topic match tool â€" given a URL, partial URL, keyword, or topic, fans out to history, engagement metadata, search terms, bookmarks, and favicons in parallel and r... |

## Filesystem Tools (3)

| Tool | Required | Description |
|------|----------|-------------|
| `filesystem_search_paths` | query | Search for files and directories by fuzzy path matching. Given a filename, partial path, or approximate/garbled path, finds the most likely matching files on disk. Handle... |
| `filesystem_search_text` | pattern | Search file contents for a text pattern (literal or regex), similar to grep. Walks specified directories, reads text files, and returns files containing matching lines wi... |
| `filesystem_read_chunk` | path | Read a chunk of a file at a given byte offset. Use for paginated reading of files too large to return in one response. |

## Google Calendar Tools (6)

| Tool | Required | Description |
|------|----------|-------------|
| `list_gcal_connectors` | (none) | Returns the list of connected Google Calendar connectors â€" each entry represents a Google account the user has connected to Pieces. When addressing the user in natural... |
| `get_gcal_events` | time_min, time_max | Fetches events from the user's Google Calendar within a time range. Returns event details including title, start/end times, location, description, attendees, and organize... |
| `get_gcal_event` | event_id | Fetches a single Google Calendar event by its ID. Returns full event details including title, times, location, description, attendees, and organizer. |
| `create_gcal_event` | (none) | Creates a new event on the user's Google Calendar. Returns the created event with its assigned ID and full details. |
| `patch_gcal_event` | event_id | Updates specific fields of an existing Google Calendar event. Only the fields you provide are changed; omitted fields are left unchanged. Returns the updated event. |
| `delete_gcal_event` | event_id | Permanently deletes a Google Calendar event by its ID. This action cannot be undone. |

## Utility Tools (4)

| Tool | Required | Description |
|------|----------|-------------|
| `extract_temporal_range` | query | Extracts UTC time ranges from natural language queries using AI/ML models. Converts human-readable time expressions like "yesterday", "last week", or "the past 3 hours" i... |
| `time_compute` | operation | Deterministic time utility supporting four operations via the "operation" parameter:... |
| `web_search` | query | Performs AI-powered web search using Perplexity to answer questions with real-time information from the internet. Returns answers with source citations for verification. |
| `material_identifiers` | material_type | Retrieves identifiers (UUIDs) for materials matching specified filters. |
