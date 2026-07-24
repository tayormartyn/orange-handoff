"""
L0 live bridge (FAROUK only). Watches newly-appended Telegram listener rows, classifies possible
Gold/XAUUSD entry signals, and writes an APPEND-ONLY PENDING_HUMAN_CONFIRMATION candidate + a
console/latest-file notification. It NEVER auto-confirms, places an order, writes campaign state,
or treats management/commentary as a new entry. Proposed entry values are candidate-only.
"""
from __future__ import annotations
import json
import os
import re
import sqlite3
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVID = os.path.join(_ROOT, "campaign_extractor", "prospective", "data", "prospective_evidence_v1.db")
CAND_DB = os.path.join(_ROOT, "data", "live_candidates_v1.db")
STATE = os.path.join(_ROOT, "data", "live_bridge_state.json")
LATEST = os.path.join(_ROOT, "data", "live_candidate_latest.json")
FAROUK_CHANNEL = "-1001902136163"

GOLD = re.compile(r"\b(gold|xau ?usd|xau)\b", re.I)
DIR = re.compile(r"\b(buy|sell)\b", re.I)
RANGE = re.compile(r"(\d{3,5}(?:\.\d+)?)\s*[-/]\s*(\d{3,5}(?:\.\d+)?)")
MGMT = re.compile(r"\b(tp\d?|sl|stop|close[d]?|breakeven|move|running|secure|book)\b", re.I)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pending_candidates (
  rowseq INTEGER PRIMARY KEY AUTOINCREMENT,
  candidate_id TEXT NOT NULL UNIQUE, provider_id TEXT NOT NULL, source_channel_id TEXT,
  source_message_id TEXT, listener_received_at TEXT, telegram_posted_at TEXT, parsed_at TEXT,
  raw_text_hash TEXT, raw_text_excerpt TEXT, gold INTEGER, direction_present INTEGER,
  entry_range_present INTEGER, proposed_direction TEXT, proposed_entry_low TEXT,
  proposed_entry_high TEXT, classification TEXT NOT NULL, status TEXT NOT NULL,
  labels TEXT, created_at TEXT);
CREATE TRIGGER IF NOT EXISTS cand_no_update BEFORE UPDATE ON pending_candidates
  BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS cand_no_delete BEFORE DELETE ON pending_candidates
  BEGIN SELECT RAISE(ABORT, 'append-only'); END;
"""


def _db():
    os.makedirs(os.path.dirname(CAND_DB), exist_ok=True)
    conn = sqlite3.connect(CAND_DB)
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


def _load_watermark():
    if os.path.exists(STATE):
        return json.load(open(STATE)).get("last_rowseq", 0)
    return 0


def _save_watermark(rowseq):
    json.dump({"last_rowseq": rowseq, "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
              open(STATE, "w"))


def current_max_rowseq():
    e = sqlite3.connect(f"file:{EVID}?mode=ro", uri=True)
    r = e.execute("SELECT MAX(rowseq) FROM prospective_message_evidence").fetchone()[0] or 0
    e.close()
    return r


def baseline_to_now():
    """Arm the bridge from the current latest row — only messages appended AFTER now are watched."""
    m = current_max_rowseq()
    _save_watermark(m)
    return m


def classify(text):
    t = text or ""
    gold, direction = bool(GOLD.search(t)), bool(DIR.search(t))
    m = RANGE.search(t)
    if gold and direction and m:
        return "QUALIFYING_GOLD_SIGNAL", "PENDING_HUMAN_CONFIRMATION", m
    if gold and MGMT.search(t) and not m:
        return "MANAGEMENT_ONLY", "NOT_A_NEW_ENTRY", None      # never processed as a new entry
    if gold:
        return "INCOMPLETE_SIGNAL", "NEEDS_MORE_EVIDENCE", None
    return "NOT_GOLD", "IGNORED_NON_GOLD", None


def watch(max_seconds=3600, poll_seconds=60):
    """Poll for newly-appended FAROUK rows until a QUALIFYING Gold candidate appears or the window
    ends. Read-only on the listener DB; only writes append-only pending candidates. Never confirms."""
    deadline = time.monotonic() + max_seconds
    polls = 0
    while time.monotonic() < deadline:
        polls += 1
        found = scan()
        if found:
            return {"status": "CANDIDATE_FOUND", "candidates": found, "polls": polls}
        time.sleep(poll_seconds)
    return {"status": "NO_CANDIDATE_IN_WINDOW", "polls": polls}


def scan(notify=True):
    """Process newly-appended FAROUK listener rows since the watermark. Returns new qualifying
    candidates. Idempotent (advances watermark; UNIQUE candidate_id)."""
    wm = _load_watermark()
    e = sqlite3.connect(f"file:{EVID}?mode=ro", uri=True)
    rows = e.execute("SELECT rowseq, telegram_message_id, telegram_channel_id, telegram_posted_at_utc, "
                     "listener_received_at_utc, parser_completed_at_utc, raw_text, raw_text_hash "
                     "FROM prospective_message_evidence WHERE rowseq > ? ORDER BY rowseq", (wm,)).fetchall()
    e.close()
    conn = _db()
    import hashlib
    qualifying = []
    max_seq = wm
    for (rs, mid, ch, posted, recv, parsed, text, rhash) in rows:
        max_seq = max(max_seq, rs)
        if str(ch) != FAROUK_CHANNEL:                          # L0: FAROUK only
            continue
        cls, status, m = classify(text)
        excerpt = re.sub(r"\s+", " ", text or "").strip()[:200]
        cid = f"cand-FAROUK-{mid}"
        rec = (cid, "FAROUK", str(ch), str(mid), recv, posted, parsed,
               rhash or (hashlib.sha256((text or "").encode()).hexdigest()),
               excerpt, int(bool(GOLD.search(text or ""))), int(bool(DIR.search(text or ""))),
               int(m is not None),
               (DIR.search(text or "").group(1).upper() if DIR.search(text or "") else None),
               (m.group(1) if m else None), (m.group(2) if m else None), cls, status,
               json.dumps(["OBSERVATION_ONLY", "PAPER_ONLY", "NOT_A_FILL", "NOT_AN_OUTCOME"]),
               time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        try:
            conn.execute("INSERT INTO pending_candidates (candidate_id,provider_id,source_channel_id,"
                         "source_message_id,listener_received_at,telegram_posted_at,parsed_at,"
                         "raw_text_hash,raw_text_excerpt,gold,direction_present,entry_range_present,"
                         "proposed_direction,proposed_entry_low,proposed_entry_high,classification,"
                         "status,labels,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rec)
            conn.commit()
        except sqlite3.IntegrityError:
            continue                                           # already seen (idempotent)
        if status == "PENDING_HUMAN_CONFIRMATION":
            cand = {"candidate_id": cid, "provider": "FAROUK", "source_message_id": mid,
                    "instrument_hint": "XAUUSD/GOLD", "proposed_direction": rec[12],
                    "proposed_entry_low": rec[13], "proposed_entry_high": rec[14],
                    "listener_received_at": recv, "telegram_posted_at": posted, "parsed_at": parsed,
                    "text_excerpt": excerpt, "status": "PENDING_HUMAN_CONFIRMATION",
                    "note": "PROPOSED values are candidate-only; requires human confirmation. Not a fill."}
            qualifying.append(cand)
            if notify:
                json.dump(cand, open(LATEST, "w"), indent=2)
                print(f"[PENDING_HUMAN_CONFIRMATION] FAROUK msg={mid} {rec[12]} "
                      f"entry {rec[13]}-{rec[14]} | {excerpt[:80]}")
    conn.close()
    _save_watermark(max_seq)
    return qualifying
