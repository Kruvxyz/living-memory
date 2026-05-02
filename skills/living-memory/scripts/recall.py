#!/usr/bin/env python3
import sys
import os
import json
import argparse

# Add lib to path (resolve from script location if CLAUDE_PLUGIN_ROOT not set)
_PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
lib_path = os.path.join(_PLUGIN_ROOT, "lib")
sys.path.insert(0, lib_path)

from search import recall


def main():
    parser = argparse.ArgumentParser(
        description="Recall past Claude Code sessions by keyword search"
    )
    parser.add_argument(
        "query",
        help="Search query (substring, case-insensitive)",
    )
    parser.add_argument(
        "--project",
        help="Filter by project name",
        default=None,
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Max number of results (default 10)",
    )
    parser.add_argument(
        "--since",
        help="Only sessions started on/after this ISO date (e.g. 2026-05-01)",
        default=None,
    )

    args = parser.parse_args()

    # Run recall
    results = recall(
        query=args.query,
        project=args.project,
        limit=args.limit,
        since=args.since,
    )

    # Output JSON to stdout
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
