"""
run_quote_supervisor.py — READ-ONLY supervisor that runs consecutive bounded XAUUSD quote
sessions with minimal gaps by WRAPPING the already-tested recorder (run_q4b_observer). It does
NOT re-implement capture, alter the quote protocol/schema, or introduce any order path.

Per cycle: token preflight (no secret printed, never mints) -> refuse if any recorder is already
running -> unique deterministic session id -> run ONE bounded session -> write per-session manifest
-> measure the gap since the previous session -> append-only failure log -> bounded retries
(<=3, fixed backoff). Stops safely when data/quote_sessions/STOP exists or --max-sessions is hit.

Usage:  .venv-ctrader\\Scripts\\python.exe run_quote_supervisor.py --session-seconds 900 --max-sessions 8
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_A2 = os.path.dirname(_HERE)
_CE = os.path.dirname(_A2)
_ROOT = os.path.dirname(_CE)

SESSIONS_DIR = os.path.join(_ROOT, "data", "quote_sessions")
STOP_FILE = os.path.join(SESSIONS_DIR, "STOP")
FAILURE_LOG = os.path.join(SESSIONS_DIR, "supervisor_failures.jsonl")
SESSION_LOG = os.path.join(SESSIONS_DIR, "supervisor_sessions.jsonl")
TOKEN_PATH = os.path.join(_ROOT, "data", "ctrader_token.json")
VENV_PY = os.path.join(_ROOT, ".venv-ctrader", "Scripts", "python.exe")
OBSERVER = os.path.join(_HERE, "run_q4b_observer.py")
MAX_RETRIES = 3
BACKOFF_SECONDS = 30


def token_preflight(path=TOKEN_PATH, now=None):
    """(ok, reason, days_remaining) — never prints or returns the secret; never mints."""
    if not os.path.exists(path):
        return False, "NO_TOKEN_FILE", None
    try:
        tok = json.load(open(path, encoding="utf-8"))
    except Exception:
        return False, "TOKEN_UNREADABLE", None
    if not tok.get("access_token"):
        return False, "NO_ACCESS_TOKEN", None
    saved, exp_in = tok.get("saved_at_utc"), tok.get("expires_in")
    if not saved or exp_in is None:
        return True, "USABLE_EXPIRY_UNKNOWN", None      # present + has token; expiry not encoded
    now = now if now is not None else datetime.now(timezone.utc).timestamp()
    saved_ts = datetime.fromisoformat(str(saved).replace("Z", "+00:00")).timestamp()
    remain = saved_ts + float(exp_in) - now
    return (remain > 120), ("USABLE" if remain > 120 else "EXPIRED"), round(remain / 86400, 2)


def make_session_id(now_iso):
    return "prospective-" + now_iso.replace("-", "").replace(":", "").replace("Z", "Z")


def recorder_running():
    """True if a quote-recorder process is already running (overlap guard). Live default."""
    try:
        out = subprocess.run(["powershell", "-NonInteractive", "-Command",
            "(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
            "Where-Object { $_.CommandLine -match 'run_q4b_observer|subscribe_and_capture' } | "
            "Measure-Object).Count"], capture_output=True, text=True, timeout=30)
        return out.stdout.strip().split("\n")[-1].strip() not in ("", "0")
    except Exception:
        return False


def _run_observer_live(session_id, manifest_path, session_seconds):
    """Default runner: invoke the tested bounded recorder as a subprocess under .venv-ctrader."""
    r = subprocess.run([VENV_PY, OBSERVER, session_id, manifest_path, str(session_seconds)],
                       capture_output=True, text=True)
    ok = r.returncode == 0 and "CAPTURE_COMPLETE" in (r.stdout or "")
    return {"ok": ok, "returncode": r.returncode, "stdout": (r.stdout or "").strip()[-300:]}


def _append(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, default=str) + "\n")


def supervise(*, max_sessions=8, session_seconds=900, runner=_run_observer_live,
              is_running=recorder_running, now_fn=None, sleep_fn=time.sleep,
              stop_file=STOP_FILE, failure_log=FAILURE_LOG, session_log=SESSION_LOG,
              max_retries=MAX_RETRIES, backoff=BACKOFF_SECONDS, token_path=TOKEN_PATH):
    """Sequential bounded sessions. Returns a summary dict. All side-channels injectable for tests."""
    now_fn = now_fn or (lambda: datetime.now(timezone.utc).timestamp())
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    summary = {"sessions_run": 0, "sessions_ok": 0, "sessions_failed": 0, "stopped_reason": None,
               "gaps_seconds": [], "session_ids": []}
    prev_end = None
    while summary["sessions_run"] < max_sessions:
        if os.path.exists(stop_file):
            summary["stopped_reason"] = "STOP_FILE"; break
        ok, reason, days = token_preflight(token_path, now=now_fn())
        if not ok:
            _append(failure_log, {"event": "PREFLIGHT_FAILED", "reason": reason, "at": now_fn()})
            summary["stopped_reason"] = f"PREFLIGHT_{reason}"; break
        if is_running():
            _append(failure_log, {"event": "OVERLAP_REFUSED", "at": now_fn()})
            summary["stopped_reason"] = "RECORDER_ALREADY_RUNNING"; break

        start_ts = now_fn()
        gap = (start_ts - prev_end) if prev_end is not None else None
        if gap is not None:
            summary["gaps_seconds"].append(round(gap, 3))
        now_iso = datetime.fromtimestamp(start_ts, tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        sid = "prospective-" + now_iso
        manifest = os.path.join(SESSIONS_DIR, f"{sid}.json")

        result, attempts = None, 0
        while attempts <= max_retries:
            result = runner(sid, manifest, session_seconds)
            if result.get("ok"):
                break
            attempts += 1
            _append(failure_log, {"event": "SESSION_FAILED", "session_id": sid, "attempt": attempts,
                                  "detail": result, "at": now_fn()})
            if attempts > max_retries:
                break
            sleep_fn(backoff)
        summary["sessions_run"] += 1
        summary["session_ids"].append(sid)
        _append(session_log, {"session_id": sid, "ok": bool(result and result.get("ok")),
                              "attempts": attempts, "gap_before_seconds": gap, "at": now_fn()})
        if result and result.get("ok"):
            summary["sessions_ok"] += 1
        else:
            summary["sessions_failed"] += 1
            summary["stopped_reason"] = "RETRIES_EXHAUSTED"; break
        prev_end = now_fn()
    if summary["stopped_reason"] is None:
        summary["stopped_reason"] = "MAX_SESSIONS"
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session-seconds", type=int, default=900)
    ap.add_argument("--max-sessions", type=int, default=8)
    args = ap.parse_args()
    ok, reason, days = token_preflight()
    print(f"token preflight: {reason} (days_remaining={days})")
    if not ok:
        print("STOP: token not usable — no mint performed."); return 2
    print(f"supervising: up to {args.max_sessions} x {args.session_seconds}s sessions "
          f"(stop file: {STOP_FILE})")
    s = supervise(max_sessions=args.max_sessions, session_seconds=args.session_seconds)
    print(json.dumps(s, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
