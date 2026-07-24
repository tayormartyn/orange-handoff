"""Listener heartbeat + liveness assessment (ADD-2, D-081; third silent-absence preventer).

CORE PRINCIPLE: absence must ALARM, never read 'healthy' from silence. A MISSING or STALE
heartbeat is treated the same as an explicit down signal.

Used by BOTH:
  * the CONTINUOUS monitor (intake_observer poll loop) -> writes data/LISTENER_DOWN.flag; and
  * the PULL-BASED BACKSTOP (operator brief / ORANGE_STATUS) which re-derives everything from
    the OS + the heartbeat file, trusting NO always-on process (so a dead monitor cannot hide
    a dead listener -- the monitor-of-the-monitor gap).

Message-silence is deliberately NOT a hard trigger: observed legitimate silence reaches ~24h
(weekends), so only PROCESS-HEALTH (rate-independent) drives the hard alarm. The listener emits
this heartbeat; a dead listener simply stops emitting, which the external readers detect.
"""
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HEARTBEAT_PATH = os.path.join(HERE, "data", "listener_heartbeat.json")
FLAG_PATH = os.path.join(HERE, "data", "LISTENER_DOWN.flag")
HEARTBEAT_INTERVAL_S = 60          # listener writes every 60s
STALE_S = 300                      # 5x interval: process-health bound, message-rate-independent


# ---- emitted BY the listener (the only in-listener part; the alarm logic is external) ----
def write_heartbeat(pid, connected, last_msg_id, last_msg_ts, path=HEARTBEAT_PATH):
    tmp = path + ".tmp"
    rec = {"ts": time.time(), "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "pid": pid, "connected": bool(connected),
           "last_msg_id": last_msg_id, "last_msg_ts": last_msg_ts}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rec, f)
    os.replace(tmp, path)           # atomic; a reader never sees a partial heartbeat
    return rec


def read_heartbeat(path=HEARTBEAT_PATH):
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return None                 # MISSING/corrupt -> None; the assessor treats this as NOT healthy


# ---- OS process liveness (rate-independent) ----
def pid_alive_os(pid):
    """True if a process with this pid exists (Windows, no dependency)."""
    if not pid:
        return False
    try:
        import ctypes
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))  # QUERY_LIMITED_INFORMATION
        if h:
            ctypes.windll.kernel32.CloseHandle(h)
            return True
        return False
    except Exception:               # noqa: BLE001 -- fail closed toward 'not alive'
        return False


# ---- the assessment (pure; process check injected for testability) ----
def assess_listener(hb, now_ts, pid_alive, stale_s=STALE_S):
    """hb: heartbeat dict or None; pid_alive: callable(pid)->bool.
    Returns {level, code, reason, detail}. level in HEALTHY|WARN|ALARM. Silence is never HEALTHY."""
    if hb is None:
        return {"level": "ALARM", "code": "HEARTBEAT_ABSENT",
                "reason": "no listener heartbeat file — liveness unverifiable; ABSENCE treated as DOWN",
                "detail": {}}
    pid = hb.get("pid")
    age = now_ts - float(hb.get("ts", 0) or 0)
    det = {"pid": pid, "age_s": round(age), "connected": hb.get("connected"),
           "last_msg_id": hb.get("last_msg_id"), "last_msg_ts": hb.get("last_msg_ts")}
    if not (pid and pid_alive(pid)):
        return {"level": "ALARM", "code": "LISTENER_PROCESS_DOWN",
                "reason": f"heartbeat pid {pid} is not alive — listener process DOWN", "detail": det}
    if age > stale_s:
        return {"level": "ALARM", "code": "HEARTBEAT_STALE",
                "reason": f"heartbeat {age:.0f}s old > {stale_s}s while process alive — silent stall/disconnect",
                "detail": det}
    if hb.get("connected") is False:
        return {"level": "ALARM", "code": "LISTENER_DISCONNECTED",
                "reason": "heartbeat reports connected=False — silent Telegram disconnect", "detail": det}
    return {"level": "HEALTHY", "code": "OK",
            "reason": f"heartbeat fresh ({age:.0f}s), connected", "detail": det}


def assess_monitor(observer_running):
    """Monitor-of-the-monitor: intake_observer runs the continuous check. If IT is down the
    flag is never WRITTEN (absence), so this must be checked INDEPENDENTLY by the pull backstop."""
    if not observer_running:
        return {"level": "ALARM", "code": "MONITOR_DOWN",
                "reason": "intake_observer (the continuous liveness monitor) is DOWN — "
                          "LISTENER_DOWN.flag can no longer be written; heartbeat must be re-checked directly"}
    return {"level": "HEALTHY", "code": "OK", "reason": "intake_observer up"}


# ---- flag helpers (written by the continuous monitor) ----
def raise_flag(verdict, path=FLAG_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"raised_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **verdict}, f)


def clear_flag(path=FLAG_PATH):
    try:
        os.remove(path)
    except OSError:
        pass


def process_running_by_marker(marker):
    """True/False if a running python process's command line contains `marker`; None if the
    query itself failed (the caller should fail TOWARD alarm on None, never toward healthy)."""
    import subprocess
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "@(Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | "
             f"Where-Object {{ $_.CommandLine -match '{marker}' }}).Count"],
            capture_output=True, text=True, timeout=25).stdout.strip()
        return (int(out) >= 1) if out.isdigit() else None
    except Exception:                                   # noqa: BLE001
        return None


def check_and_flag(now_ts=None):
    """Continuous-monitor entry point (called each intake_observer poll). Assesses the listener
    and raises/clears data/LISTENER_DOWN.flag. Returns the verdict. Fails toward alarm."""
    now_ts = now_ts if now_ts is not None else time.time()
    hb = read_heartbeat()
    lp = process_running_by_marker("module_a_telegram")
    if lp is False:
        v = {"level": "ALARM", "code": "LISTENER_PROCESS_DOWN",
             "reason": "listener process is not running", "detail": {}}
    elif hb is None:
        # process up (or the query failed) but no heartbeat: staged/not-active — WARN, not a hard
        # flag, so the transition before deploy does not cry wolf; still never reported 'healthy'.
        v = {"level": "WARN", "code": "HEARTBEAT_NOT_ACTIVE",
             "reason": "no heartbeat file (ADD-2 staged or emitter not writing)", "detail": {}}
    else:
        v = assess_listener(hb, now_ts, pid_alive_os)
    if v["level"] == "ALARM":
        raise_flag(v)
    else:
        clear_flag()
    return v
