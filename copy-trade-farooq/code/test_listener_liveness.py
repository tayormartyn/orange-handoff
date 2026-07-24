"""Tests for the listener heartbeat monitor (ADD-2, D-081).
Run: python test_listener_liveness.py"""
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import listener_liveness as L  # noqa: E402

_p = _f = 0
def check(name, cond):
    global _p, _f
    print(("  ok  " if cond else "FAIL  ") + name)
    _p += bool(cond); _f += (not cond)

NOW = 1_000_000.0
ALIVE = lambda pid: True
DEAD = lambda pid: False

def hb(ts, pid=111, connected=True, last_id=46007, last_ts="2026-07-22T06:31:15Z"):
    return {"ts": ts, "pid": pid, "connected": connected, "last_msg_id": last_id, "last_msg_ts": last_ts}

# --- the two failure modes must both ALARM ---
# (a) process dead
check("(a) process dead -> ALARM LISTENER_PROCESS_DOWN",
      L.assess_listener(hb(NOW), NOW, DEAD)["code"] == "LISTENER_PROCESS_DOWN")
# (b) alive but not receiving: stale heartbeat
v = L.assess_listener(hb(NOW - 400), NOW, ALIVE)   # 400s > 300s stale bound
check("(b1) alive+stale heartbeat -> ALARM HEARTBEAT_STALE", v["code"] == "HEARTBEAT_STALE" and v["level"] == "ALARM")
# (b) alive but connected=False (silent disconnect that did not exit)
check("(b2) alive+connected=False -> ALARM LISTENER_DISCONNECTED",
      L.assess_listener(hb(NOW, connected=False), NOW, ALIVE)["code"] == "LISTENER_DISCONNECTED")

# --- ABSENCE must alarm, never read healthy from silence ---
check("MISSING heartbeat (None) -> ALARM HEARTBEAT_ABSENT (absence alarms)",
      L.assess_listener(None, NOW, ALIVE)["code"] == "HEARTBEAT_ABSENT")

# --- healthy steady state ---
v = L.assess_listener(hb(NOW - 30), NOW, ALIVE)
check("fresh+connected+alive -> HEALTHY", v["level"] == "HEALTHY" and v["code"] == "OK")

# --- NO CRY WOLF: long message-silence but heartbeat fresh+connected -> HEALTHY ---
# last message 20h ago (legit weekend-scale quiet) but heartbeat is 30s old & connected.
quiet = hb(NOW - 30, last_ts="2026-07-21T10:00:00Z", last_id=46007)
v = L.assess_listener(quiet, NOW, ALIVE)
check("quiet session (20h no message) but healthy heartbeat -> HEALTHY (no cry wolf)",
      v["level"] == "HEALTHY")

# --- MONITOR-OF-THE-MONITOR: intake_observer down must be caught independently ---
check("intake_observer DOWN -> ALARM MONITOR_DOWN", L.assess_monitor(False)["code"] == "MONITOR_DOWN")
check("intake_observer up -> HEALTHY", L.assess_monitor(True)["level"] == "HEALTHY")

# --- the backstop scenario the operator required: kill observer, heartbeat goes stale ---
# observer down (flag can't be written) AND heartbeat now stale -> BOTH alarm; neither reads healthy.
mon = L.assess_monitor(False)
lst = L.assess_listener(hb(NOW - 999), NOW, ALIVE)
check("observer-down + stale-heartbeat -> BOTH ALARM (silence never healthy)",
      mon["level"] == "ALARM" and lst["level"] == "ALARM")

# --- heartbeat write/read round-trip is atomic + complete ---
with tempfile.TemporaryDirectory() as td:
    p = os.path.join(td, "hb.json")
    L.write_heartbeat(40104, True, 46007, "2026-07-22T06:31:15Z", path=p)
    r = L.read_heartbeat(p)
    check("write/read heartbeat round-trip", r and r["pid"] == 40104 and r["connected"] is True)
    check("read of missing file -> None (treated as absence/alarm upstream)",
          L.read_heartbeat(os.path.join(td, "nope.json")) is None)

# --- INTEGRATION: the operator brief (pull backstop) must RAISE a loud banner when the observer
#     is down AND the heartbeat is stale — the exact monitor-of-the-monitor scenario. Proven via
#     brain_refresh.render_liveness (no live services touched). ---
import importlib.util
_bp = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "research", "farouk_pilot", "orange_brain", "brain_refresh.py")
_spec = importlib.util.spec_from_file_location("brf", _bp)
_brf = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_brf)

lst_stale = L.assess_listener(hb(NOW - 999), NOW, ALIVE)   # process alive but heartbeat stale
mon_down = L.assess_monitor(False)
banner, summary = _brf.render_liveness(lst_stale, mon_down, flag_present=False)
check("brief backstop: observer-down + stale-heartbeat -> LOUD banner with BOTH alarms",
      "CAPTURE GAP" in banner and "MONITOR-OF-THE-MONITOR" in banner)
check("brief backstop: healthy -> no alarm banner",
      _brf.render_liveness(L.assess_listener(hb(NOW - 20), NOW, ALIVE), L.assess_monitor(True), False)[0] == "")
check("brief backstop: heartbeat-absent WARN is surfaced (not silent-healthy)",
      "[!]" in _brf.render_liveness({"level": "WARN", "code": "HEARTBEAT_NOT_ACTIVE", "reason": "x"},
                                    L.assess_monitor(True), False)[1])

print(f"\n{_p} passed, {_f} failed")
sys.exit(1 if _f else 0)
