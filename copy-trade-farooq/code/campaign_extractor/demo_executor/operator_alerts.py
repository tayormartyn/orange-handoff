"""
Advisory operator-alert engine. Watches the append-only prospective Telegram evidence for genuinely
NEW messages, classifies each (reusing the Farouk interpretation contract), and produces a safe alert
descriptor for the console to render as a Windows desktop toast + sound. It NEVER confirms a signal,
arms a proposal, issues a permit/lease, or calls any broker transport. Alerts carry only safe metadata
(no tokens, no account secrets, no excessive source text). De-duplicated by Telegram message id +
attachment hash; a duplicate/repost/replay never raises the urgent NEW-SIGNAL alarm.
"""
from __future__ import annotations
import hashlib
import json
import os
import sqlite3

import config as CFG

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROSPECTIVE_DB = os.path.join(_ROOT, "campaign_extractor", "prospective", "data", "prospective_evidence_v1.db")
ALERT_LOG = os.path.join(_ROOT, "data", "operator_alerts.jsonl")
STATE_FILE = os.path.join(_ROOT, "data", "operator_alerts_state.json")

# type -> (label, sound). Result card is NEVER the urgent NEW-SIGNAL sound.
ALERT_SOUNDS = {
    "NEW SIGNAL CANDIDATE": "urgent",
    "TRADE UPDATE": "soft",
    "CANCELLATION INSTRUCTION": "soft",
    "TRADE RESULT": "info",
    "HUMAN REVIEW REQUIRED": "soft",
    "DUPLICATE IGNORED": "none",
    "STALE SIGNAL BLOCKED": "none",
}


def _fc():
    import farouk_contract as FC
    return FC


def _ts_ms(iso):
    if not iso:
        return None
    try:
        import calendar
        import time
        s = iso.replace("Z", "").split("+")[0].split(".")[0]
        return int(calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%S"))) * 1000
    except Exception:
        return None


def classify_alert(raw_text, *, posted_at_ms, now_ms, seen_semantic_keys=None):
    """Return {type, sound, instrument, direction, provider_message_time_ms, signal_age_seconds,
    semantic_key}. Fail-safe: unknown -> HUMAN REVIEW REQUIRED."""
    FC = _fc()
    intent = FC.classify_intent(raw_text or "")
    fields = FC.extract_fields(FC.ocr_normalize.normalize(raw_text or "")["normalized_text"]) \
        if hasattr(FC, "ocr_normalize") else FC.extract_fields(raw_text or "")
    age = None if posted_at_ms is None else round((now_ms - posted_at_ms) / 1000.0, 1)
    sem = None
    typ = "HUMAN REVIEW REQUIRED"
    if intent == "TRADE_RESULT":
        typ = "TRADE RESULT"
    elif intent == "CANCEL_PENDING":
        typ = "CANCELLATION INSTRUCTION"
    elif intent == "TRADE_UPDATE":
        typ = "TRADE UPDATE"
    elif intent == "NEW_SIGNAL":
        import idempotency as ID
        sem = ID.semantic_fingerprint(provider="farouk", instrument=fields.get("instrument"),
                                      direction=fields.get("direction"), order_intent=fields.get("order_type") or "LIMIT",
                                      entry_low=fields.get("entry_low"), entry_high=fields.get("entry_high"),
                                      stop=fields.get("stop"), targets=fields.get("targets"),
                                      provider_ts_ms=posted_at_ms)["semantic_key"]
        if posted_at_ms is not None and age is not None and age > CFG.FRESH_SIGNAL_TTL_SECONDS:
            typ = "STALE SIGNAL BLOCKED"                 # a replay/old screenshot never raises the alarm
        elif seen_semantic_keys and sem in seen_semantic_keys:
            typ = "DUPLICATE IGNORED"
        else:
            typ = "NEW SIGNAL CANDIDATE"
    elif intent == "UNKNOWN":
        typ = "HUMAN REVIEW REQUIRED"
    return {"type": typ, "sound": ALERT_SOUNDS.get(typ, "soft"), "intent": intent,
            "instrument": fields.get("instrument"), "direction": fields.get("direction"),
            "provider_message_time_ms": posted_at_ms, "signal_age_seconds": age, "semantic_key": sem}


# ---- append-only log + state ----
def _append_log(alert):
    os.makedirs(os.path.dirname(ALERT_LOG), exist_ok=True)
    with open(ALERT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(alert) + "\n")


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            return json.load(open(STATE_FILE, encoding="utf-8"))
        except Exception:
            pass
    return {"enabled": True, "alerted_message_ids": [], "seen_semantic_keys": [], "seq": 0}


def save_state(st):
    json.dump(st, open(STATE_FILE, "w", encoding="utf-8"))


def set_enabled(on):
    st = load_state(); st["enabled"] = bool(on); save_state(st)
    return {"enabled": st["enabled"]}


def _new_prospective_messages(alerted_ids, db_path=None):
    db = db_path or PROSPECTIVE_DB
    if not os.path.exists(db):
        return []
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = c.execute("SELECT telegram_message_id, telegram_channel_id, telegram_posted_at_utc, "
                     "raw_text, media_reference_or_hash FROM prospective_message_evidence "
                     "ORDER BY rowseq ASC").fetchall()
    c.close()
    out = []
    for mid, chan, posted, raw, media in rows:
        dedup = _dedup_key(mid, media)
        if dedup in alerted_ids:
            continue
        out.append({"message_id": mid, "channel_id": chan, "posted_at": posted, "raw_text": raw,
                    "media": media, "dedup_key": dedup})
    return out


def _dedup_key(message_id, media_ref):
    raw = f"{message_id}|{media_ref or ''}"
    return "alk-" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def poll(now_ms, *, db_path=None, emit=True):
    """Scan for genuinely new messages, classify, dedup, append. Returns the newly-created alerts.
    Alerting never mutates or affects the evidence/parsing/safety layers."""
    st = load_state()
    alerted = set(st.get("alerted_message_ids", []))
    seen_sem = set(st.get("seen_semantic_keys", []))
    new_alerts = []
    for m in _new_prospective_messages(alerted, db_path):
        a = classify_alert(m["raw_text"], posted_at_ms=_ts_ms(m["posted_at"]), now_ms=now_ms,
                           seen_semantic_keys=seen_sem)
        st["seq"] = st.get("seq", 0) + 1
        alert = {"seq": st["seq"], "alert_id": m["dedup_key"], "message_id": m["message_id"],
                 "channel_id": m["channel_id"], **a,
                 "instruction": "Open the local console to review — advisory only, no action taken.",
                 "created_at_ms": now_ms}
        alerted.add(m["dedup_key"])
        if a.get("semantic_key"):
            seen_sem.add(a["semantic_key"])
        new_alerts.append(alert)
        if emit:
            _append_log(alert)
    st["alerted_message_ids"] = list(alerted)[-2000:]
    st["seen_semantic_keys"] = list(seen_sem)[-2000:]
    if emit:
        save_state(st)
    return new_alerts


def baseline(now_ms, db_path=None):
    """One-time baseline: mark all CURRENT prospective messages as already-seen WITHOUT emitting, so
    historical intake never spams the operator. Only genuinely-new messages arriving afterwards alert.
    Idempotent (guarded by the 'baselined' state flag)."""
    st = load_state()
    if st.get("baselined"):
        return {"baselined": True, "skipped": 0}
    alerted = set(st.get("alerted_message_ids", []))
    seen = set(st.get("seen_semantic_keys", []))
    n = 0
    for m in _new_prospective_messages(alerted, db_path):
        a = classify_alert(m["raw_text"], posted_at_ms=_ts_ms(m["posted_at"]), now_ms=now_ms,
                           seen_semantic_keys=seen)
        alerted.add(m["dedup_key"])
        if a.get("semantic_key"):
            seen.add(a["semantic_key"])
        n += 1
    st["alerted_message_ids"] = list(alerted)[-2000:]
    st["seen_semantic_keys"] = list(seen)[-2000:]
    st["baselined"] = True
    save_state(st)
    return {"baselined": True, "skipped": n}


def test_alert(now_ms):
    """A LOCAL test alert — creates no intake and no trading event; appended to the alert log."""
    st = load_state(); st["seq"] = st.get("seq", 0) + 1; save_state(st)
    alert = {"seq": st["seq"], "alert_id": "test-" + str(st["seq"]), "type": "TEST ALERT",
             "sound": "soft", "message_id": None, "instrument": None, "direction": None,
             "provider_message_time_ms": None, "signal_age_seconds": None,
             "instruction": "Local test only — no intake, no trading event.", "created_at_ms": now_ms}
    _append_log(alert)
    return alert
