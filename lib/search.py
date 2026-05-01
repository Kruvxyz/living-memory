import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from paths import get_index_path


def recall(
    query: str,
    project: Optional[str] = None,
    limit: int = 10,
    since: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Search the session index for relevant past sessions.

    Filters:
    - query: substring match (case-insensitive) in first_user_msg, last_assistant_msg,
             files_touched, or project_name
    - project: filter by exact project_name match
    - since: ISO date string — only sessions started on or after this date
    - limit: max number of results to return (default 10)

    Returns: list of matching index entries, sorted by started_at (newest first)
    """
    if not query:
        return []

    index_path = get_index_path()
    if not index_path.exists():
        return []

    results = []
    query_lower = query.lower()

    try:
        with open(index_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Filter by project if specified
                if project and entry.get("project_name") != project:
                    continue

                # Filter by date if specified
                if since:
                    try:
                        entry_started = entry.get("started_at", "")
                        if entry_started < since:
                            continue
                    except (TypeError, ValueError):
                        pass

                # Check if query matches any searchable field
                if _matches_query(entry, query_lower):
                    results.append(entry)

    except (IOError, OSError):
        return []

    # Sort by started_at descending (newest first)
    results.sort(key=lambda x: x.get("started_at", ""), reverse=True)

    # Return top limit results
    return results[:limit]


def _matches_query(entry: Dict[str, Any], query_lower: str) -> bool:
    """Check if entry matches the query string (case-insensitive substring)."""
    # Check first user message
    first_msg = entry.get("first_user_msg", "").lower()
    if query_lower in first_msg:
        return True

    # Check last assistant message
    last_msg = entry.get("last_assistant_msg", "").lower()
    if query_lower in last_msg:
        return True

    # Check project name
    project = entry.get("project_name", "").lower()
    if query_lower in project:
        return True

    # Check files touched
    files = entry.get("files_touched", [])
    if isinstance(files, list):
        for filepath in files:
            if isinstance(filepath, str) and query_lower in filepath.lower():
                return True

    return False
