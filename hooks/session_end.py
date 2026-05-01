#!/usr/bin/env python3
import sys, json, os, datetime, select

try:
    log_path = os.path.expanduser("~/.claude/.living-memory/hook-debug.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    data = {}
    ready, _, _ = select.select([sys.stdin], [], [], 3)
    if ready:
        raw = sys.stdin.readline()
        if raw.strip():
            data = json.loads(raw)

    with open(log_path, "a") as f:
        f.write(f"{datetime.datetime.now().isoformat()} {json.dumps(data)}\n")
except Exception:
    pass  # Never block session end

sys.exit(0)
