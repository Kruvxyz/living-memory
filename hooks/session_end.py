#!/usr/bin/env python3
import sys, os, json, select

# Add lib to path so we can import our modules
lib_path = os.path.join(os.environ.get("CLAUDE_PLUGIN_ROOT", "."), "lib")
sys.path.insert(0, lib_path)

from indexer import index_session
from paths import get_errors_log_path

try:
    # Read JSON payload from stdin with timeout
    data = {}
    ready, _, _ = select.select([sys.stdin], [], [], 3)
    if ready:
        raw = sys.stdin.readline()
        if raw.strip():
            data = json.loads(raw)

    # Index the session if we got a payload
    if data:
        index_session(data)
except Exception as e:
    # Log errors but never block session end
    try:
        err_path = get_errors_log_path()
        with open(err_path, "a") as f:
            f.write(f"{str(e)}\n")
    except Exception:
        pass

sys.exit(0)
