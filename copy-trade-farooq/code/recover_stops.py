"""
recover_stops.py — LLM re-parse to recover STOPS the deterministic parser missed.

This is DATA CLEANING, not a scoring change: the deterministic parser failed to
extract a stop-loss for 178 back-filled gold signals (so their R was uncalculable).
Farouk often writes stops in formats the regex parser missed ("SL 4218", "stop:
3300", "sl 1234.5", inline in prose). We re-read each ORIGINAL raw message with the
LLM and recover the stop level ONLY where it is genuinely present — never invented.

Honesty rules:
  * If the message contains no original protective stop, we leave it flagged as
    no-stop (stop_present=false). We do NOT fabricate one.
  * A recovered stop is VALIDATED before acceptance: numeric, on the correct side
    of entry (LONG stop<entry, SHORT stop>entry), in a plausible gold band, and not
    equal to a target. A recovered value that fails validation is recorded as
    rejected (kept for audit), not used.
  * Append-only + traceable: recoveries go to a SEPARATE data/parser_revisions.db
    (the signed-off archive is never mutated). Each row records the model, the exact
    source snippet, confidence, and validation status. Re-runs are idempotent.

Scoring is unchanged: re-scoring (recovered_rescore) feeds the recovered stop into
the EXISTING signed-off scorer (archive._score_r); no scoring logic is modified.

PAPER mode. Reads already-archived raw text (NO Telegram access). LIVE stub +
signed-off 28 untouched.

Usage:
    python recover_stops.py recover     # LLM-recover stops, store revisions
    python recover_stops.py report      # re-score with recoveries + cleaned summary
"""

import json
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import config
import module_b_parser as parser   # reuse the working Anthropic client

ARCHIVE_DB = "data/signal_archive.db"
REVISIONS_DB = "data/parser_revisions.db"
MODEL = config.PARSER_MODEL        # explicit project parser model (claude-sonnet-4-6)

GOLD_BAND = (800.0, 8000.0)

_SYS = (
    "You extract the ORIGINAL protective stop-loss from a single trading-signal "
    "message for gold (XAU/USD). The deterministic parser already has the entry and "
    "direction; you ONLY recover the stop-loss level.\n"
    "Rules:\n"
    "- Return stop_present=true ONLY if the message explicitly states a stop-loss / "
    "SL / stop for THIS entry (e.g. 'SL 4218', 'stop 3300', 'sl: 1234.5'). Stops may "
    "appear inline in prose.\n"
    "- 'SL to entry', 'move SL', 'stop to breakeven' are MANAGEMENT updates, not an "
    "original stop — do NOT treat those as the entry stop.\n"
    "- NEVER invent or infer a stop that isn't written. If there is no explicit stop, "
    "return stop_present=false and stop_value=null.\n"
    "- stop_value must be the numeric price exactly as written."
)

_TOOL = {
    "name": "record_stop",
    "description": "Record the original stop-loss if genuinely present, else mark absent.",
    "input_schema": {
        "type": "object",
        "properties": {
            "stop_present": {"type": "boolean"},
            "stop_value": {"type": ["number", "null"]},
            "stop_text": {"type": ["string", "null"],
                          "description": "exact snippet the stop came from, or null"},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        },
        "required": ["stop_present", "stop_value", "stop_text", "confidence"],
    },
}


# ----------------------------------------------------------------------------
# revisions DB (append-only, separate from the archive)
# ----------------------------------------------------------------------------
def _rev_conn():
    os.makedirs("data", exist_ok=True)
    c = sqlite3.connect(REVISIONS_DB)
    c.row_factory = sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS stop_recoveries (
        revision_id TEXT PRIMARY KEY,
        signal_id TEXT NOT NULL,
        source_message_key TEXT,
        asset TEXT, direction TEXT, entry_low TEXT, entry_high TEXT,
        original_stop TEXT,                 -- what the archive had (empty/None)
        stop_present INTEGER NOT NULL,      -- LLM says a stop is in the message
        recovered_stop TEXT,               -- the value (str) or NULL
        stop_text TEXT, confidence TEXT,
        validation TEXT NOT NULL,          -- accepted | rejected:<reason> | absent | error
        model TEXT NOT NULL, raw_text TEXT,
        created_at_utc TEXT NOT NULL,
        UNIQUE(signal_id))""")
    return c


def _utc():
    return datetime.now(timezone.utc).isoformat()


# ----------------------------------------------------------------------------
# load the missing-stop gold signals from the archive (read-only)
# ----------------------------------------------------------------------------
def load_missing_stop(conn):
    rows = conn.execute("""
        SELECT s.signal_id, s.source_message_key, s.direction, s.entry_low, s.entry_high,
               s.stop, s.tp1, s.tp2, s.tp3
        FROM signals s
        WHERE s.asset='XAUUSD' AND s.source_message_key NOT LIKE 'telegram:baseline:%'
              AND (s.stop IS NULL OR TRIM(s.stop)='')
        ORDER BY s.sent_at_utc""").fetchall()
    out = []
    for r in rows:
        rt = conn.execute("SELECT raw_text FROM raw_message_versions WHERE message_key=? "
                          "ORDER BY version_number DESC LIMIT 1",
                          (r["source_message_key"],)).fetchone()
        d = dict(r)
        d["raw_text"] = (rt["raw_text"] if rt else "") or ""
        out.append(d)
    return out


# ----------------------------------------------------------------------------
# LLM extraction
# ----------------------------------------------------------------------------
def extract_stop(sig):
    client = parser._client()
    ctx = (f"Direction: {sig['direction']}\nEntry: {sig['entry_low']}-{sig['entry_high']}\n"
           f"--- message ---\n{sig['raw_text']}")
    resp = client.messages.create(
        model=MODEL, max_tokens=512, system=_SYS, tools=[_TOOL],
        tool_choice={"type": "tool", "name": "record_stop"},
        messages=[{"role": "user", "content": ctx}],
    )
    block = next((b for b in resp.content if getattr(b, "type", None) == "tool_use"), None)
    if block is None:
        raise ValueError("no tool_use returned")
    return block.input


def _f(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def validate(sig, data):
    """Return (validation_str, recovered_stop_or_None)."""
    if not data.get("stop_present"):
        return "absent", None
    sv = _f(data.get("stop_value"))
    if sv is None or sv == 0:
        return "rejected:non-numeric-or-zero", None
    lo, hi = _f(sig["entry_low"]), _f(sig["entry_high"])
    entry_mid = (lo + hi) / 2 if (lo is not None and hi is not None) else lo
    if entry_mid is None:
        return "rejected:no-entry-to-check", None
    # If the ENTRY itself isn't a plausible gold price, this isn't a real gold
    # signal (the parser mis-tagged commentary/stocks as XAUUSD) — a recovered
    # stop would be meaningless, so don't accept one.
    if not (GOLD_BAND[0] <= entry_mid <= GOLD_BAND[1]):
        return f"rejected:non-gold-entry({entry_mid:g})", None
    if not (GOLD_BAND[0] <= sv <= GOLD_BAND[1]):
        return f"rejected:implausible-gold({sv:g})", None
    d = (sig["direction"] or "").upper()
    if d in ("LONG", "BUY") and sv >= entry_mid:
        return f"rejected:wrong-side(long sl {sv:g}>=entry {entry_mid:g})", None
    if d in ("SHORT", "SELL") and sv <= entry_mid:
        return f"rejected:wrong-side(short sl {sv:g}<=entry {entry_mid:g})", None
    for tp in (sig["tp1"], sig["tp2"], sig["tp3"]):
        if _f(tp) is not None and abs(_f(tp) - sv) < 1e-9:
            return "rejected:equals-target", None
    return "accepted", sv


def cmd_recover():
    arch = sqlite3.connect(f"file:{ARCHIVE_DB}?mode=ro", uri=True)
    arch.row_factory = sqlite3.Row
    sigs = load_missing_stop(arch)
    arch.close()
    rev = _rev_conn()
    done = {r["signal_id"] for r in rev.execute("SELECT signal_id FROM stop_recoveries")}
    todo = [s for s in sigs if s["signal_id"] not in done]
    print(f"missing-stop gold signals: {len(sigs)}  already done: {len(done)}  to do: {len(todo)}")

    for i, s in enumerate(todo, 1):
        try:
            data = extract_stop(s)
            valn, stop = validate(s, data)
        except Exception as e:  # noqa: BLE001 — network/parse errors recorded, not fatal
            data, valn, stop = {}, f"error:{type(e).__name__}", None
        rev.execute(
            "INSERT OR IGNORE INTO stop_recoveries(revision_id, signal_id, "
            "source_message_key, asset, direction, entry_low, entry_high, original_stop, "
            "stop_present, recovered_stop, stop_text, confidence, validation, model, "
            "raw_text, created_at_utc) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), s["signal_id"], s["source_message_key"], "XAUUSD",
             s["direction"], s["entry_low"], s["entry_high"], s["stop"],
             1 if data.get("stop_present") else 0, str(stop) if stop is not None else None,
             data.get("stop_text"), data.get("confidence"), valn, MODEL,
             s["raw_text"], _utc()))
        if i % 20 == 0:
            print(f"  ...{i}/{len(todo)}")
    rev.commit()
    _recover_summary(rev)
    rev.close()


def _recover_summary(rev):
    rows = rev.execute("SELECT validation FROM stop_recoveries").fetchall()
    from collections import Counter
    c = Counter(r["validation"].split(":")[0] for r in rows)
    acc = rev.execute("SELECT COUNT(*) FROM stop_recoveries WHERE validation='accepted'").fetchone()[0]
    print(f"\n  RECOVERY SUMMARY ({len(rows)} signals):")
    for k, v in c.most_common():
        print(f"    {k:10} {v}")
    print(f"  -> {acc} stops recovered + validated (genuinely present in the message)")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "recover"
    if cmd == "recover":
        cmd_recover()
    elif cmd == "report":
        import recovered_rescore
        recovered_rescore.main()
    else:
        print("usage: python recover_stops.py [recover|report]")
