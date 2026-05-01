#!/usr/bin/env python3
import sys
import os
import json
import argparse

# Add lib to path
lib_path = os.path.join(os.environ.get("CLAUDE_PLUGIN_ROOT", "."), "lib")
sys.path.insert(0, lib_path)

from query import query_session, QueryError, SessionNotFoundError, CLINotFoundError, TimeoutError


def main():
    parser = argparse.ArgumentParser(
        description="Query a past Claude Code session"
    )
    parser.add_argument(
        "session_id",
        help="Session ID (UUID) to resume and query",
    )
    parser.add_argument(
        "question",
        help="The question to ask the resumed session",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Seconds to wait for the query (default 120)",
    )

    args = parser.parse_args()

    try:
        answer = query_session(
            session_id=args.session_id,
            question=args.question,
            timeout=args.timeout,
        )
        print(answer)
    except SessionNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except CLINotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
    except TimeoutError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(3)
    except QueryError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(4)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(5)


if __name__ == "__main__":
    main()
