import os
from pathlib import Path


def get_claude_home():
    """Get ~/.claude directory."""
    return Path.home() / ".claude"


def get_transcripts_root():
    """Get ~/.claude/projects directory where Claude Code stores transcripts."""
    return get_claude_home() / "projects"


def get_living_memory_dir():
    """Get ~/.claude/.living-memory directory, creating if needed."""
    lm_dir = get_claude_home() / ".living-memory"
    lm_dir.mkdir(parents=True, exist_ok=True)
    return lm_dir


def get_index_path():
    """Get ~/.claude/.living-memory/index.jsonl path."""
    return get_living_memory_dir() / "index.jsonl"


def get_errors_log_path():
    """Get ~/.claude/.living-memory/errors.log path."""
    return get_living_memory_dir() / "errors.log"
