#!/usr/bin/env python3
import sys, os, datetime

try:
    log_path = os.path.expanduser("~/.claude/.living-memory/hook-debug.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a") as f:
        f.write(f"{datetime.datetime.now().isoformat()} hook fired\n")
except Exception:
    pass

sys.exit(0)
