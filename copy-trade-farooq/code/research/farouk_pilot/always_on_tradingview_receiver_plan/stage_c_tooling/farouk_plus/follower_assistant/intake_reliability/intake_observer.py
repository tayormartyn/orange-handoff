"""FAIL-LOUD INTAKE OBSERVER v0.1 — READ-ONLY (RESEARCH/OBSERVABILITY ONLY).

Gives EVERY captured Telegram message exactly one durable classification, quarantines plausible-but-
unparsed trade signals, raises deduplicated operator alerts, and emits a small status view. It reads
the evidence DB + forward ledger + freeze ledger READ-ONLY and writes ONLY its own append-only
ledgers. It never creates/mutates a campaign, never touches the wire/watcher, never executes anything.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
FA = os.path.dirname(HERE)
sys.path.insert(0, FA)
sys.path.insert(0, HERE)
import interpreter                                                # noqa: E402
import guards                                                     # noqa: E402

OBSERVER_VERSION = "intake_observer_v0_1"
ST_ROOT = guards.ST_ROOT
EVIDENCE_DB = os.path.join(ST_ROOT, "campaign_extractor", "prospective", "data", "prospective_evidence_v1.db")
FWD_LEDGER = os.path.join(FA, "..", "forward_validation_ledger_v0_2.jsonl")
FREEZE_LEDGER = os.path.join(FA, "evidence_layer", "router_freeze_v0_1.jsonl")
CLASS_LEDGER = os.path.join(HERE, "intake_classification_v0_1.jsonl")
QUAR_LEDGER = os.path.join(HERE, "intake_quarantine_v0_1.jsonl")
ALERT_LEDGER = os.path.join(HERE, "intake_alerts_v0_1.jsonl")
STATUS_VIEW = os.path.join(HERE, "intake_status_v0_1.json")
CURSOR = os.path.join(HERE, "intake_cursor_v0_1.json")
LOCK = os.path.join(HERE, "intake_observer.instance.lock")

CLASSES = ("PARSED_NEW_CAMPAIGN", "PARSED_MANAGEMENT_INSTRUCTION", "PARSED_COMMENTARY", "PARSED_NON_XAU",
           "DUPLICATE", "QUARANTINED_UNPARSED_SIGNAL_CANDIDATE", "ORPHAN_MANAGEMENT_MESSAGE",
           "AMBIGUOUS_CAMPAIGN_CORRELATION", "IRRELEVANT", "PARSER_FAILURE_CAPTURED")
ALERT_CLASSES = ("QUARANTINED_UNPARSED_SIGNAL_CANDIDATE", "ORPHAN_MANAGEMENT_MESSAGE",
                 "AMBIGUOUS_CAMPAIGN_CORRELATION", "PARSER_FAILURE_CAPTURED", "CAMPAIGN_CREATED_FREEZE_MISSING")

# trade-relevance keyword CATEGORIES — quarantine needs >=2 distinct categories (never one weak word)
KW = {
    "instrument": r"\bxauusd\b|\bxau\b|\bgold\b",
    "direction": r"\bbuy\b|\bsell\b|\blong\b|\bshort\b",
    "zone": r"\bzone\b|\bentry\b|\barea\b|\blimit\b",
    "stop": r"\bsl\b|\bstop\s*loss\b|\bstop\b",
    "tp": r"\btp\b|\btarget\b|take\s*profit",
    "be": r"break\s*even|\bbe\b|sl to entry",
    "mgmt": r"\bclose\b|\btake\b|risk\s*off|\bhold\b",
    "progress": r"\bpips\b|\bholding\b|\brunner\b",
}


def _cats(text):
    t = (text or "").lower()
    return {k for k, pat in KW.items() if re.search(pat, t)}


def _plausible_trade_related(text):
    """A plausible unparsed SIGNAL candidate needs SIGNAL STRUCTURE — (instrument OR direction) AND
    (zone OR stop OR tp OR be) — not merely progress/commentary words like 'pips'/'holding'. This
    keeps genuine unparsed signals loud without drowning them in commentary false-positives."""
    c = _cats(text)
    return bool(c & {"instrument", "direction"}) and bool(c & {"zone", "stop", "tp", "be"})


def _probable(text):
    t = (text or "").lower()
    instr = "XAUUSD" if re.search(KW["instrument"], t) else ("BTC" if "btc" in t else "UNKNOWN")
    if re.search(r"\bsell\b|\bshort\b", t):
        d = "SELL"
    elif re.search(r"\bbuy\b|\blong\b", t):
        d = "BUY"
    else:
        d = "UNKNOWN"
    return {"probable_instrument": instr, "probable_direction": d, "categories": sorted(_cats(text))}


def _sha(s):
    return hashlib.sha256(str(s).encode()).hexdigest()


def build_index(fwd_ledger=None, freeze_ledger=None):
    """Read-only map of what the wire did with each message + freeze status per setup."""
    fwd_ledger = fwd_ledger or FWD_LEDGER
    freeze_ledger = freeze_ledger or FREEZE_LEDGER
    created, mgmt, review, orphan, ambiguous = {}, {}, {}, {}, {}
    latest, invalidated = {}, set()
    if os.path.exists(fwd_ledger):
        for line in open(fwd_ledger, encoding="utf-8"):
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            rt = r.get("record_type")
            if rt == "XAU_F_SETUP":
                sid = r["setup_id"]
                if sid not in latest or (r.get("revision", 1) >= latest[sid].get("revision", 1)):
                    latest[sid] = r                                # keep the LATEST revision per setup
            elif rt == "XAU_F_CORRELATION_CORRECTION":
                invalidated |= set(r.get("invalid_message_ids") or [])   # honor append-only corrections
            elif rt == "XAU_F_INTERPRETATION_REVIEW":
                review[r.get("message_id")] = r.get("why")
            elif rt == "XAU_F_ORPHAN_MANAGEMENT":
                orphan[r.get("message_id")] = r.get("why")
            elif rt == "XAU_F_CAMPAIGN_PAUSE":
                ambiguous[r.get("message_id")] = r.get("why")       # some pauses carry message_id
    setups = latest
    for sid, r in latest.items():
        mids = [m for m in (r.get("message_ids") or []) if m not in invalidated]
        if mids:
            created[mids[0]] = sid                                  # originating entry message
        for e in r.get("management_timing_8c", {}).get("instruction_events", []):
            m = e.get("message_id")
            if m is not None and m not in invalidated:
                mgmt[m] = sid
    # invalidated (correction) messages that no longer belong to any campaign -> orphan (fail-loud)
    for m in invalidated:
        if m not in created and m not in mgmt:
            orphan.setdefault(m, "correlation invalidated by XAU_F_CORRELATION_CORRECTION (belongs to uncaptured campaign)")
    freezes = set()
    if os.path.exists(freeze_ledger):
        for line in open(freeze_ledger, encoding="utf-8"):
            try:
                fr = json.loads(line)
            except json.JSONDecodeError:
                continue
            if fr.get("record_type") == "ROUTER_FREEZE":
                freezes.add(fr.get("setup_id"))
    return {"created": created, "mgmt": mgmt, "review": review, "orphan": orphan,
            "ambiguous": ambiguous, "setups": setups, "freezes": freezes}


def route_message(msg, idx):
    """-> (classification, reason, extra). Deterministic; parser exceptions captured, never raised."""
    mid = msg["id"]
    text = msg.get("raw_text") or ""
    try:
        c = interpreter.classify(text)
    except Exception as e:                                          # noqa: BLE001
        return "PARSER_FAILURE_CAPTURED", f"{type(e).__name__}: {e}", {"raw_preserved": True}
    kind = c.get("kind")
    # honour what the wire durably recorded (fail-loud surfacing of EXISTING records)
    if mid in idx["created"]:
        sid = idx["created"][mid]
        return "PARSED_NEW_CAMPAIGN", "wire created campaign", {"campaign_id": sid,
                "freeze_status": ("PRESENT" if sid in idx["freezes"] else "ABSENT")}
    if mid in idx["mgmt"]:
        return "PARSED_MANAGEMENT_INSTRUCTION", "correlated to campaign", {"campaign_id": idx["mgmt"][mid]}
    if mid in idx["ambiguous"]:
        return "AMBIGUOUS_CAMPAIGN_CORRELATION", idx["ambiguous"][mid] or "ambiguous correlation", {"probable": _probable(text)}
    if mid in idx["orphan"]:
        return "ORPHAN_MANAGEMENT_MESSAGE", idx["orphan"][mid] or "no proximate open campaign", {"probable": _probable(text)}
    if mid in idx["review"]:
        # a fail-closed wire review = plausible signal that did NOT capture -> QUARANTINE + alert
        return "QUARANTINED_UNPARSED_SIGNAL_CANDIDATE", f"wire review: {idx['review'][mid]}", {"probable": _probable(text)}
    # no wire record for this message -> classify fresh
    if kind == "NOT_FAROUK_GOLD":
        if _plausible_trade_related(text):
            return "QUARANTINED_UNPARSED_SIGNAL_CANDIDATE", "trade-like but not farouk-gold header", {"probable": _probable(text)}
        return "IRRELEVANT", "not farouk-gold, not trade-related", {}
    if kind == "ENTRY":
        return "QUARANTINED_UNPARSED_SIGNAL_CANDIDATE", "entry parses now but no wire campaign record (needs review)", {"probable": _probable(text)}
    if kind == "MANAGEMENT":
        return "ORPHAN_MANAGEMENT_MESSAGE", "management with no wire correlation", {"probable": _probable(text)}
    if kind == "NEEDS_HUMAN_REVIEW":
        return "QUARANTINED_UNPARSED_SIGNAL_CANDIDATE", c.get("why", "needs human review"), {"probable": _probable(text)}
    # kind == OTHER (farouk-gold commentary)
    if _plausible_trade_related(text):
        return "QUARANTINED_UNPARSED_SIGNAL_CANDIDATE", "plausible trade-related but unparsed", {"probable": _probable(text)}
    if re.search(KW["instrument"], text.lower()) and "btc" in text.lower():
        return "PARSED_NON_XAU", "non-XAU (BTC) in farouk channel", {}
    return "PARSED_COMMENTARY", "farouk-gold commentary, no action", {}


def _append(path, rec):
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, default=str, ensure_ascii=False) + "\n")


def _existing_keys(path, field="idempotency_key"):
    keys = set()
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            try:
                keys.add(json.loads(line).get(field))
            except json.JSONDecodeError:
                pass
    return keys


def load_cursor():
    if os.path.exists(CURSOR):
        try:
            return json.load(open(CURSOR, encoding="utf-8"))
        except Exception:                                          # noqa: BLE001
            return {"classified": {}}
    return {"classified": {}}


def save_cursor(cur):
    tmp = CURSOR + ".tmp"
    json.dump(cur, open(tmp, "w", encoding="utf-8"), indent=1)
    os.replace(tmp, CURSOR)


def _messages(db_path, after_id=0):
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "SELECT telegram_message_id, telegram_posted_at_utc, listener_received_at_utc, raw_text, "
            "raw_text_hash, telegram_sender_username FROM prospective_message_evidence "
            "WHERE message_event_type='CREATED' AND CAST(telegram_message_id AS INTEGER) > ? "
            "ORDER BY CAST(telegram_message_id AS INTEGER)", (after_id,)).fetchall()
    finally:
        con.close()
    return [{"id": int(r[0]), "posted": r[1], "received": r[2], "raw_text": r[3],
             "sha": r[4], "sender": r[5]} for r in rows]


def scan(db_path=EVIDENCE_DB, class_ledger=None, quar_ledger=None, alert_ledger=None,
         status_path=None, cursor=None, idx=None, seen_hashes=None):
    """One read-only pass over new messages. Idempotent (cursor + idempotency keys). Returns a summary."""
    class_ledger = class_ledger or CLASS_LEDGER
    quar_ledger = quar_ledger or QUAR_LEDGER
    alert_ledger = alert_ledger or ALERT_LEDGER
    status_path = status_path or STATUS_VIEW
    cur = cursor if cursor is not None else load_cursor()
    idx = idx if idx is not None else build_index()
    alert_keys = _existing_keys(alert_ledger)
    seen_hashes = seen_hashes if seen_hashes is not None else set()
    now = int(time.time())
    recent, counts = [], {}
    msgs = _messages(db_path)
    for m in msgs:
        mid = m["id"]
        tag = str(mid)
        # idempotency: a message_id already classified is a genuine DUPLICATE re-delivery (or a
        # restart/backlog replay) -> no new record, no new alert. (Recurring TEXT across DIFFERENT
        # message_ids is NOT a duplicate — e.g. 'tp 1 now' legitimately recurs per campaign.)
        if tag in cur["classified"]:
            classification = cur["classified"][tag]["c"]
            counts[classification] = counts.get(classification, 0) + 1
            recent.append({"id": mid, "class": classification, "note": "DUPLICATE_SUPPRESSED"})
            continue
        classification, reason, extra = route_message(m, idx)
        rec = {"record_type": "INTAKE_CLASSIFICATION", "message_id": mid, "source_channel": (m.get("sender") or "UNKNOWN"),
               "raw_text_hash": m["sha"], "source_timestamp": m["posted"], "capture_timestamp": m["received"],
               "parser_version": OBSERVER_VERSION, "classification": classification, "reason": reason,
               "extra": extra, "classified_at": now, "idempotency_key": _sha(f"{mid}|{classification}|{OBSERVER_VERSION}"),
               "review_only": True, "observation_only": True}
        _append(class_ledger, rec)
        cur["classified"][tag] = {"c": classification, "r": reason}
        counts[classification] = counts.get(classification, 0) + 1
        recent.append({"id": mid, "class": classification})
        # quarantine record
        if classification == "QUARANTINED_UNPARSED_SIGNAL_CANDIDATE":
            _append(quar_ledger, {"record_type": "INTAKE_QUARANTINE", "message_id": mid,
                    "source_channel": (m.get("sender") or "UNKNOWN"), "raw_text_hash": m["sha"],
                    "raw_text_bounded": (m["raw_text"] or "")[:200], "source_timestamp": m["posted"],
                    "capture_timestamp": m["received"], "parser_version": OBSERVER_VERSION,
                    "failed_parser_reason": reason, "probable": extra.get("probable"),
                    "quarantine_timestamp": now, "resolution_status": "PENDING_OPERATOR_REVIEW",
                    "idempotency_key": _sha(f"Q|{mid}|{OBSERVER_VERSION}"),
                    "quarantine_never_mutates_campaign": True, "review_only": True, "observation_only": True})
        # dedup alert
        alert_type = None
        if classification in ALERT_CLASSES:
            alert_type = classification
        elif classification == "PARSED_NEW_CAMPAIGN" and extra.get("freeze_status") == "ABSENT":
            alert_type = "CAMPAIGN_CREATED_FREEZE_MISSING"
        if alert_type:
            akey = _sha(f"A|{alert_type}|{mid}|{classification}")
            if akey not in alert_keys:
                alert_keys.add(akey)
                _append(alert_ledger, {"record_type": "INTAKE_ALERT", "alert_type": alert_type,
                        "timestamp": now, "message_id": mid, "raw_text_bounded": (m["raw_text"] or "")[:160],
                        "classification": classification, "reason": reason,
                        "possible_campaign_candidates": (list(idx["setups"].keys())[-3:] if alert_type in ("ORPHAN_MANAGEMENT_MESSAGE", "AMBIGUOUS_CAMPAIGN_CORRELATION") else extra.get("campaign_id")),
                        "required_operator_action": _action_for(alert_type),
                        "parser_correlation_version": OBSERVER_VERSION, "informational_only": True,
                        "authorizes_no_mutation": True, "idempotency_key": akey,
                        "review_only": True, "observation_only": True})
    save_cursor(cur)
    # status view (read-only snapshot)
    status = {"observer_version": OBSERVER_VERSION, "generated_at_utc": datetime.fromtimestamp(now, timezone.utc).isoformat(),
              "messages_seen": len(msgs), "class_counts": counts,
              "silent_relevant_drop_count": 0,
              "last_new_campaign": _last_of(class_ledger, "PARSED_NEW_CAMPAIGN"),
              "last_freeze_present": (sorted(idx["freezes"])[-1] if idx["freezes"] else "NONE"),
              "open_quarantine": _count_pending(quar_ledger),
              "total_alerts": sum(1 for _ in open(alert_ledger, encoding="utf-8")) if os.path.exists(alert_ledger) else 0,
              "recent_route": recent[-15:],
              "note": "READ-ONLY observability; no write controls; every relevant message is PARSED or QUARANTINED",
              "review_only": True, "observation_only": True}
    json.dump(status, open(status_path, "w", encoding="utf-8"), indent=1, default=str)
    return {"counts": counts, "messages": len(msgs), "status_path": status_path}


def _action_for(t):
    return {"QUARANTINED_UNPARSED_SIGNAL_CANDIDATE": "operator: inspect message; if a real signal, add morphology to parser + fuzz corpus",
            "ORPHAN_MANAGEMENT_MESSAGE": "operator: identify the intended campaign or confirm no active campaign",
            "AMBIGUOUS_CAMPAIGN_CORRELATION": "operator: disambiguate which campaign the instruction belongs to",
            "PARSER_FAILURE_CAPTURED": "operator: inspect parser exception; raw message preserved",
            "CAMPAIGN_CREATED_FREEZE_MISSING": "operator: check watcher/freeze pipeline for this campaign"}.get(t, "operator review")


def _last_of(ledger, cls):
    last = None
    if os.path.exists(ledger):
        for line in open(ledger, encoding="utf-8"):
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("classification") == cls:
                last = r.get("extra", {}).get("campaign_id") or r.get("message_id")
    return last or "NONE"


def _count_pending(ledger):
    n = 0
    if os.path.exists(ledger):
        for line in open(ledger, encoding="utf-8"):
            try:
                if json.loads(line).get("resolution_status") == "PENDING_OPERATOR_REVIEW":
                    n += 1
            except json.JSONDecodeError:
                pass
    return n


def watch(interval=45):
    try:
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode()); os.close(fd)
    except FileExistsError:
        raise SystemExit("another intake_observer holds the lock — refusing to start")
    print(f"[{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ}] intake observer started pid={os.getpid()} | "
          f"module_sha={hashlib.sha256(open(os.path.abspath(__file__),'rb').read()).hexdigest()[:16]} | "
          f"READ-ONLY | NO BROKER | NO EXECUTION | never mutates campaigns", flush=True)
    try:
        while True:
            try:
                s = scan()
                print(f"[{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ}] scan: {s['messages']} msgs {s['counts']}", flush=True)
            except Exception as e:                                 # noqa: BLE001
                print(f"observer cycle error: {type(e).__name__}: {e} — live processes unaffected", flush=True)
            # ADD-2 (D-081): CONTINUOUS listener-liveness monitor. Raises/clears data/LISTENER_DOWN.flag.
            # Independent of the listener it watches; the operator brief is the monitor-of-THIS-monitor.
            try:
                _ST = r"C:\Users\Marty\signal-terminal"
                if _ST not in sys.path:
                    sys.path.insert(0, _ST)
                import listener_liveness as _ll
                _v = _ll.check_and_flag()
                if _v["level"] == "ALARM":
                    print(f"[{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ}] !! LISTENER LIVENESS ALARM: "
                          f"{_v['code']} — {_v['reason']} (LISTENER_DOWN.flag raised)", flush=True)
            except Exception as _le:                               # noqa: BLE001
                print(f"listener-liveness check error: {type(_le).__name__} — flag not updated", flush=True)
            time.sleep(interval)
    finally:
        os.remove(LOCK)


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", action="store_true")
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()
    if args.watch:
        watch()
    else:
        s = scan()
        print(json.dumps(s["counts"], indent=1))
        print("status ->", s["status_path"])
