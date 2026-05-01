#!/usr/bin/env python3
import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from transcript import (
    read_transcript,
    extract_user_messages,
    extract_assistant_messages,
    extract_files_touched,
    extract_message_count,
)


def test_read_empty_transcript():
    """Test reading an empty transcript file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        temp_path = f.name

    try:
        messages = read_transcript(temp_path)
        assert messages == []
    finally:
        os.unlink(temp_path)


def test_read_transcript_with_messages():
    """Test reading a transcript with actual messages."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write(json.dumps({"type": "user", "message": {"content": [{"type": "text", "text": "Hello"}]}}) + "\n")
        f.write(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Hi there"}]}}) + "\n")
        temp_path = f.name

    try:
        messages = read_transcript(temp_path)
        assert len(messages) == 2
        assert messages[0]["type"] == "user"
        assert messages[1]["type"] == "assistant"
    finally:
        os.unlink(temp_path)


def test_extract_user_messages():
    """Test extracting user message text."""
    messages = [
        {"type": "user", "message": {"content": [{"type": "text", "text": "First user msg"}]}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "Response"}]}},
        {"type": "user", "message": {"content": [{"type": "text", "text": "Second user msg"}]}},
    ]
    result = extract_user_messages(messages)
    assert len(result) == 2
    assert result[0] == "First user msg"
    assert result[1] == "Second user msg"


def test_extract_assistant_messages():
    """Test extracting assistant message text."""
    messages = [
        {"type": "user", "message": {"content": [{"type": "text", "text": "User msg"}]}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "First response"}]}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "Second response"}]}},
    ]
    result = extract_assistant_messages(messages)
    assert len(result) == 2
    assert result[0] == "First response"
    assert result[1] == "Second response"


def test_extract_files_touched():
    """Test extracting file paths from tool calls."""
    messages = [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Read",
                        "input": {"file_path": "/path/to/file.py"}
                    }
                ]
            }
        },
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Write",
                        "input": {"file_path": "/path/to/other.py"}
                    }
                ]
            }
        },
    ]
    result = extract_files_touched(messages)
    assert "/path/to/file.py" in result
    assert "/path/to/other.py" in result


def test_extract_message_count():
    """Test message counting."""
    messages = [
        {"type": "user"},
        {"type": "assistant"},
        {"type": "tool_result"},
        {"type": "user"},
        {"type": "assistant"},
    ]
    result = extract_message_count(messages)
    assert result == 4  # 2 user + 2 assistant, not tool_result


if __name__ == "__main__":
    test_read_empty_transcript()
    test_read_transcript_with_messages()
    test_extract_user_messages()
    test_extract_assistant_messages()
    test_extract_files_touched()
    test_extract_message_count()
    print("All transcript tests passed!")
