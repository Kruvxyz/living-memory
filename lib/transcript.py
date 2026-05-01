import json
from typing import List, Dict, Any


def read_transcript(path: str) -> List[Dict[str, Any]]:
    """
    Read a Claude Code JSONL transcript file and return list of message objects.

    Each line is a JSON object representing a message, tool call, or metadata event.
    Returns only the parsed objects; skips any invalid lines.
    """
    messages = []
    try:
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    messages.append(obj)
                except json.JSONDecodeError:
                    continue
    except (IOError, OSError):
        return []

    return messages


def extract_user_messages(messages: List[Dict[str, Any]]) -> List[str]:
    """Extract text content from user messages in transcript."""
    user_texts = []
    for msg in messages:
        if msg.get("type") == "user":
            content = msg.get("message", {}).get("content", "")
            # Content can be either string or list
            if isinstance(content, str) and content:
                user_texts.append(content)
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text = item.get("text", "")
                        if text:
                            user_texts.append(text)
    return user_texts


def extract_assistant_messages(messages: List[Dict[str, Any]]) -> List[str]:
    """Extract text content from assistant messages in transcript."""
    assistant_texts = []
    for msg in messages:
        if msg.get("type") == "assistant":
            content = msg.get("message", {}).get("content", "")
            # Content can be either string or list
            if isinstance(content, str) and content:
                assistant_texts.append(content)
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text = item.get("text", "")
                        if text:
                            assistant_texts.append(text)
    return assistant_texts


def extract_files_touched(messages: List[Dict[str, Any]]) -> List[str]:
    """
    Extract file paths from tool calls and file edits in transcript.
    Returns deduplicated list of files, max 20 most recent.
    """
    files = []
    seen = set()

    for msg in messages:
        # Check for attachment type (edited files)
        if msg.get("type") == "attachment":
            attachment = msg.get("attachment", {})
            if attachment.get("type") == "edited_text_file":
                filename = attachment.get("filename", "")
                if filename and filename not in seen:
                    files.append(filename)
                    seen.add(filename)

        # Check for Read/Write/Edit tool calls
        if msg.get("type") == "assistant":
            content = msg.get("message", {}).get("content", [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "tool_use":
                        tool_name = item.get("name", "")
                        tool_input = item.get("input", {})

                        # Extract file paths from common tools
                        if tool_name in ("Read", "Write", "Edit"):
                            file_path = tool_input.get("file_path", "")
                            if file_path and file_path not in seen:
                                files.append(file_path)
                                seen.add(file_path)

    # Keep most recent 20
    return files[-20:] if len(files) > 20 else files


def extract_message_count(messages: List[Dict[str, Any]]) -> int:
    """Count user + assistant messages (not tool calls or metadata)."""
    count = 0
    for msg in messages:
        if msg.get("type") in ("user", "assistant"):
            count += 1
    return count


def extract_timestamps(messages: List[Dict[str, Any]]) -> tuple[str, str]:
    """
    Extract session start and end timestamps from transcript.

    Returns (started_at, ended_at) ISO 8601 strings.
    Uses first and last entry timestamps if available.
    """
    started_at = ""
    ended_at = ""

    # Find first timestamp (session start)
    for msg in messages:
        ts = msg.get("timestamp", "")
        if ts:
            started_at = ts
            break

    # Find last timestamp (session end)
    for msg in reversed(messages):
        ts = msg.get("timestamp", "")
        if ts:
            ended_at = ts
            break

    return started_at, ended_at
