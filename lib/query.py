import subprocess
import json
import signal
from typing import Optional
from pathlib import Path

from search import recall
from paths import get_index_path


class QueryError(Exception):
    """Base exception for query_session errors."""
    pass


class SessionNotFoundError(QueryError):
    """Raised when the session ID is not found in the index."""
    pass


class TimeoutError(QueryError):
    """Raised when the query times out."""
    pass


class CLINotFoundError(QueryError):
    """Raised when the claude CLI is not available."""
    pass


def query_session(
    session_id: str,
    question: str,
    timeout: int = 120,
) -> str:
    """
    Query a past session by spawning claude --resume with -p flag.

    Validates that the session_id exists in the index before spawning,
    then builds the question with a system suffix instructing the resumed
    session to answer based only on its context.

    Args:
        session_id: UUID of the session to resume
        question: The question to ask the resumed session
        timeout: Seconds to wait for the subprocess (default 120)

    Returns:
        The answer text from the resumed session

    Raises:
        SessionNotFoundError: If session_id is not in the index
        CLINotFoundError: If claude CLI is not available
        TimeoutError: If the query exceeds timeout seconds
        QueryError: For other errors (non-zero exit, etc.)
    """
    # Validate session exists in index
    _validate_session_exists(session_id)

    # Build the question with system suffix
    full_question = (
        f"{question}\n\n"
        "Answer based on what we discussed in this session. "
        "Do not take further actions. Reply with a concise answer only."
    )

    # Spawn claude --resume <session_id> -p "<question>"
    try:
        result = subprocess.run(
            ["claude", "--resume", session_id, "-p", full_question],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        raise CLINotFoundError(
            "claude CLI not found. Ensure claude is installed and in PATH."
        )
    except subprocess.TimeoutExpired:
        raise TimeoutError(
            f"Query timed out after {timeout} seconds"
        )
    except Exception as e:
        raise QueryError(f"Failed to spawn claude: {e}")

    # Check exit code
    if result.returncode != 0:
        error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
        raise QueryError(
            f"claude --resume exited with code {result.returncode}: {error_msg}"
        )

    # Return the captured output
    return result.stdout.strip()


def _validate_session_exists(session_id: str) -> None:
    """
    Validate that session_id exists in the living-memory index.

    Raises SessionNotFoundError if not found.
    """
    index_path = get_index_path()
    if not index_path.exists():
        raise SessionNotFoundError(
            f"No sessions indexed yet. Index file not found at {index_path}"
        )

    try:
        with open(index_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("session_id") == session_id:
                        return
                except json.JSONDecodeError:
                    continue
    except (IOError, OSError) as e:
        raise SessionNotFoundError(f"Error reading index: {e}")

    raise SessionNotFoundError(
        f"Session {session_id} not found in index"
    )
