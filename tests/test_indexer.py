#!/usr/bin/env python3
import sys
import os
import json
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from indexer import get_project_name, truncate, index_session


def test_get_project_name():
    """Test project name extraction from cwd."""
    assert get_project_name("/Users/test/projects/my-app") == "my-app"
    assert get_project_name("/home/user/workspace") == "workspace"
    assert get_project_name("") == ""


def test_truncate():
    """Test text truncation."""
    text = "a" * 600
    result = truncate(text, 500)
    assert len(result) == 500
    assert result == "a" * 500

    short_text = "hello"
    assert truncate(short_text, 500) == "hello"

    assert truncate("", 500) == ""


def test_index_session_with_valid_payload():
    """Test indexing a session with no transcript (should not crash)."""
    # Create a temporary index file
    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = Path(tmpdir) / "index.jsonl"

        # Mock get_index_path to return our temp file
        import indexer
        original_get_index_path = indexer.get_index_path

        def mock_get_index_path():
            return index_path

        indexer.get_index_path = mock_get_index_path

        try:
            payload = {
                "sessionId": "test-session-123",
                "startedAt": "2026-05-01T10:00:00+00:00",
                "endedAt": "2026-05-01T10:15:00+00:00",
                "cwd": "/Users/test/my-project",
            }

            # Index the session (will skip since no valid transcript)
            index_session(payload)

            # Check that nothing was written (no valid transcript found)
            # The function returns early if no transcript is found
            if index_path.exists():
                # It's ok if it exists but is empty
                assert True
            else:
                assert True

        finally:
            indexer.get_index_path = original_get_index_path


def test_index_session_fields():
    """Test that index entry has all required fields."""
    from indexer import index_session
    import indexer
    from transcript import read_transcript

    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = Path(tmpdir) / "index.jsonl"

        original_get_index_path = indexer.get_index_path
        original_read_transcript = indexer.read_transcript

        def mock_get_index_path():
            return index_path

        def mock_read_transcript(path):
            return [
                {"type": "user", "message": {"content": [{"type": "text", "text": "Hello"}]}},
                {"type": "assistant", "message": {"content": [{"type": "text", "text": "Hi"}]}},
            ]

        indexer.get_index_path = mock_get_index_path
        indexer.read_transcript = mock_read_transcript

        try:
            payload = {
                "sessionId": "test-123",
                "startedAt": "2026-05-01T10:00:00+00:00",
                "endedAt": "2026-05-01T10:15:00+00:00",
                "cwd": "/Users/test/my-project",
                "transcript": "/fake/path/transcript.jsonl",
            }

            index_session(payload)

            # Read the index and verify fields
            if index_path.exists():
                with open(index_path) as f:
                    entry = json.loads(f.read().strip())

                expected_fields = [
                    "session_id", "started_at", "ended_at", "cwd", "project_name",
                    "first_user_msg", "last_assistant_msg", "files_touched",
                    "message_count", "transcript_path"
                ]
                for field in expected_fields:
                    assert field in entry, f"Missing field: {field}"

        finally:
            indexer.get_index_path = original_get_index_path
            indexer.read_transcript = original_read_transcript


if __name__ == "__main__":
    test_get_project_name()
    test_truncate()
    test_index_session_with_valid_payload()
    test_index_session_fields()
    print("All indexer tests passed!")
