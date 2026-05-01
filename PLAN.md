# Living Memory — Spec & Implementation Plan

## Vision

A Claude Code plugin that turns past sessions into queryable agents.
Instead of compressing sessions into static summaries, we keep them whole
and let the main agent spawn sub-agents loaded with specific past sessions
to answer questions about them.

The core insight: `claude --resume <session-id> -p "<question>"` already
does the heavy lifting. We don't need to parse transcripts, manage context
windows, or build summarization pipelines. We just need an index that
helps us find the right session ID, then we delegate to Claude Code itself.

## User Stories

1. **Recall by topic.** "Find the sessions where we discussed Health Score."
   → Returns 3 session IDs with metadata (date, cwd, first message).

2. **Query a specific session.** "What did session abc123 conclude about
   selection pressure?"
   → Spawns `claude --resume abc123 -p "..."`, returns answer.

3. **Cross-session synthesis.** "How did our definition of Health Score
   evolve across the last 5 Organism sessions?"
   → Recall finds candidates, query_session runs against each, main agent
   synthesizes.

4. **Project filter.** "Find recall results only from The Organism repo."
   → Same as (1) but filtered by `cwd`.

## Non-Goals (v0)

- No vector database. No embeddings. Substring + tag search only.
- No automatic context injection at SessionStart. Retrieval is on-demand.
- No summarization pipeline. Metadata only.
- No web UI. CLI + skill tools only.
- No multi-user / cloud sync. Local filesystem only.
- **No external Python dependencies.** Pure stdlib only. (Design constraint,
  not a guideline. Keeps install to a single `/plugin install` command.)

## Distribution Strategy

This is a **Claude Code plugin**, installable via the standard plugin
system. No custom installer, no `npm install`, no manual hook editing.

Two install paths users will have:

1. **Direct from GitHub:**
   ```
   /plugin install https://github.com/<owner>/living-memory
   ```

2. **Via marketplace** (if we maintain one):
   ```
   /plugin marketplace add <owner>/living-memory
   /plugin install living-memory
   ```

After install + restart, the SessionEnd hook is auto-registered and the
skill becomes available to the agent. Zero manual config.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Claude Code Session (active)                               │
│                                                             │
│  User: "What did we decide about X last week?"              │
│       │                                                     │
│       ▼                                                     │
│  Main agent invokes skill: recall("X")                      │
│       │                                                     │
│       ▼                                                     │
│  Skill reads ~/.claude/.living-memory/index.jsonl           │
│  Returns: [{session_id, date, cwd, first_msg}, ...]         │
│       │                                                     │
│       ▼                                                     │
│  Main agent picks session, invokes: query_session(id, q)    │
│       │                                                     │
│       ▼                                                     │
│  Skill runs: claude --resume <id> -p "<q>"                  │
│  Returns answer text to main agent                          │
│       │                                                     │
│       ▼                                                     │
│  Main agent synthesizes and replies to user                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  SessionEnd Hook (auto-registered by plugin)                │
│                                                             │
│  On session end:                                            │
│    1. Read JSON payload from stdin                          │
│    2. Read transcript from ~/.claude/projects/<...>         │
│    3. Extract: session_id, started_at, ended_at, cwd,       │
│       first_user_msg (truncated), last_assistant_msg        │
│       (truncated), files_touched (from tool calls)          │
│    4. Append line to ~/.claude/.living-memory/index.jsonl   │
│    5. Exit 0 (always — never block session end)             │
└─────────────────────────────────────────────────────────────┘
```

## Repository Layout (Plugin Structure)

This follows the official Claude Code plugin spec. Do **not** invent
your own structure — these paths are required for `/plugin install` to
work correctly.

```
├── .claude-plugin/
│   └── living-memory/
├── .claude-plugin/
│   └── plugin.json              # REQUIRED: plugin manifest
│
├── hooks/
│   ├── hooks.json               # Hook registration (SessionEnd)
│   └── session_end.py           # The hook script itself
│
├── skills/
│   └── living-memory/
│       ├── SKILL.md             # Skill description + usage
│       └── scripts/
│           ├── recall.py        # Invoked by skill for substring search
│           └── query_session.py # Invoked by skill to run claude --resume
│
├── lib/
│   ├── __init__.py
│   ├── paths.py                 # Resolve ~/.claude, ~/.claude/.living-memory
│   ├── transcript.py            # Read & parse Claude Code transcripts
│   ├── indexer.py               # Used by session_end.py
│   ├── search.py                # Used by recall.py
│   ├── query.py                 # Used by query_session.py
│   └── redact.py                # Secret redaction
│
├── tests/
│   ├── test_indexer.py
│   ├── test_search.py
│   ├── test_redact.py
│   └── fixtures/
│       └── sample_transcript.jsonl
│
├── README.md
├── LICENSE                       # MIT
└── PLAN.md                       # This file
```

**Key rules:**

- `${CLAUDE_PLUGIN_ROOT}` is an environment variable Claude Code sets to
  the absolute path of the installed plugin. Use it in `hooks.json` and
  any script paths — never hardcode absolute paths.
- `lib/` is plain Python imported via `sys.path` manipulation in the
  entry-point scripts (since we have no `pip install` step). Each script
  in `hooks/` and `skills/.../scripts/` adds `${CLAUDE_PLUGIN_ROOT}/lib`
  to its path before importing.
- All Python code must work with system Python 3.9+ and stdlib only.

## Plugin Manifest Files

### `.claude-plugin/plugin.json`

```json
{
  "name": "living-memory",
  "version": "0.1.0",
  "description": "Query past Claude Code sessions as living memories. Indexes every session and lets the agent ask questions about specific past sessions via claude --resume.",
  "author": {
    "name": "<your name>",
    "email": "<your email>"
  },
  "license": "MIT",
  "repository": "https://github.com/<owner>/living-memory",
  "keywords": ["memory", "session", "context", "history"]
}
```

### `hooks/hooks.json`

```json
{
  "SessionEnd": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/session_end.py"
        }
      ]
    }
  ]
}
```

### `skills/living-memory/SKILL.md`

```markdown
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
```

## Data Schema

### Index file: `~/.claude/.living-memory/index.jsonl`

One JSON object per line, append-only:

```json
{
  "session_id": "abc123-def456-...",
  "started_at": "2026-05-01T14:23:11+03:00",
  "ended_at": "2026-05-01T15:47:02+03:00",
  "cwd": "/Users/guyhod/projects/the-organism",
  "project_name": "the-organism",
  "first_user_msg": "Let's redesign the Health Score formula to weight...",
  "last_assistant_msg": "I've updated agent_orchestrator.py with the new...",
  "files_touched": ["agent_orchestrator.py", "health_score.py"],
  "message_count": 47,
  "transcript_path": "/Users/guyhod/.claude/projects/.../abc123.jsonl"
}
```

**Field rules:**
- `first_user_msg`, `last_assistant_msg`: truncate to 500 chars.
- `files_touched`: dedupe, max 20 entries (most recent).
- `transcript_path`: absolute path so we can re-read if needed.
- All text fields run through `redact()` before being written.

## Implementation Plan

### Phase 0: Plugin scaffolding (30-60 min) — **DO THIS FIRST**

**Goal:** A plugin that installs cleanly, even though it does nothing
useful yet. This is the most important phase because it proves the
distribution path works before you build features on top of it.

**Tasks:**

1. Create the directory structure exactly as in "Repository Layout" above.
   Empty files are fine.

2. Write `.claude-plugin/plugin.json` (template above, fill in author).

3. Write `hooks/hooks.json` (template above, exact contents).

4. Write `hooks/session_end.py` as a no-op stub:
   ```python
   #!/usr/bin/env python3
   import sys, json, os, datetime
   try:
       data = json.load(sys.stdin)
       log_path = os.path.expanduser("~/.claude/.living-memory/hook-debug.log")
       os.makedirs(os.path.dirname(log_path), exist_ok=True)
       with open(log_path, "a") as f:
           f.write(f"{datetime.datetime.now().isoformat()} {json.dumps(data)}\n")
   except Exception:
       pass  # Never block session end
   sys.exit(0)
   ```
   This logs the hook payload to a file so you can see the actual schema.

5. Write `skills/living-memory/SKILL.md` (template above, exact contents).

6. Create `skills/living-memory/scripts/recall.py` and `query_session.py`
   as stubs that print "not implemented" and exit 0.

7. Initialize a git repo, push to GitHub.

8. **Test the install:**
   ```
   /plugin install https://github.com/<owner>/living-memory
   ```
   Restart Claude Code. Run a session, exit it. Check that
   `~/.claude/.living-memory/hook-debug.log` exists and contains the payload.

**Done when:**
- `/plugin install` succeeds without errors.
- After a session ends, the hook fires and writes a debug log.
- The skill appears in Claude Code's skill list.
- Inspecting the debug log reveals the exact JSON schema Claude Code
  sends to SessionEnd hooks. **Save a sample payload — Phase 1 codes
  against it.**

### Phase 1: Real indexing (1-2 hours)

**Goal:** SessionEnd hook writes useful metadata per session.

**Tasks:**

1. `lib/paths.py` — resolve:
   - `~/.claude/projects/` (Claude Code transcript root)
   - `~/.claude/.living-memory/` (our data dir, create if missing)
   - `~/.claude/.living-memory/index.jsonl`

2. **Inspect a real transcript** before writing `transcript.py`:
   ```bash
   ls ~/.claude/projects/
   find ~/.claude/projects -name "*.jsonl" | head -1 | xargs head -3
   ```
   The format has changed between Claude Code versions. Code against
   what you see, not what you remember.

3. `lib/transcript.py` — function `read_transcript(path)`:
   - Reads Claude Code JSONL transcript.
   - Returns list of message dicts.

4. `lib/redact.py` — function `redact(text)`:
   - Simple regex for common secret patterns:
     - `sk-[A-Za-z0-9]{20,}` (API keys)
     - `ghp_[A-Za-z0-9]{36}` (GitHub tokens)
     - `AKIA[0-9A-Z]{16}` (AWS access keys)
     - Generic long tokens: `[A-Za-z0-9_-]{40,}`
   - Replaces with `[REDACTED]`.
   - Conservative: false positives are fine, leaks are not.

5. `lib/indexer.py` — function `index_session(payload)`:
   - Takes the hook payload dict.
   - Reads transcript via `transcript.py`.
   - Extracts schema fields above.
   - Runs redaction pass on text fields.
   - Appends JSON line to `~/.claude/.living-memory/index.jsonl`.

6. Replace `hooks/session_end.py` stub with the real implementation:
   ```python
   #!/usr/bin/env python3
   import sys, os, json
   sys.path.insert(0, os.path.join(os.environ["CLAUDE_PLUGIN_ROOT"], "lib"))
   from indexer import index_session

   try:
       payload = json.load(sys.stdin)
       index_session(payload)
   except Exception as e:
       err_path = os.path.expanduser("~/.claude/.living-memory/errors.log")
       os.makedirs(os.path.dirname(err_path), exist_ok=True)
       with open(err_path, "a") as f:
           f.write(f"{e}\n")
   sys.exit(0)
   ```

**Done when:** You manually exit a Claude Code session and see a new
correctly-formed line in `~/.claude/.living-memory/index.jsonl`.

### Phase 2: Recall (1 hour)

**Goal:** `recall` returns relevant sessions fast.

**Tasks:**

1. `lib/search.py` — function `recall(query, project=None, limit=10, since=None)`:
   - Reads `index.jsonl` (full-file scan is fine for thousands of lines).
   - Filters:
     - `query` (substring, case-insensitive) matches any of:
       `first_user_msg`, `last_assistant_msg`, `files_touched`, `project_name`.
     - `project` (optional) matches `project_name`.
     - `since` (optional ISO date) matches `started_at >= since`.
   - Sorts by `started_at` desc.
   - Returns top `limit`.

2. `skills/living-memory/scripts/recall.py` — CLI wrapper:
   - argparse: positional `query`, optional `--project`, `--limit`, `--since`.
   - Adds `${CLAUDE_PLUGIN_ROOT}/lib` to sys.path, imports `search.recall`.
   - Prints JSON results to stdout.

**Done when:** `python3 skills/living-memory/scripts/recall.py "health score"`
returns sensible results from your real history.

### Phase 3: Query session (1-2 hours)

**Goal:** `query_session` spawns Claude Code on a past session and
returns the answer.

**Pre-flight check (do this before writing code):**

Manually verify `claude --resume` behavior:
```bash
claude --resume <some-real-session-id> -p "What was this session about?"
```

Check:
- Does it print to stdout cleanly?
- Does it require a TTY or interactive confirmation?
- Does it block waiting for input?
- What's the exit code on success / failure?
- Is there a `--output-format json` or `--no-tools` flag worth using?
  Run `claude --help` to find out.

If `claude --resume` doesn't work as a clean subprocess, the architecture
needs to change (fall back to Anthropic API + transcript as context).
**Discover this in 5 minutes, not after writing 200 lines.**

**Tasks:**

1. `lib/query.py` — function `query_session(session_id, question, timeout=120)`:
   - Validates `session_id` exists in index (security: never pass arbitrary
     strings to subprocess).
   - Builds the question with a system suffix:
     ```
     <question>

     Answer based on what we discussed in this session. Do not take
     further actions. Reply with a concise answer only.
     ```
   - Runs: `claude --resume <session_id> -p <question>` via subprocess.
   - Captures stdout, returns it.
   - Handles timeout, missing CLI, non-zero exit.

2. `skills/living-memory/scripts/query_session.py` — CLI wrapper:
   - argparse: positional `session_id`, `question`.
   - Adds lib to sys.path, imports `query.query_session`.
   - Prints answer to stdout.

**Done when:** From an active Claude Code session, you say "use
living-memory to query session X about Y" and get a real answer back.

### Phase 4: Polish & README (30-60 min)

**Tasks:**

1. README with: what it does, install command, quickstart example,
   troubleshooting.
2. `tests/` — at least basic tests for `redact`, `search`, and
   `transcript` parsing.
3. Update `version` in `plugin.json` to `0.1.0` and tag a release.

### Phase 5: Real-world hardening (only after using it for a few days)

- Limit transcript-scan size in `recall` if index gets huge.
- Better error messages when Claude Code CLI isn't on PATH.
- Document the index file format in README so others can extend.
- Consider adding `--no-tools` or similar flag to `query_session` to
  prevent the resumed session from taking actions.

## Critical Implementation Notes

### 1. Test the install path before everything else

Phase 0 exists for one reason: to fail fast if the plugin manifest, hook
registration, or skill discovery is wrong. Don't write business logic
until you can install + uninstall the plugin cleanly.

### 2. `${CLAUDE_PLUGIN_ROOT}` everywhere

Every path reference inside `hooks.json` and inside skill scripts must
use `${CLAUDE_PLUGIN_ROOT}` (or read it via `os.environ`). Never
hardcode `/Users/guyhod/...` or relative paths from cwd.

### 3. Pure stdlib

The constraint is real. If you find yourself wanting `requests`,
`pydantic`, `numpy`, anything — stop and use stdlib. `urllib`, `json`,
plain dicts, plain lists. The reward is `/plugin install` and you're done.

### 4. Hook payload format

Phase 0's debug stub captures the exact payload schema. Don't guess
field names. Read the log, code against what you see.

### 5. `claude --resume` behavior

The whole architecture rests on this command working as a subprocess.
The Phase 3 pre-flight check is non-negotiable. If it doesn't behave,
the fallback (Anthropic API + transcript injection) is more work but
still doable — just better to know on day three than on day seven.

### 6. Avoid these traps

- **Don't add a vector DB.** Substring search will work for thousands of
  sessions. You'll know when it stops working.
- **Don't summarize at SessionEnd.** It costs tokens, slows the hook,
  and the metadata is enough for retrieval. Summarization belongs in
  `query_session`, where Claude Code does it for free.
- **Don't auto-inject context at SessionStart.** Tempting, but pollutes
  the working set and slows session start. Make retrieval explicit.
- **Don't add pip dependencies.** See note 3.
- **Don't try to handle every edge case in v0.** Ship the happy path,
  use it for a week, fix what actually breaks.

## Acceptance Criteria

The project is "done enough to use daily" when:

1. `/plugin install https://github.com/<owner>/living-memory` succeeds
   in a fresh Claude Code instance and the skill is available after
   restart.
2. Every session you finish gets indexed automatically (no manual step).
3. `recall "<word>"` returns useful results from your real history
   within 1 second.
4. From inside Claude Code, you can say "use living-memory to find
   sessions about The Organism's health score" and the agent does it.
5. `query_session` returns an answer in under 30 seconds for a typical
   session.
6. No secrets from your transcripts have leaked into the index file
   (spot-check by grepping for `sk-`, `ghp_`, `AKIA`).

## Future Ideas (Don't Build Yet)

- Embeddings layer for semantic recall (only when grep stops being enough).
- Cross-session synthesis tool (`synthesize(query, session_ids)`).
- Web viewer for the index.
- Optional `marketplace.json` so others can `/plugin marketplace add` you.
- Auto-tagging via lightweight LLM call.
- Decay / archive old sessions.
- `--no-tools` mode for `query_session` so resumed sessions can't act.

These are all reasonable. None of them are needed for the tool to be
valuable to you starting day one.
