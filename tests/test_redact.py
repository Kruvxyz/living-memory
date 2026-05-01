#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from redact import redact, redact_dict


def test_redact_api_keys():
    """Test OpenAI-style API key redaction."""
    text = "My key is sk-" + "x" * 40
    result = redact(text)
    assert "[REDACTED]" in result
    assert "sk-" not in result or len(result.split("sk-")[1].split()[0]) < 10


def test_redact_github_tokens():
    """Test GitHub token redaction."""
    text = "Token: ghp_" + "y" * 36
    result = redact(text)
    assert "[REDACTED]" in result


def test_redact_aws_keys():
    """Test AWS access key redaction."""
    text = "AWS: AKIA" + "Z" * 16
    result = redact(text)
    assert "[REDACTED]" in result


def test_no_redact_normal_text():
    """Ensure normal text is not redacted."""
    text = "Hello world, this is a test email test@example.com"
    result = redact(text)
    assert result == text


def test_redact_dict():
    """Test recursive dict redaction."""
    obj = {
        "secret": "sk-" + "x" * 40,
        "safe": "hello",
        "nested": {
            "token": "ghp_" + "y" * 36,
        }
    }
    result = redact_dict(obj)
    assert "[REDACTED]" in result["secret"]
    assert result["safe"] == "hello"
    assert "[REDACTED]" in result["nested"]["token"]


if __name__ == "__main__":
    test_redact_api_keys()
    test_redact_github_tokens()
    test_redact_aws_keys()
    test_no_redact_normal_text()
    test_redact_dict()
    print("All redact tests passed!")
