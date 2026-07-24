"""
Alert output: console + append-only JSONL (data/paper_alerts_v1.jsonl) + latest readable artifact
(data/paper_alert_latest.json). Always PAPER ONLY / NOT A FILL. No external credentials.
"""
from __future__ import annotations
import json
import os
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
JSONL = os.path.join(_ROOT, "data", "paper_alerts_v1.jsonl")
LATEST = os.path.join(_ROOT, "data", "paper_alert_latest.json")


def format_alert(decision, *, observation_id, provider_id):
    u = decision.get("unified", {})
    act = decision.get("actionable") or {}
    dev = decision.get("delivery") or {}
    return {
        "labels": ["OBSERVATION_ONLY", "PAPER_ONLY", "NOT_A_FILL", "NOT_AN_OUTCOME"],
        "banner": "PAPER ONLY / NOT A FILL",
        "observation_id": observation_id, "provider": provider_id,
        "source_message_id": u.get("source_message_id"),
        "instrument": u.get("instrument"), "direction": u.get("direction"),
        "confirmed_entry_range": [str(u.get("entry_low")), str(u.get("entry_high"))],
        "decision": decision["status"], "reason": decision.get("reason"),
        "pepperstone_bid": act.get("bid"), "pepperstone_ask": act.get("ask"),
        "executable_quote_side": act.get("executable_side"),
        "delivery_anchor_result": dev.get("result"), "delivery_reason": dev.get("reason"),
        "actionable_system_result": act.get("result"), "actionable_reason": act.get("reason"),
        "freshness": {k: act.get(k) for k in ("bid_source_age_ms", "ask_source_age_ms")},
        "q4a_config_version": decision.get("q4a_config_version"),
        "emitted_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def emit(alert, *, to_console=True, jsonl_path=None, latest_path=None):
    jp, lp = jsonl_path or JSONL, latest_path or LATEST
    os.makedirs(os.path.dirname(jp), exist_ok=True)
    with open(jp, "a", encoding="utf-8") as f:                   # append-only stream
        f.write(json.dumps(alert, default=str) + "\n")
    with open(lp, "w", encoding="utf-8") as f:                   # latest readable artifact
        json.dump(alert, f, indent=2, default=str)
    if to_console:
        print(f"[{alert['banner']}] {alert['provider']} msg={alert['source_message_id']} "
              f"{alert['instrument']} {alert['direction']} zone={alert['confirmed_entry_range']} "
              f"-> {alert['decision']} ({alert.get('reason')}) "
              f"bid={alert['pepperstone_bid']} ask={alert['pepperstone_ask']} "
              f"side={alert['executable_quote_side']}")
    return alert
