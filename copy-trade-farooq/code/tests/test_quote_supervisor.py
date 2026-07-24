"""Focused tests for run_quote_supervisor.py — overlap guard, stop-file, retry cap, read-only.
All injectable seams mocked; NO live cTrader connection, NO real recorder invoked."""
from __future__ import annotations
import json
import os
import sys
import tempfile

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_QUOTES = os.path.join(_ROOT, "campaign_extractor", "ctrader_a2", "quotes")
for p in (_ROOT, _QUOTES, os.path.join(_ROOT, "campaign_extractor")):
    if p not in sys.path:
        sys.path.insert(0, p)

import run_quote_supervisor as S


class Clock:
    def __init__(self, start=1782000000.0, step=1.0):
        self.t = start
        self.step = step

    def __call__(self):
        self.t += self.step
        return self.t


def _token(tmp, usable=True):
    p = os.path.join(tmp, "tok.json")
    # saved recently + huge lifetime => usable; tiny lifetime => expired
    json.dump({"access_token": "x" * 10, "saved_at_utc": "2026-07-01T00:00:00Z",
               "expires_in": (10 ** 9 if usable else 10)}, open(p, "w"))
    return p


def _paths(tmp):
    return {"stop_file": os.path.join(tmp, "STOP"), "failure_log": os.path.join(tmp, "fail.jsonl"),
            "session_log": os.path.join(tmp, "sess.jsonl"), "token_path": _token(tmp)}


def _ok_runner(sid, man, secs):
    return {"ok": True, "returncode": 0, "stdout": "CAPTURE_COMPLETE"}


def _fail_runner(sid, man, secs):
    return {"ok": False, "returncode": 1, "stdout": "ERROR"}


def _run(fn):
    tmp = tempfile.mkdtemp(prefix="sup_")
    try:
        return fn(tmp)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def test_overlap_refused():
    def f(tmp):
        s = S.supervise(max_sessions=3, session_seconds=900, runner=_ok_runner,
                        is_running=lambda: True, now_fn=Clock(), sleep_fn=lambda _x: None, **_paths(tmp))
        assert s["sessions_run"] == 0 and s["stopped_reason"] == "RECORDER_ALREADY_RUNNING"
    _run(f)


def test_stop_file_halts():
    def f(tmp):
        pths = _paths(tmp)
        open(pths["stop_file"], "w").write("stop")
        s = S.supervise(max_sessions=3, session_seconds=900, runner=_ok_runner,
                        is_running=lambda: False, now_fn=Clock(), sleep_fn=lambda _x: None, **pths)
        assert s["sessions_run"] == 0 and s["stopped_reason"] == "STOP_FILE"
    _run(f)


def test_retry_limit_bounded():
    def f(tmp):
        pths = _paths(tmp)
        s = S.supervise(max_sessions=5, session_seconds=900, runner=_fail_runner,
                        is_running=lambda: False, now_fn=Clock(), sleep_fn=lambda _x: None,
                        max_retries=3, backoff=0, **pths)
        assert s["sessions_failed"] == 1 and s["stopped_reason"] == "RETRIES_EXHAUSTED"
        fails = [json.loads(l) for l in open(pths["failure_log"], encoding="utf-8")]
        # 4 SESSION_FAILED entries = initial + 3 retries (bounded, not infinite)
        assert sum(1 for x in fails if x["event"] == "SESSION_FAILED") == 4
    _run(f)


def test_max_sessions_honoured():
    def f(tmp):
        s = S.supervise(max_sessions=3, session_seconds=900, runner=_ok_runner,
                        is_running=lambda: False, now_fn=Clock(), sleep_fn=lambda _x: None, **_paths(tmp))
        assert s["sessions_run"] == 3 and s["sessions_ok"] == 3 and s["stopped_reason"] == "MAX_SESSIONS"
    _run(f)


def test_deterministic_unique_session_ids():
    def f(tmp):
        s = S.supervise(max_sessions=4, session_seconds=900, runner=_ok_runner,
                        is_running=lambda: False, now_fn=Clock(step=2.0), sleep_fn=lambda _x: None, **_paths(tmp))
        ids = s["session_ids"]
        assert len(ids) == 4 and len(set(ids)) == 4 and all(i.startswith("prospective-") for i in ids)
    _run(f)


def test_gap_measurement_recorded():
    def f(tmp):
        s = S.supervise(max_sessions=3, session_seconds=900, runner=_ok_runner,
                        is_running=lambda: False, now_fn=Clock(step=5.0), sleep_fn=lambda _x: None, **_paths(tmp))
        assert len(s["gaps_seconds"]) == 2 and all(g >= 0 for g in s["gaps_seconds"])
    _run(f)


def test_preflight_expired_token_stops():
    def f(tmp):
        pths = _paths(tmp)
        pths["token_path"] = _token(tmp, usable=False)
        s = S.supervise(max_sessions=3, session_seconds=900, runner=_ok_runner,
                        is_running=lambda: False, now_fn=lambda: 9.9e9, sleep_fn=lambda _x: None, **pths)
        assert s["sessions_run"] == 0 and s["stopped_reason"].startswith("PREFLIGHT_")
    _run(f)


def test_token_preflight_no_secret_leak():
    def f(tmp):
        ok, reason, days = S.token_preflight(_token(tmp), now=1782000100.0)
        assert ok is True and reason == "USABLE" and isinstance(days, float)
        # returns only (ok, reason, days) — no token material
        assert "x" not in str((ok, reason, days))
    _run(f)


def test_no_order_or_execution_code():
    from broker_readonly.source_scan import scan_no_order_code
    assert scan_no_order_code([_QUOTES]) == []


def test_read_only_no_quote_db_write():
    # the supervisor itself only appends to its own logs + invokes an injected runner;
    # with a mock runner it must not create or touch ctrader_quotes_v1.db
    def f(tmp):
        before = os.path.getmtime(os.path.join(_ROOT, "data", "ctrader_quotes_v1.db"))
        S.supervise(max_sessions=2, session_seconds=900, runner=_ok_runner, is_running=lambda: False,
                    now_fn=Clock(), sleep_fn=lambda _x: None, **_paths(tmp))
        after = os.path.getmtime(os.path.join(_ROOT, "data", "ctrader_quotes_v1.db"))
        assert before == after
    _run(f)
