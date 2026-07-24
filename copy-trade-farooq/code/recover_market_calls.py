"""
recover_market_calls.py — LLM-recover the gold MARKET-CALL entries the parser dropped.

Farouk posts many gold entries with NO explicit entry price ("gold long sl 4440",
"GOLD Long First TP: 30 pips sl 4218") — the follower enters at MARKET. The
deterministic parser needs an entry price, so these were missing/broken and excluded
from the clean limit-zone edge. The capture-recall check showed they include LOSSES
(e.g. 2026-01-07). We recover them so the edge can be measured INCLUDING them.

Recover (where GENUINELY present, never invented; honest if absent):
  is_genuine_entry, direction, stop (absolute), targets_abs (absolute prices),
  targets_pips (pip offsets if stated as pips). The ENTRY is intentionally NOT
  recovered — it is a market entry, priced later from real ticks at posted time.

Append-only + traceable -> parser_revisions.db (market_call_recoveries). Reads
ARCHIVED raw text only (no Telegram). Archive + signed-off 28 + LIVE stub untouched.

Usage: python recover_market_calls.py recover
"""

import os
import re
import sqlite3
import sys
import uuid
from datetime import datetime, timezone

import backfill_audit as BA
import config
import gold_clean_report as G
import module_b_parser as parser

REVISIONS_DB = "data/parser_revisions.db"
MODEL = config.PARSER_MODEL
GOLD_BAND = (800.0, 8000.0)

_CALL = re.compile(r"\bgold\s+(long|short|buy|sell)\b", re.I)
_CUE = re.compile(r"\b(sl|tp|stop|target)\b", re.I)

_SYS = (
    "You read ONE gold (XAU/USD) trade message and extract a MARKET-ENTRY call's "
    "parameters. The follower enters at market, so there is intentionally NO entry "
    "price to extract — only direction, stop-loss, and take-profits.\n"
    "Rules:\n"
    "- is_genuine_entry=true ONLY if this is a NEW gold trade entry instruction "
    "(a call to get in now / market). Commentary, recaps, management-only updates, "
    "or pure analysis => false.\n"
    "- direction: LONG or SHORT (map buy->LONG, sell->SHORT).\n"
    "- stop: the absolute stop-loss PRICE if stated (e.g. 'sl 4440', 'stop loss 4218').\n"
    "- targets_abs: absolute take-profit PRICES if stated as prices (e.g. 'TP1 4088').\n"
    "- targets_pips: take-profits stated as PIP offsets (e.g. 'First TP: 30 pips' -> [30]).\n"
    "- NEVER invent a stop or target that isn't written. Empty/absent => null or []."
)

_TOOL = {
    "name": "record_market_call",
    "description": "Extract a gold market-entry call's direction, stop, and targets.",
    "input_schema": {
        "type": "object",
        "properties": {
            "is_genuine_entry": {"type": "boolean"},
            "direction": {"type": ["string", "null"], "enum": ["LONG", "SHORT", None]},
            "stop": {"type": ["number", "null"]},
            "targets_abs": {"type": "array", "items": {"type": "number"}},
            "targets_pips": {"type": "array", "items": {"type": "number"}},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        },
        "required": ["is_genuine_entry", "direction", "stop", "targets_abs",
                     "targets_pips", "confidence"],
    },
}


def _rev_conn():
    os.makedirs("data", exist_ok=True)
    c = sqlite3.connect(REVISIONS_DB)
    c.row_factory = sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS market_call_recoveries (
        revision_id TEXT PRIMARY KEY, message_key TEXT UNIQUE, sent_at_utc TEXT,
        is_genuine_entry INTEGER, direction TEXT, stop TEXT,
        targets_abs TEXT, targets_pips TEXT, confidence TEXT,
        validation TEXT NOT NULL, model TEXT NOT NULL, raw_text TEXT,
        created_at_utc TEXT NOT NULL)""")
    return c


def identify(conn):
    """gold market-call messages NOT in the clean limit-zone set."""
    gold = BA.load_gold(conn)
    clean_keys = set()
    for s in gold:
        is_b, _ = G.classify(s)
        if not is_b:
            clean_keys.add(s["source_message_key"])
    rows = conn.execute(
        "SELECT message_key, sent_at_utc, raw_text FROM raw_message_versions r "
        "JOIN (SELECT message_key mk, MAX(version_number) v FROM raw_message_versions "
        "GROUP BY message_key) m ON r.message_key=m.mk AND r.version_number=m.v "
        "WHERE sent_at_utc>='2025-06-13' AND raw_text LIKE '%gold-trades%'").fetchall()
    out = []
    for r in rows:
        t = r["raw_text"] or ""
        if _CALL.search(t) and _CUE.search(t) and len(t) < 300 and r["message_key"] not in clean_keys:
            out.append(dict(r))
    return out


def extract(raw_text):
    client = parser._client()
    resp = client.messages.create(
        model=MODEL, max_tokens=600, system=_SYS, tools=[_TOOL],
        tool_choice={"type": "tool", "name": "record_market_call"},
        messages=[{"role": "user", "content": raw_text}])
    b = next((x for x in resp.content if getattr(x, "type", None) == "tool_use"), None)
    if b is None:
        raise ValueError("no tool_use")
    return b.input


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def validate(d):
    if not d.get("is_genuine_entry"):
        return "rejected:not-entry"
    if (d.get("direction") or "").upper() not in ("LONG", "SHORT"):
        return "rejected:no-direction"
    s = _f(d.get("stop"))
    if s is None:
        return "accepted:no-stop"          # genuine entry but no stop (risk undefined later)
    if not (GOLD_BAND[0] <= s <= GOLD_BAND[1]):
        return f"rejected:implausible-stop({s:g})"
    return "accepted"


def cmd_recover():
    import json
    arch = BA._ro_conn()
    cands = identify(arch)
    arch.close()
    rev = _rev_conn()
    done = {r["message_key"] for r in rev.execute("SELECT message_key FROM market_call_recoveries")}
    todo = [c for c in cands if c["message_key"] not in done]
    print(f"market-call candidates: {len(cands)}  done: {len(done)}  to do: {len(todo)}")
    for i, c in enumerate(todo, 1):
        try:
            d = extract(c["raw_text"])
            v = validate(d)
        except Exception as e:  # noqa: BLE001
            d, v = {}, f"error:{type(e).__name__}"
        rev.execute(
            "INSERT OR IGNORE INTO market_call_recoveries(revision_id, message_key, "
            "sent_at_utc, is_genuine_entry, direction, stop, targets_abs, targets_pips, "
            "confidence, validation, model, raw_text, created_at_utc) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), c["message_key"], c["sent_at_utc"],
             1 if d.get("is_genuine_entry") else 0, (d.get("direction") or None),
             str(_f(d.get("stop"))) if _f(d.get("stop")) is not None else None,
             json.dumps(d.get("targets_abs") or []), json.dumps(d.get("targets_pips") or []),
             d.get("confidence"), v, MODEL, c["raw_text"],
             datetime.now(timezone.utc).isoformat()))
        if i % 15 == 0:
            print(f"  ...{i}/{len(todo)}")
    rev.commit()
    from collections import Counter
    rows = rev.execute("SELECT validation, is_genuine_entry, stop, targets_abs, targets_pips "
                       "FROM market_call_recoveries").fetchall()
    c = Counter(r["validation"].split(":")[0].split("(")[0] for r in rows)
    print(f"\n  RECOVERY SUMMARY ({len(rows)} candidates):", dict(c))
    acc = [r for r in rows if r["validation"].startswith("accepted")]
    with_stop = sum(1 for r in acc if r["stop"])
    with_tp = sum(1 for r in acc if (r["targets_abs"] not in ("[]", None)) or (r["targets_pips"] not in ("[]", None)))
    print(f"  accepted genuine entries: {len(acc)}  (with stop: {with_stop}, with TP: {with_tp})")
    rev.close()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "recover"
    if cmd == "recover":
        cmd_recover()
    else:
        print("usage: python recover_market_calls.py recover")
