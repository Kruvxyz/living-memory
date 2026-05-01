#!/usr/bin/env python3
import sys
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, ANY

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from query import (
    query_session,
    _validate_session_exists,
    SessionNotFoundError,
    CLINotFoundError,
    TimeoutError as QueryTimeoutError,
    QueryError,
)


def test_validate_session_exists():
    """Test that _validate_session_exists checks the index correctly."""
    import query

    original_get_index_path = query.get_index_path

    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = Path(tmpdir) / "index.jsonl"

        # Write test entry
        with open(index_path, 'w') as f:
            f.write(json.dumps({
                "session_id": "abc123-test",
                "started_at": "2026-05-01T10:00:00+00:00",
                "first_user_msg": "test",
                "last_assistant_msg": "test",
                "files_touched": [],
                "project_name": "test",
            }) + "\n")

        def mock_get_index_path():
            return index_path

        query.get_index_path = mock_get_index_path

        try:
            # Should not raise
            _validate_session_exists("abc123-test")

            # Should raise SessionNotFoundError
            try:
                _validate_session_exists("nonexistent-id")
                assert False, "Should have raised SessionNotFoundError"
            except SessionNotFoundError:
                pass

        finally:
            query.get_index_path = original_get_index_path


def test_validate_session_no_index():
    """Test that _validate_session_exists raises when index doesn't exist."""
    import query

    original_get_index_path = query.get_index_path

    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = Path(tmpdir) / "nonexistent.jsonl"

        def mock_get_index_path():
            return index_path

        query.get_index_path = mock_get_index_path

        try:
            try:
                _validate_session_exists("any-id")
                assert False, "Should have raised SessionNotFoundError"
            except SessionNotFoundError:
                pass
        finally:
            query.get_index_path = original_get_index_path


@patch('query.subprocess.run')
@patch('query._validate_session_exists')
def test_query_session_success(mock_validate, mock_run):
    """Test successful query_session execution."""
    mock_validate.return_value = None
    mock_run.return_value = Mock(returncode=0, stdout="This is the answer", stderr="")

    answer = query_session("test-session-id", "What happened?")

    assert answer == "This is the answer"
    mock_validate.assert_called_once_with("test-session-id")
    mock_run.assert_called_once()

    # Check that the command was constructed correctly
    call_args = mock_run.call_args
    assert call_args[0][0][0] == "claude"
    assert call_args[0][0][1] == "--resume"
    assert call_args[0][0][2] == "test-session-id"
    assert call_args[0][0][3] == "-p"
    question_arg = call_args[0][0][4]
    assert "What happened?" in question_arg
    assert "Do not take further actions" in question_arg


@patch('query.subprocess.run')
@patch('query._validate_session_exists')
def test_query_session_validation_failure(mock_validate, mock_run):
    """Test query_session when session validation fails."""
    mock_validate.side_effect = SessionNotFoundError("Session not found")

    try:
        query_session("nonexistent-id", "test question")
        assert False, "Should have raised SessionNotFoundError"
    except SessionNotFoundError:
        pass

    mock_run.assert_not_called()


@patch('query.subprocess.run')
@patch('query._validate_session_exists')
def test_query_session_cli_not_found(mock_validate, mock_run):
    """Test query_session when claude CLI is not available."""
    mock_validate.return_value = None
    mock_run.side_effect = FileNotFoundError("claude not found")

    try:
        query_session("test-id", "test question")
        assert False, "Should have raised CLINotFoundError"
    except CLINotFoundError as e:
        assert "claude CLI not found" in str(e)


@patch('query.subprocess.run')
@patch('query._validate_session_exists')
def test_query_session_timeout(mock_validate, mock_run):
    """Test query_session timeout handling."""
    import subprocess
    mock_validate.return_value = None
    mock_run.side_effect = subprocess.TimeoutExpired("cmd", 120)

    try:
        query_session("test-id", "test question", timeout=120)
        assert False, "Should have raised TimeoutError"
    except QueryTimeoutError as e:
        assert "timed out after 120 seconds" in str(e)


@patch('query.subprocess.run')
@patch('query._validate_session_exists')
def test_query_session_non_zero_exit(mock_validate, mock_run):
    """Test query_session handling non-zero exit codes."""
    mock_validate.return_value = None
    mock_run.return_value = Mock(
        returncode=1,
        stdout="",
        stderr="Session error: something went wrong"
    )

    try:
        query_session("test-id", "test question")
        assert False, "Should have raised QueryError"
    except QueryError as e:
        assert "exited with code 1" in str(e)
        assert "something went wrong" in str(e)


if __name__ == "__main__":
    # Run tests
    import traceback

    tests = [
        ("test_validate_session_exists", test_validate_session_exists),
        ("test_validate_session_no_index", test_validate_session_no_index),
        ("test_query_session_success", test_query_session_success),
        ("test_query_session_validation_failure", test_query_session_validation_failure),
        ("test_query_session_cli_not_found", test_query_session_cli_not_found),
        ("test_query_session_timeout", test_query_session_timeout),
        ("test_query_session_non_zero_exit", test_query_session_non_zero_exit),
    ]

    failed = 0
    for name, test_func in tests:
        try:
            test_func()
            print(f"✓ {name}")
        except Exception as e:
            print(f"✗ {name}")
            traceback.print_exc()
            failed += 1

    if failed:
        print(f"\n{failed} test(s) failed")
        sys.exit(1)
    else:
        print("\nAll tests passed!")
        sys.exit(0)
