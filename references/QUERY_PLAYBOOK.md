# Query playbook for Pieces LTM via MCP

The goal: maximize recall and relevance with minimal tool calls.

## 0) First, decide what you *really* need

Turn "What was I doing?" into a retrieval spec:

- **Time scope**: exact date/range beats "recently"
- **Workstream**: repo/project/customer
- **Sources**: IDE, terminal, browser, Slack, email, etc.
- **People**: names/emails involved
- **Artifacts**: file paths, commands, PRs, tickets
- **Output format**: standup bullets vs narrative

## 1) Pick the right entry tool

- **`search_memory`** -- the server's designated PRIMARY tool for work-history questions. Graph-based evidence retrieval. Person names go in `persons[]` (never in `hints[]`); topics/technologies go in `hints[]`; time bounds go in `created`.
- **`ask_pieces_ltm`** -- semantic question answering over all LTM data. Only `question` is required; `chat_llm` is optional but recommended so Pieces can fit the context to your model.
- **`ask_memory`** -- like `ask_pieces_ltm` but takes explicit UTC `time_ranges[]`; always provide at least one range.
- **Targeted `*_full_text_search` / `*_vector_search`** -- when you know the data type you want (summaries, events, conversations, annotations, websites, tags, persons).

Minimal baseline (use when you don't know what's in memory yet):
```
mcporter call pieces.ask_pieces_ltm --args '{"question":"What did I work on?"}' --output json
```

## 2) Temporal filtering (important!)

`ask_pieces_ltm` has **no** `time_window` parameter. When called without temporal hints:

- It returns the most **relevant summaries and events** across _all time_.
- **Recency is a strong factor in relevance**, so recent items naturally rank higher.
- It does NOT enforce a strict "last N hours/days" cutoff. Highly relevant older items might still be returned.

For precise temporal filtering, do one of:
1. Put the timeframe in the question text itself ("yesterday afternoon", "last Tuesday") -- the LTM pipeline parses it.
2. Call `extract_temporal_range` to convert the phrase into UTC timestamps, then pass them as `created: {from, to}` to any search tool, or as `time_ranges[]` to `ask_memory`.
3. Use `search_memory` with a `created` range.

## 3) Retrieval refinement patterns

### A) Time slicing
If "yesterday" is too broad, split:
- "yesterday morning"
- "yesterday afternoon"
- "yesterday evening"

### B) Source slicing
If memory includes noise, constrain:
- IDE/terminal only
- browser only
- meetings/chats only

Example:
```json
{
  "question": "What terminal commands did I run while debugging yesterday?",
  "application_sources": ["Warp", "Terminal", "Windows Terminal"]
}
```

### C) Entity anchoring
If you know *any* anchor, include it:
- repo name
- branch name
- PR number
- ticket id
- filename(s)

Example:
```json
{
  "question": "Summarize my changes related to ABC-456.",
  "topics": ["ABC-456", "billing", "refund", "controller", "integration test"]
}
```

With `search_memory`, anchors go in `hints[]` and people go in `persons[]`:
```json
{
  "persons": ["jane@example.com"],
  "hints": ["ABC-456", "billing", "refund"],
  "created": { "from": "2026-01-14T00:00:00Z", "to": "2026-01-15T00:00:00Z" }
}
```

### D) Follow-up "show evidence"
After a summary query, run a follow-up query asking for:
- filenames
- commands
- URLs
- error messages

This increases the specificity of the final answer.

### E) Hydrate the shells
Workstream summaries are shells; their narrative lives in annotations. If a summary result looks thin, take its annotation UUIDs and call `annotations_batch_snapshot` to get the actual text.

## 4) Quality gates before you answer

Before responding to the user, confirm:
- the returned context matches the user's timeframe
- you can cite 2-5 concrete artifacts (file, command, ticket, PR)
- you're not hallucinating connections between unrelated items

If you can't, state:
- what you have evidence for
- what you do *not* have evidence for
- what follow-up query would resolve it

## 5) Common failure mode: "too smart" questions
Avoid asking the tool to *already* produce the final report.

Good: "Retrieve what I worked on yesterday afternoon on caching."
Bad: "Write a perfect standup report with action items and priorities."

Let retrieval retrieve; synthesis synthesizes.
