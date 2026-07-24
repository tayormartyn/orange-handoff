"""
archive.py — PHASE 1 of the permanent, append-only signal archive.

SQLite is the SOURCE OF TRUTH; CSV is an EXPORT ONLY. This replaces the shifting
1500-message Telegram window with a permanent, growing archive that NEVER silently
loses or overwrites data.

  * PAPER MODE. Read-only to Telegram. Never touches paper_log.csv or the LIVE stub.
  * One transaction per import: success = commit, failure = rollback (no partial batch).
  * raw_message_versions / outcome_evidence / manual_overrides are APPEND-ONLY.
  * outcome_projections is derived and fully rebuildable from raw + signals + overrides.

Projection precedence:  active manual override  >  verified deterministic evidence
  >  accepted automatic evidence  >  unknown.  An auto-run may REPORT a conflict
  with an override but must NEVER replace it.

Commands:
    python archive.py import [--csv FILE | --limit N --sender NAME]
    python archive.py rebuild-projections
    python archive.py export-csv [--out FILE]
    python archive.py backup
    python archive.py integrity-check
    python archive.py archive-status
    python archive.py baseline            # one-time: build + verify the signed-off baseline
"""

import csv
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import config
import module_a_telegram as listener

# ----------------------------------------------------------------------------
# Constants / versions
# ----------------------------------------------------------------------------
SCHEMA_VERSION = 2          # v2: added the append-only signal_timing table
DATA_DIR = "data"
DB_PATH = os.path.join(DATA_DIR, "signal_archive.db")
EXPORT_CSV = os.path.join(DATA_DIR, "signal_archive_export.csv")
SNAPSHOT_DIR = os.path.join(DATA_DIR, "audit_snapshots")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
BASELINE_CSV = "history_review_FINAL_SIGNOFF.csv"

CODE_VERSION = "archive-phase1"
DETECTOR_VERSION = "signoff-r4"        # the signed-off re-entry-boundary detector
CALC_VERSION = "r-goldpip-v1"          # gold $0.10 pip, furthest-target cap, boundary
PARSER_VERSION = "regex-v1"

# A fixed namespace so signal_ids are DETERMINISTIC (re-import == same id).
_SIGNAL_NS = uuid.UUID("6f9b8c2a-1d4e-4f3a-9c7b-0a1b2c3d4e5f")

_WIN_CATS = listener._WIN_CATEGORIES
_LOSS_CATS = listener._LOSS_CATEGORIES
_KNOWN_CATEGORIES = {
    listener.OUT_TARGET_HIT, listener.OUT_MANAGED_PROFIT, listener.OUT_PROFIT_RUNKNOWN,
    listener.OUT_MANUAL_LOSS, listener.OUT_STOP_LOSS, listener.OUT_BREAKEVEN,
    listener.OUT_MISSED, listener.OUT_UNCLEAR,
}


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _content_hash(text):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _message_key(channel_id, message_id):
    return f"telegram:{channel_id}:{message_id}"


def _signal_id(message_key, index):
    return str(uuid.uuid5(_SIGNAL_NS, f"{message_key}#{index}"))


# ----------------------------------------------------------------------------
# Connection + schema
# ----------------------------------------------------------------------------
def connect(db_path=DB_PATH):
    """Open the archive DB with the durability/integrity settings Phase 1 requires."""
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path, isolation_level=None)   # we manage transactions
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    init_schema(conn)
    return conn


_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_meta (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    schema_version INTEGER NOT NULL,
    applied_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS import_batches (
    batch_id           TEXT PRIMARY KEY,
    started_at_utc     TEXT NOT NULL,
    completed_at_utc   TEXT,
    messages_seen      INTEGER NOT NULL DEFAULT 0,
    messages_inserted  INTEGER NOT NULL DEFAULT 0,
    duplicates_skipped INTEGER NOT NULL DEFAULT 0,
    status             TEXT NOT NULL,
    code_version       TEXT,
    detector_version   TEXT
);

-- APPEND-ONLY. A Telegram edit (same key, new hash) appends a NEW version.
CREATE TABLE IF NOT EXISTS raw_message_versions (
    row_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    message_key     TEXT NOT NULL,
    channel_id      TEXT,
    message_id      TEXT,
    content_hash    TEXT NOT NULL,
    raw_text        TEXT NOT NULL,
    sent_at_utc     TEXT,
    edited_at_utc   TEXT,
    captured_at_utc TEXT NOT NULL,
    version_number  INTEGER NOT NULL,
    batch_id        TEXT REFERENCES import_batches(batch_id),
    UNIQUE (message_key, content_hash)
);
CREATE INDEX IF NOT EXISTS ix_rmv_key ON raw_message_versions(message_key);

CREATE TABLE IF NOT EXISTS signals (
    signal_id           TEXT PRIMARY KEY,
    source_message_key  TEXT NOT NULL,
    source_signal_index INTEGER NOT NULL DEFAULT 0,
    provider            TEXT,
    asset               TEXT,
    asset_class         TEXT,
    direction           TEXT,
    entry_low           TEXT,
    entry_high          TEXT,
    stop                TEXT,
    tp1                 TEXT,
    tp2                 TEXT,
    tp3                 TEXT,
    classification      TEXT,
    parser_version      TEXT,
    sent_at_utc         TEXT,
    created_at_utc      TEXT NOT NULL,
    UNIQUE (source_message_key, source_signal_index)
);

-- APPEND-ONLY. Rejected evidence is recorded too (accepted=0 + a reason) so
-- nothing is ever silently ignored.
CREATE TABLE IF NOT EXISTS outcome_evidence (
    evidence_id          TEXT PRIMARY KEY,
    signal_id            TEXT NOT NULL REFERENCES signals(signal_id),
    evidence_message_key TEXT,
    evidence_type        TEXT,
    numeric_value        REAL,
    unit                 TEXT,
    detector_version     TEXT,
    accepted             INTEGER NOT NULL,
    rejection_reason     TEXT,
    created_at_utc       TEXT NOT NULL,
    UNIQUE (signal_id, evidence_message_key, evidence_type, accepted, detector_version)
);

-- Derived / rebuildable: the CURRENT calculated result per signal.
CREATE TABLE IF NOT EXISTS outcome_projections (
    signal_id                  TEXT PRIMARY KEY REFERENCES signals(signal_id),
    outcome_category           TEXT,
    binary_rollup              TEXT,
    calculated_r               TEXT,
    r_is_known                 INTEGER NOT NULL DEFAULT 0,
    primary_evidence_message_key TEXT,
    source                     TEXT,          -- override / evidence / unknown
    override_conflict          TEXT,          -- set if an auto-run disagrees with an active override
    calculation_version        TEXT,
    calculated_at_utc          TEXT NOT NULL
);

-- APPEND-ONLY. Never edit an override — supersede it with a new row.
CREATE TABLE IF NOT EXISTS manual_overrides (
    override_id           TEXT PRIMARY KEY,
    signal_id             TEXT NOT NULL REFERENCES signals(signal_id),
    override_type         TEXT,
    override_payload      TEXT,
    reason                TEXT,
    created_at_utc        TEXT NOT NULL,
    supersedes_override_id TEXT REFERENCES manual_overrides(override_id),
    is_active             INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS ix_ovr_signal ON manual_overrides(signal_id);

-- APPEND-ONLY capture of the per-stage timestamps + processing delays + the price
-- context available at capture time. This is FOUNDATIONAL GROUNDWORK for shadow
-- mode (a separate FUTURE build): it only RECORDS the raw timing/price data shadow
-- mode will consume — it computes NO shadow result here. One row per signal,
-- captured once (never updated). price_context is JSON and includes a clearly
-- labelled, currently-null slot for the real broker/market price to be filled in
-- during the shadow-mode phase.
CREATE TABLE IF NOT EXISTS signal_timing (
    timing_id                 TEXT PRIMARY KEY,
    signal_id                 TEXT NOT NULL REFERENCES signals(signal_id),
    telegram_posted_at        TEXT,    -- the message's own timestamp (UTC)
    listener_received_at      TEXT,    -- when our listener captured it (UTC)
    parsed_at                 TEXT,    -- when parsing completed (UTC)
    received_minus_posted_sec REAL,    -- listener capture latency (s); NULL if unknown
    parsed_minus_received_sec REAL,    -- parse processing time (s); NULL if unknown
    price_context             TEXT,    -- JSON: prices available at capture (+ market_price slot)
    code_version              TEXT,
    captured_at_utc           TEXT NOT NULL,
    UNIQUE (signal_id)
);
"""


def init_schema(conn):
    conn.executescript(_SCHEMA)           # CREATE ... IF NOT EXISTS adds new tables safely
    row = conn.execute("SELECT schema_version FROM schema_meta WHERE id = 1").fetchone()
    if row is None:
        conn.execute("INSERT INTO schema_meta(id, schema_version, applied_at_utc) VALUES (1, ?, ?)",
                     (SCHEMA_VERSION, _utc_now()))
    elif row[0] < SCHEMA_VERSION:
        # forward migration: the new table is already created above; record the bump.
        conn.execute("UPDATE schema_meta SET schema_version=?, applied_at_utc=? WHERE id=1",
                     (SCHEMA_VERSION, _utc_now()))


# ----------------------------------------------------------------------------
# Timestamp + price-context capture (groundwork for shadow mode — NOT shadow mode)
# ----------------------------------------------------------------------------
def _parse_dt(s):
    """Tolerant parse of a stored timestamp -> datetime, or None. Handles full ISO
    (live pulls) and the historical 'YYYY-MM-DD HH:MM' baseline format."""
    if not s:
        return None
    s = str(s).strip()
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _delay_seconds(later, earlier):
    """(later - earlier) in seconds, or None if either is missing/unparseable or the
    two can't be compared (e.g. one tz-aware, one naive)."""
    a, b = _parse_dt(later), _parse_dt(earlier)
    if a is None or b is None:
        return None
    try:
        return (a - b).total_seconds()
    except TypeError:                    # naive vs aware -> not comparable
        return None


_PRICE_TOKEN_RE = None


def _extract_message_prices(text):
    """Plausible price-looking numbers in the raw text (rough capture for context)."""
    import re
    global _PRICE_TOKEN_RE
    if _PRICE_TOKEN_RE is None:
        _PRICE_TOKEN_RE = re.compile(r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b|\b\d{3,}(?:\.\d+)?\b|\b\d+\.\d+\b")
    seen, out = set(), []
    for m in _PRICE_TOKEN_RE.finditer(text or ""):
        v = m.group(0).replace(",", "")
        if v not in seen:
            seen.add(v)
            out.append(v)
        if len(out) >= 12:
            break
    return out


def _build_price_context(rec):
    """
    The price data AVAILABLE at capture time, as JSON. Contains the signal's own
    levels and any prices found in the message. The `market_price` slot is a
    CLEARLY-LABELLED PLACEHOLDER: the real broker/market price is captured in the
    shadow-mode phase (a separate future build) — it is NULL here on purpose.
    """
    lo, hi = _split_entry(rec.get("entry", ""))
    return {
        "captured_at_utc": _utc_now(),
        "signal_entry_low": lo or None,
        "signal_entry_high": hi or None,
        "signal_stop": rec.get("stop", "") or None,
        "message_prices": _extract_message_prices(rec.get("raw_text", "")),
        # ---- SHADOW-MODE PLACEHOLDER (FUTURE BUILD) --------------------------
        # The real market/broker price at capture time is NOT integrated yet.
        # Shadow mode will populate these from a live price source and only then
        # calculate a shadow fill/result. Nothing here computes a shadow outcome.
        "market_price": None,
        "market_price_source": None,
        "market_price_captured_at_utc": None,
        "note": ("PLACEHOLDER: real broker/market price is added in the shadow-mode "
                 "phase (not built yet). This row CAPTURES timing/price data only."),
    }


def _record_timing(conn, signal_id, rec):
    """
    APPEND-ONLY: record the per-stage timestamps, the computed delays, and the
    price context for one signal. INSERT OR IGNORE so a re-import never overwrites
    a signal's original capture timing. Must be called inside the import transaction.
    """
    posted = rec.get("sent_at_utc", "") or ""
    received = rec.get("listener_received_at", "") or ""
    parsed = rec.get("parsed_at", "") or ""
    conn.execute(
        "INSERT OR IGNORE INTO signal_timing(timing_id, signal_id, telegram_posted_at, "
        "listener_received_at, parsed_at, received_minus_posted_sec, "
        "parsed_minus_received_sec, price_context, code_version, captured_at_utc) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), signal_id, posted or None, received or None, parsed or None,
         _delay_seconds(received, posted), _delay_seconds(parsed, received),
         json.dumps(_build_price_context(rec)), CODE_VERSION, _utc_now()))


# ----------------------------------------------------------------------------
# Normalising messages (from a CSV baseline row or a live pull record)
# ----------------------------------------------------------------------------
def _records_from_csv(path):
    """
    Turn the signed-off review CSV into archive message records. Synthetic but
    STABLE keys (telegram:baseline:<n>) so re-imports dedupe. The detector still
    sees every message in order; the 28 clean rows become signals.
    """
    records = []
    with open(path, encoding="utf-8") as f:
        for i, r in enumerate(csv.DictReader(f)):
            is_sig = (r.get("Classification") == "clean signal")
            records.append({
                "channel_id": "baseline",
                "message_id": str(i),
                "raw_text": r.get("RawMessage", "") or "",
                "sent_at_utc": (r.get("Date") or ""),       # telegram_posted_at
                "edited_at_utc": "",
                # Historical back-fill: the listener-received / parsed stage times
                # were not captured at the time, so they're left blank ("where
                # available"). Delays are therefore NULL for baseline rows.
                "listener_received_at": "",
                "parsed_at": "",
                "sender": r.get("Sender", ""),
                "classification": r.get("Classification", ""),
                "asset": r.get("Asset", "") if is_sig else "",
                "direction": r.get("Direction", "") if is_sig else "",
                "entry": r.get("Entry", "") if is_sig else "",
                "stop": r.get("Stop", "") if is_sig else "",
                "tp1": r.get("TP1", "") if is_sig else "",
                "tp2": r.get("TP2", "") if is_sig else "",
                "tp3": r.get("TP3", "") if is_sig else "",
            })
    return records


def _split_entry(entry):
    """'4006-4016' -> ('4006','4016'); '4016' -> ('4016','4016'); '' -> ('','')."""
    import re
    nums = re.findall(r"\d[\d,]*\.?\d*", entry or "")
    if not nums:
        return "", ""
    nums = [n.replace(",", "") for n in nums]
    return nums[0], nums[-1]


def _is_signal_record(rec):
    """A record is a tradeable signal iff it has asset + direction + entry."""
    return bool((rec.get("asset") or "").strip()
                and (rec.get("direction") or "").strip()
                and (rec.get("entry") or "").strip())


# ----------------------------------------------------------------------------
# IMPORT  (one transaction; success = commit, failure = rollback)
# ----------------------------------------------------------------------------
def import_messages(conn, records, code_version=CODE_VERSION,
                    detector_version=DETECTOR_VERSION, _fail_after=None):
    """
    Append a pull's messages + signals in ONE transaction. Deduplicates raw
    messages by (message_key, content_hash) and signals by
    (source_message_key, source_signal_index). Returns the batch summary dict.
    `_fail_after` (int) is a TEST hook: raise after N raw inserts to prove rollback.
    """
    batch_id = str(uuid.uuid4())
    started = _utc_now()
    seen = inserted = dups = sig_inserted = 0
    conn.execute("BEGIN")
    try:
        # Insert the batch row first so raw rows can reference it; if anything
        # below fails, the ROLLBACK removes this row too (no partial batch).
        conn.execute(
            "INSERT INTO import_batches(batch_id, started_at_utc, status, code_version, "
            "detector_version) VALUES (?,?,?,?,?)",
            (batch_id, started, "running", code_version, detector_version))
        for n, rec in enumerate(records):
            seen += 1
            key = _message_key(rec.get("channel_id", ""), rec.get("message_id", ""))
            chash = _content_hash(rec.get("raw_text", ""))
            dup = conn.execute(
                "SELECT 1 FROM raw_message_versions WHERE message_key=? AND content_hash=?",
                (key, chash)).fetchone()
            if dup:
                dups += 1
            else:
                mx = conn.execute(
                    "SELECT COALESCE(MAX(version_number),0) FROM raw_message_versions WHERE message_key=?",
                    (key,)).fetchone()[0]
                conn.execute(
                    "INSERT INTO raw_message_versions(message_key, channel_id, message_id, "
                    "content_hash, raw_text, sent_at_utc, edited_at_utc, captured_at_utc, "
                    "version_number, batch_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (key, str(rec.get("channel_id", "")), str(rec.get("message_id", "")),
                     chash, rec.get("raw_text", ""), rec.get("sent_at_utc", ""),
                     rec.get("edited_at_utc", ""), _utc_now(), mx + 1, batch_id))
                inserted += 1

            if _is_signal_record(rec):
                lo, hi = _split_entry(rec.get("entry", ""))
                sid = _signal_id(key, 0)
                cur = conn.execute(
                    "INSERT OR IGNORE INTO signals(signal_id, source_message_key, "
                    "source_signal_index, provider, asset, asset_class, direction, entry_low, "
                    "entry_high, stop, tp1, tp2, tp3, classification, parser_version, "
                    "sent_at_utc, created_at_utc) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (sid, key, 0, rec.get("sender", ""), (rec.get("asset", "") or "").upper(),
                     "", (rec.get("direction", "") or "").upper(), lo, hi, rec.get("stop", ""),
                     rec.get("tp1", ""), rec.get("tp2", ""), rec.get("tp3", ""),
                     "clean signal", PARSER_VERSION, rec.get("sent_at_utc", ""), _utc_now()))
                sig_inserted += cur.rowcount
                # Capture per-stage timestamps + price context (append-only). Done
                # for new AND existing signals; INSERT OR IGNORE keeps the original.
                _record_timing(conn, sid, rec)

            if _fail_after is not None and n + 1 >= _fail_after:
                raise RuntimeError("INJECTED FAILURE (test hook) mid-import")

        conn.execute(
            "UPDATE import_batches SET completed_at_utc=?, messages_seen=?, "
            "messages_inserted=?, duplicates_skipped=?, status='committed' WHERE batch_id=?",
            (_utc_now(), seen, inserted, dups, batch_id))
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")           # no partial batch — nothing persists
        raise
    return {"batch_id": batch_id, "messages_seen": seen, "messages_inserted": inserted,
            "duplicates_skipped": dups, "signals_inserted": sig_inserted}


# ----------------------------------------------------------------------------
# Reconstruct the ordered message list + detector rows from the DB
# ----------------------------------------------------------------------------
def _latest_messages(conn):
    """Latest version of every message, oldest-first (sent time, then message_id)."""
    rows = conn.execute(
        "SELECT r.* FROM raw_message_versions r "
        "JOIN (SELECT message_key, MAX(version_number) v FROM raw_message_versions "
        "      GROUP BY message_key) m "
        "  ON r.message_key=m.message_key AND r.version_number=m.v").fetchall()
    def sort_key(r):
        try:
            mid = int(r["message_id"])
        except (TypeError, ValueError):
            mid = 0
        return (r["sent_at_utc"] or "", mid)
    return sorted((dict(r) for r in rows), key=sort_key)


def _detector_rows(conn):
    """
    Build the chronological row list the signed-off detector expects, plus a
    parallel list of (message_key, signal_id-or-None). Classification is 'clean
    signal' iff the message has a signal; everything else is commentary (the
    boundary logic re-derives fresh entries from raw text). This faithfully
    reproduces the signed-off run (verified: 0 diffs).
    """
    sig_by_key = {s["source_message_key"]: dict(s)
                  for s in conn.execute("SELECT * FROM signals").fetchall()}
    rows, keys, sigids = [], [], []
    for m in _latest_messages(conn):
        key = m["message_key"]
        s = sig_by_key.get(key)
        if s:
            lo, hi = s["entry_low"] or "", s["entry_high"] or ""
            entry = lo if (lo == hi) else f"{lo}-{hi}"
            rows.append({"Date": s["sent_at_utc"] or "", "Sender": s["provider"] or "",
                         "Asset": s["asset"] or "", "Direction": s["direction"] or "",
                         "Entry": entry, "Stop": s["stop"] or "", "TP1": s["tp1"] or "",
                         "TP2": s["tp2"] or "", "TP3": s["tp3"] or "",
                         "Classification": "clean signal", "Confidence": "",
                         "DetectedOutcome": "", "OutcomeEvidence": "",
                         "RawMessage": m["raw_text"]})
            sigids.append(s["signal_id"])
        else:
            rows.append({"Date": m["sent_at_utc"] or "", "Sender": "", "Asset": "",
                         "Direction": "", "Entry": "", "Stop": "", "TP1": "", "TP2": "",
                         "TP3": "", "Classification": "commentary", "Confidence": "",
                         "DetectedOutcome": "", "OutcomeEvidence": "", "RawMessage": m["raw_text"]})
            sigids.append(None)
        keys.append(key)
    return rows, keys, sigids


# ----------------------------------------------------------------------------
# Evidence collection — mirrors assign_detected_outcomes' windowing exactly, but
# also emits the REJECTED evidence (post-boundary / wrong-asset) so nothing is
# silently ignored. The re-entry boundary is preserved verbatim.
# ----------------------------------------------------------------------------
def _evidence_for_signals(rows, keys):
    """
    Returns {row_index: {accepted:[(key,event,text)], rejected:[(key,reason,text)],
                         primary_key, primary_text}} for each clean-signal row.
    """
    import module_b_parser as parser
    L = listener
    meta = []
    for r in rows:
        txt = r.get("RawMessage", "") or ""
        asset = r.get("Asset") or parser._detect_instrument(txt)[0]
        is_entry = (r.get("Classification") == "clean signal") or parser.has_fresh_entry(txt)
        meta.append({"key": L._outcome_asset_key(asset),
                     "msg_key": L._outcome_msg_asset_key(txt),
                     "thread": L._thread_of(txt), "is_entry": is_entry, "text": txt})

    out = {}
    for p, r in enumerate(rows):
        if r.get("Classification") != "clean signal":
            continue
        key = meta[p]["key"]
        entry_thread = meta[p]["thread"]
        end = len(rows)
        for q in range(p + 1, len(rows)):
            if meta[q]["is_entry"] and meta[q]["key"] == key:
                end = q
                break
        candidates, rejected = [], []
        for q in range(p + 1, end):
            if meta[q]["is_entry"]:
                continue
            txt = meta[q]["text"]
            mk = meta[q]["msg_key"]
            if mk:
                if mk != key:
                    if L._detect_event(txt):
                        rejected.append((keys[q], "WRONG_ASSET", txt))
                    continue
            else:
                mt = meta[q]["thread"]
                if entry_thread and mt and mt != entry_thread:
                    if L._detect_event(txt):
                        rejected.append((keys[q], "WRONG_THREAD", txt))
                    continue
            candidates.append((q, txt))
        texts = [t for _, t in candidates]
        truncated = L._truncate_at_reentry(texts)
        cut = len(truncated)
        accepted = []
        for idx, (q, txt) in enumerate(candidates):
            ev = L._detect_event(txt)
            if not ev:
                continue
            if idx < cut:
                accepted.append((keys[q], ev, txt))
            else:
                rejected.append((keys[q], "POST_REENTRY_BOUNDARY", txt))
        # primary = the message the matcher chose as evidence (r['OutcomeEvidence'])
        primary_text = r.get("OutcomeEvidence", "") or ""
        primary_key = None
        for q, txt in candidates:
            if txt == primary_text:
                primary_key = keys[q]
                break
        out[p] = {"accepted": accepted, "rejected": rejected,
                  "primary_key": primary_key, "primary_text": primary_text}
    return out


def _numeric_for_event(text):
    """(numeric_value, unit) for an evidence message — pips if present, else target."""
    pips = listener._evidence_pips(text)
    if pips:
        return float(pips), "pips"
    tgt = listener._evidence_target(text)
    if tgt:
        return float(tgt), "target"
    return None, None


# ----------------------------------------------------------------------------
# R scoring (reuses the signed-off scorer in log_history)
# ----------------------------------------------------------------------------
def _score_r(signal, category, evidence_text):
    """Return (calculated_r: Decimal|None, r_is_known: bool, label)."""
    import log_history as lh
    import module_c_risk as risk
    lo, hi = signal["entry_low"] or "", signal["entry_high"] or ""
    entry = lo if (lo == hi) else f"{lo}-{hi}"
    row = {"Asset": signal["asset"], "Direction": signal["direction"], "Entry": entry,
           "Stop": signal["stop"], "TP1": signal["tp1"], "TP2": signal["tp2"],
           "TP3": signal["tp3"], "RawMessage": "", "Sender": signal.get("provider", ""),
           "OutcomeEvidence": evidence_text or ""}
    sig, why = lh.build_signal(row)
    if sig is None:
        return None, False, f"unsizable ({why})"
    try:
        ticket = risk.size_signal(sig, Decimal(config.POT_SIZE), require_targets=False)
    except Exception as e:                                       # noqa: BLE001
        return None, False, f"unsizable ({e})"
    if category in _WIN_CATS:
        rr, lbl = lh._resolve_win_rr(sig, ticket, row)
        return rr, ("unknown" not in lbl.lower()), lbl
    if category in _LOSS_CATS:
        rr, lbl = lh._resolve_loss_rr(ticket, row)
        if rr is None:
            return None, False, lbl
        return rr, True, lbl
    if category == listener.OUT_BREAKEVEN:
        return Decimal("0"), True, "breakeven 0R"
    return None, False, "no R for this category"


# ----------------------------------------------------------------------------
# Overrides
# ----------------------------------------------------------------------------
def active_override(conn, signal_id):
    """The CURRENT (latest) override for a signal, or None. Latest row wins; we
    never edit/flip older rows (append-only)."""
    row = conn.execute(
        "SELECT * FROM manual_overrides WHERE signal_id=? AND is_active=1 "
        "ORDER BY created_at_utc DESC, rowid DESC LIMIT 1", (signal_id,)).fetchone()
    return dict(row) if row else None


def add_override(conn, signal_id, override_type, payload, reason, supersedes=None):
    """Append a manual override (never edits an existing one)."""
    oid = str(uuid.uuid4())
    conn.execute("BEGIN")
    try:
        conn.execute(
            "INSERT INTO manual_overrides(override_id, signal_id, override_type, "
            "override_payload, reason, created_at_utc, supersedes_override_id, is_active) "
            "VALUES (?,?,?,?,?,?,?,1)",
            (oid, signal_id, override_type, json.dumps(payload), reason, _utc_now(), supersedes))
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return oid


# ----------------------------------------------------------------------------
# REBUILD PROJECTIONS  (append new evidence; recompute projections; respect overrides)
# ----------------------------------------------------------------------------
def rebuild_projections(conn, detector_version=DETECTOR_VERSION, calc_version=CALC_VERSION):
    """
    Re-derive evidence links (append-only — INSERT OR IGNORE) and recompute every
    signal's projection from current evidence + overrides. Idempotent: re-running
    on an unchanged DB changes nothing. Returns a summary dict.
    """
    rows, keys, sigids = _detector_rows(conn)
    listener.assign_detected_outcomes(rows)               # category + primary evidence
    ev = _evidence_for_signals(rows, keys)
    signals = {s["signal_id"]: dict(s)
               for s in conn.execute("SELECT * FROM signals").fetchall()}

    conn.execute("BEGIN")
    try:
        conflicts = 0
        for p, info in ev.items():
            sid = sigids[p]
            if sid is None:
                continue
            row = rows[p]
            category = row["DetectedOutcome"] or listener.OUT_UNCLEAR

            # --- append evidence (accepted + rejected), append-only/idempotent ---
            for k, event, text in info["accepted"]:
                nv, unit = _numeric_for_event(text)
                conn.execute(
                    "INSERT OR IGNORE INTO outcome_evidence(evidence_id, signal_id, "
                    "evidence_message_key, evidence_type, numeric_value, unit, "
                    "detector_version, accepted, rejection_reason, created_at_utc) "
                    "VALUES (?,?,?,?,?,?,?,1,NULL,?)",
                    (str(uuid.uuid4()), sid, k, event, nv, unit, detector_version, _utc_now()))
            for k, reason, text in info["rejected"]:
                nv, unit = _numeric_for_event(text)
                conn.execute(
                    "INSERT OR IGNORE INTO outcome_evidence(evidence_id, signal_id, "
                    "evidence_message_key, evidence_type, numeric_value, unit, "
                    "detector_version, accepted, rejection_reason, created_at_utc) "
                    "VALUES (?,?,?,?,?,?,?,0,?,?)",
                    (str(uuid.uuid4()), sid, k, (listener._detect_event(text) or "none"),
                     nv, unit, detector_version, reason, _utc_now()))

            # --- compute the automatic projection ---
            r_val, r_known, _lbl = _score_r(signals[sid], category, info["primary_text"])
            auto = {"category": category, "binary": listener.outcome_group(category),
                    "r": r_val, "r_known": r_known, "primary": info["primary_key"]}

            # --- precedence: active override > computed ---
            ovr = active_override(conn, sid)
            conflict = None
            if ovr:
                payload = json.loads(ovr["override_payload"] or "{}")
                cat = payload.get("outcome_category", auto["category"])
                rr = payload.get("calculated_r", None)
                rk = bool(payload.get("r_is_known", rr is not None))
                if cat != auto["category"]:
                    conflict = f"auto={auto['category']} override={cat}"
                    conflicts += 1
                final = {"category": cat, "binary": listener.outcome_group(cat),
                         "r": (Decimal(str(rr)) if rr is not None else None),
                         "r_known": rk, "primary": payload.get("primary_evidence_message_key",
                                                               auto["primary"]),
                         "source": "override"}
            else:
                final = {"category": auto["category"], "binary": auto["binary"],
                         "r": auto["r"], "r_known": auto["r_known"],
                         "primary": auto["primary"],
                         "source": "evidence" if auto["primary"] else "unknown"}

            conn.execute(
                "INSERT INTO outcome_projections(signal_id, outcome_category, binary_rollup, "
                "calculated_r, r_is_known, primary_evidence_message_key, source, "
                "override_conflict, calculation_version, calculated_at_utc) "
                "VALUES (?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(signal_id) DO UPDATE SET outcome_category=excluded.outcome_category, "
                "binary_rollup=excluded.binary_rollup, calculated_r=excluded.calculated_r, "
                "r_is_known=excluded.r_is_known, "
                "primary_evidence_message_key=excluded.primary_evidence_message_key, "
                "source=excluded.source, override_conflict=excluded.override_conflict, "
                "calculation_version=excluded.calculation_version, "
                "calculated_at_utc=excluded.calculated_at_utc",
                (sid, final["category"], final["binary"],
                 (str(final["r"]) if final["r"] is not None else None),
                 1 if final["r_known"] else 0, final["primary"], final["source"],
                 conflict, calc_version, _utc_now()))
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return {"signals": len(signals), "override_conflicts": conflicts}


# ----------------------------------------------------------------------------
# EXPORT CSV  (export only — never the source of truth)
# ----------------------------------------------------------------------------
EXPORT_COLUMNS = ["signal_id", "sent_at_utc", "source_message_key", "asset", "direction",
                  "entry_low", "entry_high", "stop", "tp1", "tp2", "tp3",
                  "outcome_category", "binary_rollup", "calculated_r", "r_is_known",
                  "primary_evidence_message_key", "source", "override_conflict"]


def export_csv(conn, path=EXPORT_CSV):
    """Deterministic per-signal export (ordered by sent time, then key)."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    q = ("SELECT s.signal_id, s.sent_at_utc, s.source_message_key, s.asset, s.direction, "
         "s.entry_low, s.entry_high, s.stop, s.tp1, s.tp2, s.tp3, "
         "p.outcome_category, p.binary_rollup, p.calculated_r, p.r_is_known, "
         "p.primary_evidence_message_key, p.source, p.override_conflict "
         "FROM signals s LEFT JOIN outcome_projections p ON s.signal_id=p.signal_id "
         "ORDER BY s.sent_at_utc, s.source_message_key, s.source_signal_index")
    rows = conn.execute(q).fetchall()
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=EXPORT_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r[k] is None else r[k]) for k in EXPORT_COLUMNS})
    return path


# ----------------------------------------------------------------------------
# Distribution / baseline metrics
# ----------------------------------------------------------------------------
def get_timing(conn, signal_id):
    """The captured timing row for a signal (dict), or None."""
    row = conn.execute("SELECT * FROM signal_timing WHERE signal_id=?", (signal_id,)).fetchone()
    return dict(row) if row else None


def timing_summary(conn):
    """Coverage + delay stats over signal_timing (no shadow calculation)."""
    n_sig = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
    n_tim = conn.execute("SELECT COUNT(*) FROM signal_timing").fetchone()[0]
    rp = conn.execute("SELECT AVG(received_minus_posted_sec), COUNT(received_minus_posted_sec) "
                      "FROM signal_timing").fetchone()
    pr = conn.execute("SELECT AVG(parsed_minus_received_sec), COUNT(parsed_minus_received_sec) "
                      "FROM signal_timing").fetchone()
    return {"signals": n_sig, "timing_rows": n_tim,
            "received_minus_posted_avg": rp[0], "received_minus_posted_n": rp[1],
            "parsed_minus_received_avg": pr[0], "parsed_minus_received_n": pr[1]}


def distribution(conn):
    """Per-category counts, coarse roll-up, and the gold known-R average."""
    rows = conn.execute(
        "SELECT s.asset, p.outcome_category, p.binary_rollup, p.calculated_r, p.r_is_known "
        "FROM signals s JOIN outcome_projections p ON s.signal_id=p.signal_id").fetchall()
    cats, roll = {}, {}
    gold_r = []
    for r in rows:
        cats[r["outcome_category"]] = cats.get(r["outcome_category"], 0) + 1
        roll[r["binary_rollup"]] = roll.get(r["binary_rollup"], 0) + 1
        if (r["asset"] or "").upper().startswith("XAU") and r["r_is_known"] and r["calculated_r"] is not None:
            gold_r.append(Decimal(str(r["calculated_r"])))
    avg_gold = (sum(gold_r) / len(gold_r)) if gold_r else Decimal("0")
    return {"categories": cats, "rollup": roll, "total": len(rows),
            "gold_known_r_n": len(gold_r), "gold_avg_r": float(avg_gold)}


# ----------------------------------------------------------------------------
# Backup / integrity / status
# ----------------------------------------------------------------------------
def backup(db_path=DB_PATH, dest_dir=BACKUP_DIR):
    """Checkpoint WAL and copy the DB file to a timestamped backup (read-only copy)."""
    os.makedirs(dest_dir, exist_ok=True)
    conn = connect(db_path)
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        conn.close()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = os.path.join(dest_dir, f"signal_archive_{stamp}.db")
    # sqlite backup API => a consistent copy
    src = sqlite3.connect(db_path)
    dst = sqlite3.connect(dest)
    with dst:
        src.backup(dst)
    src.close()
    dst.close()
    return dest


def integrity_check(conn):
    """PRAGMA integrity + FK check + Phase-1 invariants. Returns (ok, [problems])."""
    problems = []
    ic = conn.execute("PRAGMA integrity_check").fetchone()[0]
    if ic != "ok":
        problems.append(f"integrity_check: {ic}")
    fk = conn.execute("PRAGMA foreign_key_check").fetchall()
    if fk:
        problems.append(f"foreign_key_check: {len(fk)} violation(s)")
    sv = conn.execute("SELECT schema_version FROM schema_meta WHERE id=1").fetchone()
    if not sv or sv[0] != SCHEMA_VERSION:
        problems.append("schema_meta version mismatch")
    # every signal should have a projection (after a rebuild)
    miss = conn.execute(
        "SELECT COUNT(*) FROM signals s LEFT JOIN outcome_projections p "
        "ON s.signal_id=p.signal_id WHERE p.signal_id IS NULL").fetchone()[0]
    if miss:
        problems.append(f"{miss} signal(s) without a projection (run rebuild-projections)")
    # raw_message_versions must never duplicate (key, hash)
    dup = conn.execute(
        "SELECT COUNT(*) FROM (SELECT message_key, content_hash, COUNT(*) c "
        "FROM raw_message_versions GROUP BY message_key, content_hash HAVING c>1)").fetchone()[0]
    if dup:
        problems.append(f"{dup} duplicate raw (key,hash) rows")
    # every signal should have its (append-only) timing capture row
    miss_t = conn.execute(
        "SELECT COUNT(*) FROM signals s LEFT JOIN signal_timing t "
        "ON s.signal_id=t.signal_id WHERE t.signal_id IS NULL").fetchone()[0]
    if miss_t:
        problems.append(f"{miss_t} signal(s) without a signal_timing row")
    return (not problems), problems


def archive_status(conn):
    """Human-readable snapshot of the archive."""
    def one(q):
        return conn.execute(q).fetchone()[0]
    print("=" * 64)
    print("  SIGNAL ARCHIVE — STATUS  (SQLite source of truth, PAPER mode)")
    print("=" * 64)
    print(f"  DB file            : {os.path.abspath(DB_PATH)}")
    print(f"  Schema version     : {one('SELECT schema_version FROM schema_meta WHERE id=1')}")
    print(f"  Import batches     : {one('SELECT COUNT(*) FROM import_batches')}")
    print(f"  Distinct messages  : {one('SELECT COUNT(DISTINCT message_key) FROM raw_message_versions')}")
    print(f"  Message versions   : {one('SELECT COUNT(*) FROM raw_message_versions')}")
    print(f"  Signals            : {one('SELECT COUNT(*) FROM signals')}")
    print(f"  Evidence (accepted): {one('SELECT COUNT(*) FROM outcome_evidence WHERE accepted=1')}")
    print(f"  Evidence (rejected): {one('SELECT COUNT(*) FROM outcome_evidence WHERE accepted=0')}")
    print(f"  Projections        : {one('SELECT COUNT(*) FROM outcome_projections')}")
    print(f"  Active overrides   : {one('SELECT COUNT(*) FROM manual_overrides WHERE is_active=1')}")
    ts = timing_summary(conn)
    print(f"  Signal timing rows : {ts['timing_rows']} / {ts['signals']} signals")
    if ts["parsed_minus_received_n"]:
        print(f"    parse delay avg  : {ts['parsed_minus_received_avg']:.4f}s "
              f"(n={ts['parsed_minus_received_n']})")
    if ts["received_minus_posted_n"]:
        print(f"    capture lag avg  : {ts['received_minus_posted_avg']:.1f}s "
              f"(n={ts['received_minus_posted_n']}; = message age for back-fills)")
    print("    (timing/price are GROUNDWORK for shadow mode — no shadow result computed)")
    d = distribution(conn)
    if d["total"]:
        print("  " + "-" * 60)
        order = [listener.OUT_TARGET_HIT, listener.OUT_MANAGED_PROFIT,
                 listener.OUT_PROFIT_RUNKNOWN, listener.OUT_MANUAL_LOSS,
                 listener.OUT_STOP_LOSS, listener.OUT_BREAKEVEN, listener.OUT_MISSED,
                 listener.OUT_UNCLEAR]
        for k in order:
            if d["categories"].get(k):
                print(f"  {k:<28} {d['categories'][k]}")
        rl = d["rollup"]
        print(f"  Roll-up: {rl.get('win',0)} win / {rl.get('loss',0)} loss / "
              f"{rl.get('breakeven',0)} breakeven / {rl.get('missed',0)} missed / "
              f"{rl.get('unclear',0)} unclear")
        print(f"  Gold known-R avg: {d['gold_avg_r']:.4f}R  (n={d['gold_known_r_n']})")
    conflicts = one("SELECT COUNT(*) FROM outcome_projections WHERE override_conflict IS NOT NULL")
    if conflicts:
        print(f"  ** {conflicts} projection(s) CONFLICT with an active override (override wins).")
    print("=" * 64)


# ----------------------------------------------------------------------------
# Logical DB hash (stable regardless of WAL/file layout)
# ----------------------------------------------------------------------------
def db_logical_hash(conn):
    """A content hash over signals + projections — stable across WAL/file noise."""
    parts = []
    for s in conn.execute("SELECT * FROM signals ORDER BY signal_id").fetchall():
        parts.append("|".join(str(s[k]) for k in s.keys()))
    for p in conn.execute("SELECT signal_id, outcome_category, binary_rollup, calculated_r, "
                          "r_is_known FROM outcome_projections ORDER BY signal_id").fetchall():
        parts.append("|".join(str(p[k]) for k in p.keys()))
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _file_hash(path):
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ----------------------------------------------------------------------------
# BASELINE  (build the signed-off baseline + manifest + verify)
# ----------------------------------------------------------------------------
def build_baseline(db_path=DB_PATH, csv_path=BASELINE_CSV, test_count=None):
    """Import the signed-off sample, rebuild, export, verify, and snapshot a manifest."""
    if os.path.exists(db_path):
        # start the baseline from a clean DB (this is the one-time seed)
        for suffix in ("", "-wal", "-shm"):
            p = db_path + suffix
            if os.path.exists(p):
                os.remove(p)
    conn = connect(db_path)
    records = _records_from_csv(csv_path)
    summary = import_messages(conn, records)
    rebuild_projections(conn)

    # add manual_overrides ONLY where the signed-off audit differs from the auto result
    overrides = _reconcile_overrides(conn, csv_path)
    if overrides:
        rebuild_projections(conn)

    out = export_csv(conn)
    d = distribution(conn)

    ok_dist = (d["rollup"].get("win", 0) == 24 and d["rollup"].get("loss", 0) == 3
               and d["rollup"].get("breakeven", 0) == 1 and d["total"] == 28)
    ok_r = abs(d["gold_avg_r"] - 0.33) <= 0.05
    verified = ok_dist and ok_r

    manifest = {
        "kind": "baseline_snapshot",
        "created_at_utc": _utc_now(),
        "signal_count": d["total"],
        "distribution": d["categories"],
        "rollup": d["rollup"],
        "gold_known_r_avg": round(d["gold_avg_r"], 4),
        "gold_known_r_n": d["gold_known_r_n"],
        "source_csv": os.path.basename(csv_path),
        "source_csv_sha256": _file_hash(csv_path),
        "export_csv_sha256": _file_hash(out),
        "db_logical_hash": db_logical_hash(conn),
        "schema_version": SCHEMA_VERSION,
        "code_version": CODE_VERSION,
        "detector_version": DETECTOR_VERSION,
        "calculation_version": CALC_VERSION,
        "parser_version": PARSER_VERSION,
        "manual_overrides": overrides,
        "test_count": test_count,
        "verified_reproduces_signoff": verified,
        "verify_distribution_ok": ok_dist,
        "verify_gold_r_ok": ok_r,
        "import_summary": summary,
    }
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    mpath = os.path.join(SNAPSHOT_DIR, f"baseline_{stamp}.json")
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    conn.close()
    return manifest, mpath


def _reconcile_overrides(conn, csv_path):
    """
    Add a manual override anywhere the signed-off CSV's DetectedOutcome differs
    from the archive's automatic projection. (For the current signed-off sample
    this is expected to be empty — the archive reproduces the detector exactly.)
    """
    signed = {}
    with open(csv_path, encoding="utf-8") as f:
        for i, r in enumerate(csv.DictReader(f)):
            if r.get("Classification") == "clean signal":
                key = _message_key("baseline", i)
                signed[_signal_id(key, 0)] = r.get("DetectedOutcome", "")
    added = []
    for sid, signed_cat in signed.items():
        proj = conn.execute("SELECT outcome_category FROM outcome_projections WHERE signal_id=?",
                            (sid,)).fetchone()
        if proj and signed_cat and proj["outcome_category"] != signed_cat:
            payload = {"outcome_category": signed_cat}
            add_override(conn, sid, "outcome_category", payload,
                         reason="signed-off audit differs from automatic detector result")
            added.append({"signal_id": sid, "to": signed_cat,
                          "from": proj["outcome_category"]})
    return added


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
def _cmd_import(args):
    csv_path = _opt(args, "--csv")
    conn = connect()
    if csv_path:
        records = _records_from_csv(csv_path)
        print(f"  Importing {len(records)} message(s) from {csv_path} ...")
    else:
        limit = _opt(args, "--limit")
        sender = _opt(args, "--sender")
        backfill = "--backfill" in args
        print("  Pulling from Telegram (read-only) ..."
              + ("  [back-fill: stage times left blank -> posted-only T-C]" if backfill else ""))
        records = listener.pull_for_archive(limit=int(limit) if limit else None,
                                            sender_filter=sender, backfill=backfill)
        if not records:
            print("  No messages pulled (no Telethon/credentials/channel, or empty). Nothing imported.")
            conn.close()
            return
    summary = import_messages(conn, records)
    rebuild_projections(conn)
    print(f"  Imported: {summary['messages_inserted']} new message(s), "
          f"{summary['duplicates_skipped']} duplicate(s) skipped, "
          f"{summary['signals_inserted']} new signal(s).")
    archive_status(conn)
    conn.close()


def _cmd_rebuild(args):
    conn = connect()
    s = rebuild_projections(conn)
    print(f"  Rebuilt projections for {s['signals']} signal(s); "
          f"{s['override_conflicts']} override conflict(s).")
    conn.close()


def _cmd_export(args):
    conn = connect()
    out = export_csv(conn, _opt(args, "--out") or EXPORT_CSV)
    print(f"  Exported {os.path.abspath(out)}")
    conn.close()


def _cmd_backup(args):
    dest = backup()
    print(f"  Backup written: {os.path.abspath(dest)}")


def _cmd_integrity(args):
    conn = connect()
    ok, problems = integrity_check(conn)
    if ok:
        print("  integrity-check: OK")
    else:
        print("  integrity-check: PROBLEMS")
        for p in problems:
            print(f"    - {p}")
    conn.close()
    sys.exit(0 if ok else 1)


def _cmd_status(args):
    conn = connect()
    archive_status(conn)
    conn.close()


def _cmd_baseline(args):
    manifest, mpath = build_baseline()
    print(f"  Baseline built. Manifest: {os.path.abspath(mpath)}")
    print(f"  Signals: {manifest['signal_count']}   "
          f"Roll-up: {manifest['rollup'].get('win',0)} win / "
          f"{manifest['rollup'].get('loss',0)} loss / "
          f"{manifest['rollup'].get('breakeven',0)} breakeven")
    print(f"  Gold known-R avg: {manifest['gold_known_r_avg']}R "
          f"(n={manifest['gold_known_r_n']})")
    print(f"  Manual overrides added: {len(manifest['manual_overrides'])}")
    print(f"  VERIFIED reproduces signed-off baseline: {manifest['verified_reproduces_signoff']}")
    sys.exit(0 if manifest["verified_reproduces_signoff"] else 1)


def _opt(args, name):
    if name in args:
        i = args.index(name)
        if i + 1 < len(args):
            return args[i + 1]
    return None


_COMMANDS = {
    "import": _cmd_import, "rebuild-projections": _cmd_rebuild, "export-csv": _cmd_export,
    "backup": _cmd_backup, "integrity-check": _cmd_integrity, "archive-status": _cmd_status,
    "baseline": _cmd_baseline,
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return
    cmd = argv[0]
    fn = _COMMANDS.get(cmd)
    if not fn:
        print(f"  Unknown command: {cmd}\n")
        print(__doc__)
        sys.exit(2)
    fn(argv[1:])


if __name__ == "__main__":
    main()
