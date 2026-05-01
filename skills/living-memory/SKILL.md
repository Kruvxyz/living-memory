---
name: living-memory
description: "Query past Claude Code sessions as living memories. Use when the user references prior work — phrases like 'what did we decide', 'remember when', 'last week's session', 'the script we built before', 'continue from'. Two tools: `recall` finds relevant past sessions by topic; `query_session` asks a specific past session a question by spawning Claude Code with --resume."
---

# Living Memory

This skill lets you query past Claude Code sessions instead of trying to
remember them from summaries. Past sessions are kept whole and resumable.

## When to use

Use this skill whenever the user references prior work that isn't in the
current session's context. Common cues:

- "What did we decide about X?"
- "Remember when we worked on Y?"
- "Continue from where we left off"
- "Find the script we built last week"
- "How did we solve the bug in <file>?"

## Workflow

1. **Find candidate sessions** with `recall`:

   ```
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/living-memory/scripts/recall.py "<query>"
   ```

   Optional flags: `--project <name>`, `--limit <n>`, `--since <iso-date>`.

   Returns a JSON list of sessions: `session_id`, `started_at`, `cwd`,
   `first_user_msg`, `files_touched`.

2. **Pick the most relevant** session_id from the results.

3. **Ask that session a question** with `query_session`:

   ```
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/living-memory/scripts/query_session.py <session_id> "<question>"
   ```

   This spawns `claude --resume <session_id> -p "<question>"` and returns
   the answer text.

4. **Synthesize** the answer into your reply to the user. If multiple
   sessions are relevant, repeat step 3 for each and combine.

## Tips

- Keep `recall` queries short (1-3 keywords). It's substring search,
  not semantic.
- For cross-session synthesis, run `query_session` on 2-4 candidates
  rather than dumping all results into context.
- The resumed session is sandboxed: it answers and exits. It does not
  continue the active session or modify files.
