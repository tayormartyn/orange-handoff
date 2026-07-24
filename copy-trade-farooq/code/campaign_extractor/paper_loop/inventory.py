"""
Phase 7 — READ-ONLY captured-message inventory. Scans Telegram evidence for messages received
during valid Pepperstone quote-session coverage, groups by provider, and classifies each. Does NOT
auto-confirm or auto-process anything. Recommends the best first real Gold message for HUMAN review.
"""
from __future__ import annotations
import os
import re
import sqlite3
from datetime import datetime, timezone

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
QUOTES = os.path.join(_ROOT, "data", "ctrader_quotes_v1.db")
EVID = os.path.join(_ROOT, "campaign_extractor", "prospective", "data", "prospective_evidence_v1.db")
FAROUK_CHANNEL = "-1001902136163"

GOLD = re.compile(r"\b(gold|xau ?usd|xau)\b", re.I)
DIR = re.compile(r"\b(buy|sell)\b", re.I)
RANGE = re.compile(r"\b\d{3,4}(?:\.\d+)?\s*[-/to ]{1,4}\s*\d{3,4}(?:\.\d+)?\b", re.I)
MGMT = re.compile(r"\b(tp\d?|sl|stop|close[d]?|breakeven|move|running|secure|book)\b", re.I)


def _ms(s):
    if not s:
        return None
    d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).timestamp() * 1000


def _provider(channel_id):
    return "FAROUK" if str(channel_id) == FAROUK_CHANNEL else "OTHER"


def coverage_spans():
    if not os.path.exists(QUOTES):
        return []
    c = sqlite3.connect(f"file:{QUOTES}?mode=ro", uri=True)
    rows = c.execute("SELECT connection_session_id, MIN(local_received_utc), MAX(local_received_utc) "
                     "FROM raw_spot_events GROUP BY connection_session_id").fetchall()
    c.close()
    return [(sid, _ms(a), _ms(b)) for sid, a, b in rows]


def build_inventory():
    spans = coverage_spans()
    c = sqlite3.connect(f"file:{EVID}?mode=ro", uri=True)
    msgs = c.execute("SELECT telegram_message_id, telegram_channel_id, listener_received_at_utc, "
                     "raw_text FROM prospective_message_evidence").fetchall()
    c.close()
    groups = {"FAROUK": [], "RUPES": [], "OTHER": []}
    for mid, ch, recv, text in msgs:
        t = text or ""
        rms = _ms(recv)
        covered = any(a is not None and b is not None and rms is not None and a <= rms <= b
                      for _s, a, b in spans)
        gold = bool(GOLD.search(t))
        direction = bool(DIR.search(t))
        rng = bool(RANGE.search(t))
        if not covered:
            status = "NO_COVERAGE"
        elif not gold:
            status = "NOT_GOLD"
        elif gold and direction and rng:
            status = "READY_FOR_HUMAN_CONFIRMATION"
        elif gold and (direction or rng):
            status = "INCOMPLETE_SIGNAL"
        elif MGMT.search(t):
            status = "MANAGEMENT_ONLY"
        else:
            status = "ANALYSIS_ONLY"
        rec = {"message_id": mid, "provider": _provider(ch), "received": recv,
               "gold_related": gold, "direction_present": direction, "entry_range_present": rng,
               "quote_coverage": covered, "status": status}
        groups.setdefault(rec["provider"], []).append(rec)
    ready = [m for g in groups.values() for m in g if m["status"] == "READY_FOR_HUMAN_CONFIRMATION"]
    recommended = sorted(ready, key=lambda m: str(m["received"]))[0]["message_id"] if ready else None
    return {"coverage_sessions": len(spans), "total_messages": len(msgs),
            "groups": groups, "recommended_first_gold_message_id": recommended,
            "note": "READ-ONLY; nothing auto-confirmed or processed. Human review required."}
