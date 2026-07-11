# Write-back playbook (curated memories)

Writing back to memory is most valuable when you store *compressed signal* that will be reusable.

## What to write back

Good candidates:
- Daily standup summary
- Incident timeline + root cause + mitigation
- "Decision record" (what we chose, why, alternatives)
- "How to fix" runbook entry
- A short project status checkpoint

Avoid writing back:
- raw logs
- huge pasted stack traces (unless you add a crisp summary)
- repetitive low-value entries

## Field semantics (get these right)

`create_pieces_memory` takes exactly these fields (verified against PiecesOS 12.5.0):

- `summary_description` (required) -- the short title. 1-2 sentences describing what the memory is about.
- `summary` (required) -- the detailed **markdown-formatted narrative**. This is the body; make it as complete as a future reader needs.
- `files` (optional) -- absolute paths of relevant files or folders.
- `externalLinks` (optional) -- GitHub/GitLab URLs (with branch details), docs, articles consulted.
- `project` (optional) -- absolute path to the project root.
- `connected_client` (optional) -- name of the calling client (e.g., `Claude`, `Cursor`).

There is **no `tags` parameter and no `source_hint` parameter**. Weave key terms (project, subsystem, ticket id, "standup"/"incident"/"decision"/"runbook") into the summary text itself -- full-text and vector search will find them there.

## Minimal payload
```json
{
  "summary_description": "One-line title",
  "summary": "5-15 lines of structured markdown detail"
}
```

## Recommended enriched payload
```json
{
  "summary_description": "Incident RCA -- cache stampede in /pricing endpoint",
  "summary": "## Incident RCA: cache stampede in /pricing (backend)\n- Symptom: intermittent 500s under load\n- Root cause: cache TTL jitter missing; concurrent recompute\n- Fix: added singleflight guard + jittered TTL\n- Tests: load test + regression test\n- Next: monitor p95 latency and error rate\n- Keywords: incident, cache, pricing, backend",
  "files": ["/repo/services/pricing/cache.py"],
  "externalLinks": ["https://github.com/org/repo/pull/123"],
  "project": "/repo"
}
```

## "Memory card" template (human-readable)
If your write tool supports only plain text, embed structure:

- Title:
- TL;DR:
- Key facts:
- Decision / action:
- Links / artifacts:
- Next steps:

This is easy for future retrieval + summarization.
