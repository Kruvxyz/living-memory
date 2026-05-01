# Living Memory

Turn your past Claude Code sessions into queryable agents. Instead of compressing work into summaries, keep sessions whole and ask them questions directly.

## The Problem

After a long session, you exit. The next day, someone asks: *"What did we decide about X? Do we have a script for that? How did we solve that bug?"*

You could search your files, flip through notebooks, or remember from scratch. Or: **you could ask the session itself.**

## The Solution

Living Memory automatically indexes every Claude Code session you run. When you need to recall something, you search for relevant sessions and ask them questions using `claude --resume`. The agent in *this* session finds the right past sessions, spawns them with your question, and synthesizes the answer.

**Key insight:** Claude Code already has a tool for this — `claude --resume <session-id> -p "<question>"`. We just need an index to find the right session ID.

## Install

```bash
/plugin install https://github.com/Kruvxyz/living-memory
```

Restart Claude Code. That's it. The SessionEnd hook auto-registers and the skill becomes available.

## Quick Start

### 1. Let a session finish normally

Just use Claude Code as usual. When you exit, the hook fires silently in the background and indexes the session.

### 2. In a later session, ask for what you built

```
User: "What did we decide about the Health Score formula last week?"

Claude: "Let me search your past sessions for that."
→ Recalls 3 sessions mentioning "health score"
→ Picks the most recent one
→ Asks it: "What was our final conclusion on the Health Score formula?"
→ Returns: "We settled on a weighted 3-component model: organism fitness (40%), environment synergy (35%), selection pressure (25%)."
```

## Workflow

### Search for past sessions

When you mention prior work, the agent uses `recall` to find relevant sessions:

```
recall("health score", project="organism", since="2026-04-01")
```

Returns:
```json
[
  {
    "session_id": "abc123-...",
    "started_at": "2026-04-28T14:22:00+03:00",
    "cwd": "/Users/you/projects/organism",
    "first_user_msg": "Let's redesign the Health Score formula...",
    "files_touched": ["health_score.py", "agent_orchestrator.py"]
  }
]
```

### Ask that session a question

Pick the most relevant session and ask it something specific:

```
query_session("abc123-...", "What was our final conclusion on the Health Score formula?")
```

The session resumes, reads your question, and answers. The answer lands back in your current session.

### The agent synthesizes

If multiple sessions are relevant, the agent repeats step 2 for each and combines the results into a coherent answer for you.

## Features

- **Automatic indexing** — Every session is logged at exit. Zero manual steps.
- **Fast substring search** — Find sessions by keywords in messages, files, or project names. Scales to thousands of sessions.
- **Real answers, not summaries** — You get answers from the actual session, not a compressed description. The resumed session has full context.
- **Sandboxed retrieval** — When you ask a past session a question, it answers and exits. It doesn't modify your files or affect the current session.
- **Secret redaction** — API keys, tokens, and credentials are automatically stripped from the index before storage.
- **Pure stdlib** — No npm install, no pip install, no dependencies. Just `/plugin install`.

## Examples

### "I remember we built a script for this, where is it?"

```
User: "Remember when we wrote a script to backfill the database? Find it."

Claude: [recalls sessions mentioning "backfill"]
→ Finds session from 3 weeks ago
→ Asks: "What was the backfill script we built? Show me the file path and key functions."
→ Returns the location and summary.
```

### "How did we fix that performance issue?"

```
User: "I think we solved the latency spike in requests.py. What was the fix?"

Claude: [recalls sessions with "requests.py" and "latency"]
→ Finds the session where you debugged it
→ Asks: "What was causing the latency spike in requests.py and how did we fix it?"
→ Returns: "It was N+1 queries in the user fetch loop. We batched them with..."
```

### "Continue work from where we left off"

```
User: "Continue the authentication refactor from last week."

Claude: [recalls sessions mentioning "authentication" or "auth"]
→ Asks the most recent relevant session: "Summarize the state of the auth refactor. What's left to do?"
→ Gets the status and next steps
→ You continue from there.
```

## Architecture

```
┌─────────────────────────────────────┐
│  Your active Claude Code session    │
├─────────────────────────────────────┤
│  User: "What did we decide about X?"│
│         ↓                           │
│  Agent invokes: recall("X")         │
│         ↓                           │
│  Returns: [session_id, ...]         │
│         ↓                           │
│  Agent invokes: query_session(...)  │
│         ↓                           │
│  Past session answers & exits       │
│         ↓                           │
│  Agent synthesizes & replies        │
└─────────────────────────────────────┘
```

**At session end:**
- Hook reads transcript from `~/.claude/projects/<session-id>.jsonl`
- Extracts: session ID, timestamp, files touched, first & last message
- Redacts secrets
- Appends to `~/.claude/.living-memory/index.jsonl`

## Data Storage

Sessions are indexed in `~/.claude/.living-memory/index.jsonl` — one JSON line per session. The actual transcripts stay in Claude Code's normal location and are only re-read when you ask about a specific session.

Each index entry contains:
- `session_id` — UUID to identify the session
- `started_at`, `ended_at` — Timestamps
- `cwd` — What directory you were working in
- `project_name` — Extracted from cwd (for filtering)
- `first_user_msg`, `last_assistant_msg` — First 500 chars of key messages
- `files_touched` — Most recent 20 files you edited
- `message_count` — Total messages in the session
- `transcript_path` — Where Claude Code stores the full transcript

**No secrets in the index** — API keys, tokens, and credentials are redacted before storage.

## Tips

- **Keep recall queries short** — 1–3 keywords work best. It's substring search, not semantic.
- **Be specific with query_session** — The better the question, the better the answer. "What was the bug?" beats "Tell me about that session."
- **Use project filtering** — If you work on multiple repos, add `project="organism"` to narrow results.
- **Spot-check the index** — First time, grep for `sk-`, `ghp_`, `AKIA` to verify no secrets leaked. They shouldn't appear.

## Troubleshooting

### "The plugin installed but the skill doesn't show up"

Restart Claude Code. Skills load at startup.

### "I ran a session but it didn't get indexed"

Check `~/.claude/.living-memory/` exists and is writable. If there's an error, check `~/.claude/.living-memory/errors.log`.

### "Recall returns no results"

Queries are case-insensitive substring matches. Try shorter keywords. Check that sessions actually touched files or mentioned topics with those words.

### "I see secrets in the index"

Open an issue — that's a bug. The redaction should catch common patterns. If it missed something, we'll add it.

## Contributing

This is early-stage. If you hit problems or have ideas, [open an issue on GitHub](https://github.com/Kruvxyz/living-memory/issues).

## What's Planned

- Semantic search (when substring search isn't enough)
- Cross-session synthesis tool
- Web viewer for the index
- Optional marketplace listing for easier discovery
- Decay / archive old sessions

See [PLAN.md](PLAN.md) for the full roadmap and architecture details.

## License

MIT
