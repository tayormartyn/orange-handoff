"""ALERT_LANE_MONITOR v0.1 (D-015 step 4) — read-only data-flow health check.

Detects what is LOCALLY observable and is honest about what is not:
 1. BAR LANE: staleness of the R2->tracker 1m bar feed (ingestion log), with
    market-hours awareness. Bar death = Worker/feed/tracker problem.
 2. ALERT LANE: TradingView mirror alerts cannot be observed locally (uuid R2
    keys, no list). This monitor tracks the AGE OF LAST VERIFICATION (from
    alert_lane_verification_state.json, updated whenever an authorised R2 audit
    runs) and ALARMS when it exceeds MAX_VERIFICATION_AGE_DAYS — converting the
    named defect ALERT_LANE_SILENCE_UNMONITORED from silent to loud.
 3. PROCESS + gate summary comes from brain_refresh; this tool is called by
    ORANGE_STATUS.ps1 after it.
Proper fix (needs approval — Worker baseline change): predictable-key
`alerts/last_any.json` marker in the Worker; see work order in the state file.
"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
FA = os.path.join(os.path.dirname(HERE),
                  r"always_on_tradingview_receiver_plan\stage_c_tooling\farouk_plus\follower_assistant")
ING = os.path.join(FA, r"market_tracker\ingestion_log_v0_1.jsonl")
STATE = os.path.join(HERE, "alert_lane_verification_state.json")

BAR_STALE_MIN = 20            # completed-bar steady state is ~11 min; 20 = alarm
MAX_VERIFICATION_AGE_DAYS = 7


def market_open(now):
    # XAU CFD week: Sun 22:00Z -> Fri 21:00Z, daily break 21:00-22:00Z
    wd, hhmm = now.weekday(), now.hour * 60 + now.minute
    if wd == 5:
        return False
    if wd == 6:
        return hhmm >= 22 * 60
    if wd == 4:
        return hhmm < 21 * 60
    return not (21 * 60 <= hhmm < 22 * 60)


def tail_ts(path):
    with open(path, "rb") as f:
        f.seek(0, 2)
        f.seek(max(0, f.tell() - 8192))
        for line in reversed(f.read().decode("utf-8", "replace").strip().splitlines()):
            if '"ACCEPTED"' in line:
                return json.loads(line)["bar"]["event_ts"]
    return None


def main():
    now = datetime.now(timezone.utc)
    warnings, ok = [], []

    ts = tail_ts(ING)
    if ts is None:
        warnings.append("BAR LANE: no ACCEPTED bar found in ingestion log tail — CHECK TRACKER/WORKER")
    else:
        age = (now - datetime.fromtimestamp(ts, timezone.utc)).total_seconds() / 60
        if market_open(now) and age > BAR_STALE_MIN:
            warnings.append(f"BAR LANE STALE: last bar {age:.0f} min old during market hours "
                            f"(threshold {BAR_STALE_MIN}) — Worker/feed/tracker needs attention")
        else:
            ok.append(f"bar lane: last bar {age:.0f} min old ({'market open' if market_open(now) else 'market closed'}) OK")

    # D-020: live marker read (Worker baseline 2045cdb1 writes alerts/last_any.json on every
    # accepted non-bar POST). Direct flow-age check; falls back to audit-age logic on failure.
    marker = None
    try:
        import subprocess
        wd = os.path.join(os.path.dirname(HERE), r"always_on_tradingview_receiver_plan\cloud_worker_dark")
        r = subprocess.run(
            'npx wrangler r2 object get "farouk-tv-webhook-evidence-v1/alerts/last_any.json" --remote --pipe',
            capture_output=True, text=True, timeout=60, shell=True, cwd=wd)
        lines = [l for l in r.stdout.strip().splitlines() if l.strip().startswith("{")]
        if lines:
            marker = json.loads(lines[-1])
    except Exception:
        marker = None
    if marker:
        m_age_h = (now - datetime.fromisoformat(
            marker["received_at_utc"].replace("Z", "+00:00"))).total_seconds() / 3600
        if market_open(now) and m_age_h > 24:
            warnings.append(f"ALERT LANE FLOW STALE: last non-bar POST {m_age_h:.0f}h ago "
                            f"(marker) during market hours — check TradingView mirror alerts")
        else:
            ok.append(f"alert lane FLOW: last non-bar POST {m_age_h:.1f}h ago "
                      f"({marker.get('payload_head', '')!r})")

    st = json.load(open(STATE)) if os.path.exists(STATE) else {}
    lv = st.get("last_verified_utc")
    if not lv:
        warnings.append("ALERT LANE: never verified via this monitor — run the R2 audit and record it")
    else:
        age_d = (now - datetime.fromisoformat(lv.replace("Z", "+00:00"))).days
        routes = st.get("last_confirmed_per_route", {})
        if age_d > MAX_VERIFICATION_AGE_DAYS:
            warnings.append(f"ALERT LANE VERIFICATION STALE: last R2 audit {age_d}d ago "
                            f"(max {MAX_VERIFICATION_AGE_DAYS}) — run the authorised list-branch audit "
                            f"(deploy->list->revert, see D-013) or approve the Worker last-alert marker")
        else:
            ok.append(f"alert lane: last verified {age_d}d ago; routes: " +
                      ", ".join(f"{k}@{v}" for k, v in routes.items()))

    print("== ALERT_LANE_MONITOR v0.1 ==")
    for w in warnings:
        print("  [WARN]", w)
    for o in ok:
        print("  [ok]  ", o)
    if not warnings:
        print("  ALL LANES HEALTHY (within verification limits)")
    return 1 if warnings else 0


if __name__ == "__main__":
    sys.exit(main())
