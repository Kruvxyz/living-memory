#!/usr/bin/env python3
import sys
import os
import json
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from search import recall, _matches_query


def test_empty_index():
    """Test recall with empty index."""
    import search
    original_get_index_path = search.get_index_path

    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = Path(tmpdir) / "index.jsonl"

        def mock_get_index_path():
            return index_path

        search.get_index_path = mock_get_index_path

        try:
            results = recall("test")
            assert results == []
        finally:
            search.get_index_path = original_get_index_path


def test_recall_basic_query():
    """Test basic recall query matching."""
    import search

    original_get_index_path = search.get_index_path

    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = Path(tmpdir) / "index.jsonl"

        # Write test entries
        with open(index_path, 'w') as f:
            f.write(json.dumps({
                "session_id": "s1",
                "started_at": "2026-05-01T10:00:00+00:00",
                "first_user_msg": "How do I use health score?",
                "last_assistant_msg": "Health score measures organism vitality",
                "files_touched": ["health.py"],
                "project_name": "organism",
            }) + "\n")
            f.write(json.dumps({
                "session_id": "s2",
                "started_at": "2026-05-01T11:00:00+00:00",
                "first_user_msg": "Fix the login bug",
                "last_assistant_msg": "Login fixed",
                "files_touched": ["auth.py"],
                "project_name": "webapp",
            }) + "\n")

        def mock_get_index_path():
            return index_path

        search.get_index_path = mock_get_index_path

        try:
            # Search for "health"
            results = recall("health")
            assert len(results) == 1
            assert results[0]["session_id"] == "s1"

            # Search for "login"
            results = recall("login")
            assert len(results) == 1
            assert results[0]["session_id"] == "s2"

            # Search for non-existent term
            results = recall("xyz123")
            assert len(results) == 0

        finally:
            search.get_index_path = original_get_index_path


def test_recall_project_filter():
    """Test recall with project filter."""
    import search

    original_get_index_path = search.get_index_path

    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = Path(tmpdir) / "index.jsonl"

        # Write test entries
        with open(index_path, 'w') as f:
            f.write(json.dumps({
                "session_id": "s1",
                "started_at": "2026-05-01T10:00:00+00:00",
                "first_user_msg": "bug fix",
                "last_assistant_msg": "fixed",
                "files_touched": [],
                "project_name": "organism",
            }) + "\n")
            f.write(json.dumps({
                "session_id": "s2",
                "started_at": "2026-05-01T11:00:00+00:00",
                "first_user_msg": "bug fix",
                "last_assistant_msg": "fixed",
                "files_touched": [],
                "project_name": "webapp",
            }) + "\n")

        def mock_get_index_path():
            return index_path

        search.get_index_path = mock_get_index_path

        try:
            # Search in all projects
            results = recall("bug")
            assert len(results) == 2

            # Search in organism only
            results = recall("bug", project="organism")
            assert len(results) == 1
            assert results[0]["session_id"] == "s1"

            # Search in webapp only
            results = recall("bug", project="webapp")
            assert len(results) == 1
            assert results[0]["session_id"] == "s2"

        finally:
            search.get_index_path = original_get_index_path


def test_recall_date_filter():
    """Test recall with date filter."""
    import search

    original_get_index_path = search.get_index_path

    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = Path(tmpdir) / "index.jsonl"

        # Write test entries with different dates
        with open(index_path, 'w') as f:
            f.write(json.dumps({
                "session_id": "s1",
                "started_at": "2026-04-01T10:00:00+00:00",
                "first_user_msg": "test",
                "last_assistant_msg": "response",
                "files_touched": [],
                "project_name": "proj",
            }) + "\n")
            f.write(json.dumps({
                "session_id": "s2",
                "started_at": "2026-05-01T10:00:00+00:00",
                "first_user_msg": "test",
                "last_assistant_msg": "response",
                "files_touched": [],
                "project_name": "proj",
            }) + "\n")

        def mock_get_index_path():
            return index_path

        search.get_index_path = mock_get_index_path

        try:
            # All results
            results = recall("test")
            assert len(results) == 2

            # Only since May 1
            results = recall("test", since="2026-05-01T00:00:00+00:00")
            assert len(results) == 1
            assert results[0]["session_id"] == "s2"

        finally:
            search.get_index_path = original_get_index_path


def test_recall_limit():
    """Test recall result limiting."""
    import search

    original_get_index_path = search.get_index_path

    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = Path(tmpdir) / "index.jsonl"

        # Write many test entries
        with open(index_path, 'w') as f:
            for i in range(15):
                f.write(json.dumps({
                    "session_id": f"s{i}",
                    "started_at": f"2026-05-01T{i:02d}:00:00+00:00",
                    "first_user_msg": "test query",
                    "last_assistant_msg": "response",
                    "files_touched": [],
                    "project_name": "proj",
                }) + "\n")

        def mock_get_index_path():
            return index_path

        search.get_index_path = mock_get_index_path

        try:
            # Default limit (10)
            results = recall("test")
            assert len(results) == 10

            # Custom limit
            results = recall("test", limit=5)
            assert len(results) == 5

            # Limit larger than results
            results = recall("test", limit=50)
            assert len(results) == 15

        finally:
            search.get_index_path = original_get_index_path


def test_matches_query():
    """Test query matching logic."""
    entry = {
        "first_user_msg": "How to use health score",
        "last_assistant_msg": "Health score is calculated by...",
        "project_name": "organism",
        "files_touched": ["/path/to/health.py", "/path/to/score.py"],
    }

    # Matches in first_user_msg
    assert _matches_query(entry, "health")

    # Matches in last_assistant_msg
    assert _matches_query(entry, "calculated")

    # Matches in project_name
    assert _matches_query(entry, "organism")

    # Matches in files_touched
    assert _matches_query(entry, "health.py")

    # No match
    assert not _matches_query(entry, "xyz123")


def test_recall_sorting():
    """Test that results are sorted by started_at descending."""
    import search

    original_get_index_path = search.get_index_path

    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = Path(tmpdir) / "index.jsonl"

        # Write entries in random order
        with open(index_path, 'w') as f:
            f.write(json.dumps({
                "session_id": "s2",
                "started_at": "2026-05-02T10:00:00+00:00",
                "first_user_msg": "test",
                "last_assistant_msg": "response",
                "files_touched": [],
                "project_name": "proj",
            }) + "\n")
            f.write(json.dumps({
                "session_id": "s1",
                "started_at": "2026-05-01T10:00:00+00:00",
                "first_user_msg": "test",
                "last_assistant_msg": "response",
                "files_touched": [],
                "project_name": "proj",
            }) + "\n")
            f.write(json.dumps({
                "session_id": "s3",
                "started_at": "2026-05-03T10:00:00+00:00",
                "first_user_msg": "test",
                "last_assistant_msg": "response",
                "files_touched": [],
                "project_name": "proj",
            }) + "\n")

        def mock_get_index_path():
            return index_path

        search.get_index_path = mock_get_index_path

        try:
            results = recall("test")
            # Should be sorted newest first
            assert [r["session_id"] for r in results] == ["s3", "s2", "s1"]

        finally:
            search.get_index_path = original_get_index_path


if __name__ == "__main__":
    test_empty_index()
    test_recall_basic_query()
    test_recall_project_filter()
    test_recall_date_filter()
    test_recall_limit()
    test_matches_query()
    test_recall_sorting()
    print("All search tests passed!")
