# Query playbook for Pieces LTM via MCP

The goal: maximize recall and relevance with minimal tool calls.

## 0) First, decide what you *really* need

Turn “What was I doing?” into a retrieval spec:

- **Time scope**: exact date/range beats “recently”
- **Workstream**: repo/project/customer
- **Sources**: IDE, terminal, browser, Slack, email, etc.
- **Artifacts**: file paths, commands, PRs, tickets
- **Output format**: standup bullets vs narrative

## 1) Minimal query (baseline)

Use when:
- you don’t know what’s in memory yet
- you’re unsure which app(s) matter

Payload (using mcporter --args):
```
mcporter call pieces.ask_pieces_ltm --args '{"question":"What did I work on?","chat_llm":"gemini-2.5-flash"}' --output json
```


## The default timeframe behavior (important!)

When `ask_pieces_ltm` is called *without* a `time_window` parameter:

- It returns the most **relevant summaries and events** across _all time_.
- **Recency is a strong factor in relevance**, so recent items will naturally appear higher in results.
- However, it **does NOT enforce a strict "last N hours/days" cutoff**. Highly relevant older items might still be returned.
- For precise temporal filtering (e.g., "last 24 hours", "yesterday afternoon"), always include the `time_window` parameter.


## 2) Retrieval refinement patterns

### A) Time slicing
If “yesterday” is too broad, split:
- “yesterday morning”
- “yesterday afternoon”
- “yesterday evening”

### B) Source slicing
If memory includes noise, constrain:
- IDE/terminal only
- browser only
- meetings/chats only

Example:
```json
{
  "question": "What terminal commands did I run while debugging yesterday?",
  "application_sources": ["Warp", "Terminal", "Windows Terminal"],
  "time_window": "yesterday"
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

### D) Follow-up “show evidence”
After a summary query, run a follow-up query asking for:
- filenames
- commands
- URLs
- error messages

This increases the specificity of the final answer.

## 3) Quality gates before you answer

Before responding to the user, confirm:
- the returned context matches the user’s timeframe
- you can cite 2–5 concrete artifacts (file, command, ticket, PR)
- you’re not hallucinating connections between unrelated items

If you can’t, state:
- what you have evidence for
- what you do *not* have evidence for
- what follow-up query would resolve it

## 4) Common failure mode: “too smart” questions
Avoid asking the tool to *already* produce the final report.

Good: “Retrieve what I worked on yesterday afternoon on caching.”
Bad: “Write a perfect standup report with action items and priorities.”

Let retrieval retrieve; synthesis synthesizes.
