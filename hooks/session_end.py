#!/usr/bin/env python3
import sys, json, os, datetime, signal

def _timeout(signum, frame):
    raise TimeoutError

try:
    signal.signal(signal.SIGALRM, _timeout)
    signal.alarm(5)  # 5-second hard deadline
    raw = sys.stdin.read()
    signal.alarm(0)
    data = json.loads(raw)
    log_path = os.path.expanduser("~/.claude/.living-memory/hook-debug.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a") as f:
        f.write(f"{datetime.datetime.now().isoformat()} {json.dumps(data)}\n")
except Exception:
    pass  # Never block session end

sys.exit(0)
