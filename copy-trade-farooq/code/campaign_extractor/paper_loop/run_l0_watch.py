"""L0 controlled-observation watcher. Polls for a new FAROUK Gold candidate until one appears or
the window ends. Read-only on the listener DB; writes only append-only pending candidates; never
confirms/orders. argv: <max_seconds> <poll_seconds>."""
from __future__ import annotations
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import live_bridge as lb


def main():
    max_s = int(sys.argv[1]) if len(sys.argv) > 1 else 3600
    poll = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    print(f"L0 watch start {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} "
          f"window={max_s}s poll={poll}s watermark={lb._load_watermark()}")
    r = lb.watch(max_seconds=max_s, poll_seconds=poll)
    print("L0 watch result:", json.dumps(r, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
