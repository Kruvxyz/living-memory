import re


def redact(text: str) -> str:
    """
    Redact secrets from text using conservative regex patterns.
    Replaces matches with [REDACTED].

    Patterns:
    - API keys: sk-[A-Za-z0-9]{20,}
    - GitHub tokens: ghp_[A-Za-z0-9]{36}
    - AWS access keys: AKIA[0-9A-Z]{16}
    - Generic long tokens: [A-Za-z0-9_-]{40,}
    """
    if not isinstance(text, str):
        return str(text)

    # API keys (OpenAI-style)
    text = re.sub(r'sk-[A-Za-z0-9]{20,}', '[REDACTED]', text)

    # GitHub tokens
    text = re.sub(r'ghp_[A-Za-z0-9]{36}', '[REDACTED]', text)

    # AWS access keys
    text = re.sub(r'AKIA[0-9A-Z]{16}', '[REDACTED]', text)

    # Generic long tokens (40+ alphanumeric, underscore, or dash)
    # More conservative: only redact if clearly token-like (mixed case or underscores)
    text = re.sub(r'[A-Za-z0-9_-]{40,}(?:[A-Z]|_|[a-z]{2,}[A-Z]|[A-Z]{2,})', '[REDACTED]', text)

    return text


def redact_dict(obj):
    """
    Recursively redact secrets from a dict or list.
    Returns new object with redacted strings.
    """
    if isinstance(obj, str):
        return redact(obj)
    elif isinstance(obj, dict):
        return {k: redact_dict(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [redact_dict(item) for item in obj]
    else:
        return obj
