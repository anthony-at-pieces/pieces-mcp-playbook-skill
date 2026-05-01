# Write-back playbook (curated memories)

Writing back to memory is most valuable when you store *compressed signal* that will be reusable.

## What to write back

Good candidates:
- Daily standup summary
- Incident timeline + root cause + mitigation
- “Decision record” (what we chose, why, alternatives)
- “How to fix” runbook entry
- A short project status checkpoint

Avoid writing back:
- raw logs
- huge pasted stack traces (unless you add a crisp summary)
- repetitive low-value entries

## Minimal payload
```json
{
  "summary": "One-line title",
  "summary_description": "5–15 lines of structured detail"
}
```

## Recommended enriched payload
```json
{
  "summary": "Incident RCA — cache stampede in /pricing endpoint",
  "summary_description": "- Symptom: intermittent 500s under load\n- Root cause: cache TTL jitter missing; concurrent recompute\n- Fix: added singleflight guard + jittered TTL\n- Tests: load test + regression test\n- Next: monitor p95 latency and error rate",
  "tags": ["incident", "cache", "pricing", "backend"],
  "source_hint": "Derived from LTM retrieval via Pieces MCP on 2026-01-02"
}
```

## Tagging guidance
Use tags that age well:
- project/repo
- subsystem
- ticket/incident id
- “standup”, “incident”, “decision”, “runbook”

Avoid tags that are too transient (“random”, “misc”, “today”).

## “Memory card” template (human-readable)
If your write tool supports only plain text, embed structure:

- Title:
- TL;DR:
- Key facts:
- Decision / action:
- Links / artifacts:
- Next steps:

This is easy for future retrieval + summarization.
