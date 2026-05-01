import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from paths import get_index_path, get_living_memory_dir
from transcript import (
    read_transcript,
    extract_user_messages,
    extract_assistant_messages,
    extract_files_touched,
    extract_message_count,
)
from redact import redact


def get_project_name(cwd: str) -> str:
    """Extract project name from cwd path."""
    if not cwd:
        return ""
    # Return last directory component as project name
    return Path(cwd).name


def truncate(text: str, max_len: int = 500) -> str:
    """Truncate text to max_len characters."""
    if not text:
        return ""
    return text[:max_len] if len(text) > max_len else text


def index_session(payload: Dict[str, Any]) -> None:
    """
    Index a session from the SessionEnd hook payload.

    Expected payload fields:
    - sessionId: unique session identifier
    - startedAt: ISO timestamp
    - endedAt: ISO timestamp
    - cwd: current working directory
    - transcript: path to transcript file (optional, will compute if missing)

    Reads the transcript, extracts metadata, redacts secrets, and appends to index.
    """
    session_id = payload.get("sessionId", "unknown")
    started_at = payload.get("startedAt", "")
    ended_at = payload.get("endedAt", "")
    cwd = payload.get("cwd", "")
    transcript_path = payload.get("transcript", "")

    # If transcript path not provided, try to find it
    if not transcript_path:
        transcript_path = find_transcript(session_id, started_at)

    if not transcript_path or not os.path.exists(transcript_path):
        return

    # Read transcript
    messages = read_transcript(transcript_path)
    if not messages:
        return

    # Extract metadata
    user_messages = extract_user_messages(messages)
    assistant_messages = extract_assistant_messages(messages)
    files = extract_files_touched(messages)
    msg_count = extract_message_count(messages)

    # Build index entry
    entry = {
        "session_id": session_id,
        "started_at": started_at,
        "ended_at": ended_at,
        "cwd": redact(cwd),
        "project_name": get_project_name(cwd),
        "first_user_msg": truncate(redact(user_messages[0] if user_messages else "")),
        "last_assistant_msg": truncate(redact(assistant_messages[-1] if assistant_messages else "")),
        "files_touched": [redact(f) for f in files],
        "message_count": msg_count,
        "transcript_path": transcript_path,
    }

    # Append to index file
    index_path = get_index_path()
    try:
        with open(index_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except (IOError, OSError):
        pass


def find_transcript(session_id: str, started_at: Optional[str] = None) -> Optional[str]:
    """
    Attempt to find transcript file for a session.

    Claude Code stores transcripts in ~/.claude/projects/ with structure:
    ~/.claude/projects/<cwd-hash>/<session-id>.jsonl
    """
    from paths import get_transcripts_root

    transcripts_root = get_transcripts_root()
    if not transcripts_root.exists():
        return None

    # Search for transcript file matching session_id
    for project_dir in transcripts_root.iterdir():
        if not project_dir.is_dir():
            continue

        # Look for .jsonl files named <session-id>.jsonl in project dir
        transcript_file = project_dir / f"{session_id}.jsonl"
        if transcript_file.exists():
            return str(transcript_file)

        # Also search subdirectories for .jsonl files
        for jsonl_file in project_dir.glob("*.jsonl"):
            return str(jsonl_file)
        for jsonl_file in project_dir.glob("*/*.jsonl"):
            return str(jsonl_file)

    return None
