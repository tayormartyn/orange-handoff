"""Follower Assistant safety guards (deterministic, in-code — Phase 8).

Narrow protections, no frameworks:
  * forbidden execution/broker tokens can never appear as KEYS in emitted artifacts;
  * required review-only stamps present and unaltered;
  * pre-mark ledger immutability (sha256 pinned to the knowledge-register registration value);
  * scorer immutability (v0.2 / v0.3 / v0.4 hashes pinned);
  * gates PAPER/PREVIEW/False/False verified by import;
  * single authoritative ledger writer (exclusive lockfile);
  * secret hygiene: LOCAL_ONLY_* / LOCAL_SECRET_* content never read here, and emitted
    records are scanned for accidental webhook-URL/secret-path substrings.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from contextlib import contextmanager

HERE = os.path.dirname(os.path.abspath(__file__))
FP = os.path.dirname(HERE)                                   # farouk_plus
ST_ROOT = os.path.abspath(os.path.join(FP, "..", "..", "..", "..", ".."))  # signal-terminal

FORBIDDEN_KEY_TOKENS = ("trade_ready", "execut", "order", "lot", "broker", "account",
                        "risk_size", "copy_trade", "nano", "credential", "password",
                        "api_key", "apikey", "access_token", "secret", "position_size",
                        "quantity", "leverage", "margin", "ticket", "submit", "balance")
# quantity-base guard fix v0.1 (2026-07-17): the ratified explicit percentage scale-out
# ("close X% leave Y%") carries its deterministic size base in the EXACT key 'quantity_base'.
# That precise key is admitted ONLY with a supported research-vocabulary value; every other
# key containing the 'quantity' token, and every unsupported/missing/unknown base (original-
# campaign, account, broker, absolute lots, None), remains a GuardViolation — fail-closed.
QUANTITY_BASE_KEY = "quantity_base"
SUPPORTED_QUANTITY_BASES = ("CURRENTLY_REMAINING_OPEN_FILLED_QUANTITY",)
REQUIRED_STAMP = {"review_only": True, "executable": False, "trade_ready": False,
                  "observation_only": True}
# value-level smuggling patterns (red-team finding 13): forbidden identifiers appearing as
# assignments/fields INSIDE string values
FORBIDDEN_VALUE_PATTERNS = ("lot_size", "account_id", "broker_route", "copy_trade",
                            "risk_size", "demo_execute", "submit_order", "order_submission",
                            # spaced variants (red-team finding 5b); banner-safe
                            "lot size", "account id", "broker route", "submit order")
ACK_ENUM = ("REVIEW", "ACKNOWLEDGED", "REJECTED")
SECRET_SUBSTRINGS = ("workers.dev/tv/", "TV_WEBHOOK_SECRET",)

SCORER_HASHES = {
    os.path.join(FP, "detector_v0_3_replay_results.json"):
        "dd1a5a1a7a1be917856176857fdf7d148c8f17bb19c34ca594aa37cc0a24ed88",
    os.path.join(FP, "detector_v0_2_replay_results.json"):
        "f602e2fdbd2819c97123b8fee9fb50b144e7d9ced1eb4156dc840d66e23989db",
    os.path.join(FP, "tools", "detector_v0_4_offline_replay.py"):
        "a2984641e8f4a6c0c9bb6a41801129d3b83980609ab35764adad579521ad3c1d",
}
PRE_MARK_LEDGER = os.path.join(FP, "pre_mark_candidates_v0_1.jsonl")
KNOWLEDGE_REGISTER = os.path.join(FP, "knowledge", "orange_knowledge_register_v1.json")
# ratified Follower Constitution v0.1 — byte-frozen (any change requires re-ratification)
CONSTITUTION_PATH = os.path.join(HERE, "follower_constitution_v0_1.json")
CONSTITUTION_SHA = "7bce618f29d1d44a48bef085d539b05a289393ebe33fe4d304632016777defde"
# the ledger is APPEND-ONLY (full-file hash legitimately grows); what is FROZEN is each
# pre-mark's boundaries/direction/expiry — pinned here from the registered definitions
FROZEN_PRE_MARKS = {
    "PM-F001-SELL-4150-4184": {"zone": "4150-4184", "dir": "SHORT", "expires": "2026-07-17T21:00:00Z"},
    "PM-F002-SUPPLY-4430-4480": {"zone": "4430-4480", "dir": "SHORT", "expires": "2026-07-31T21:00:00Z"},
    "PM-F003-SELL-4250-4260": {"zone": "4250-4260", "dir": "SHORT", "expires": "2026-07-19T21:00:00Z"},
    "PM-F004-DEMAND-3850-3863": {"zone": "3850-3863", "dir": "LONG", "expires": "2026-07-31T21:00:00Z"},
}
REGISTERED_LEDGER_SHA = "E5B3F0D622311348845FB4E46B2E71A5AED3D92FA53D2A4A5791F926279A357A"


class GuardViolation(Exception):
    pass


def _sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def assert_clean(record: dict, where="record"):
    """Key-token guard + stamp guard + secret-substring guard on one emitted artifact."""
    def walk_keys(o):
        if isinstance(o, dict):
            # explicit percentage scale-out instruction: validated as a WHOLE (fail-closed) —
            # a supported quantity_base is REQUIRED and the percentages must reconcile to 100.
            if o.get("instruction_type") in ("EXPLICIT_PERCENTAGE_PARTIAL_CLOSE",
                                             "CLOSE_PERCENTAGE_PARTIAL"):
                if o.get(QUANTITY_BASE_KEY) not in SUPPORTED_QUANTITY_BASES:
                    raise GuardViolation(
                        f"EXPLICIT_PERCENTAGE_PARTIAL_CLOSE with missing/unsupported "
                        f"quantity_base {o.get(QUANTITY_BASE_KEY)!r} ({where})")
                cp, rp = o.get("close_percentage"), o.get("retain_percentage")
                if not (isinstance(cp, int) and isinstance(rp, int)
                        and 0 < cp < 100 and 0 < rp < 100 and cp + rp == 100):
                    raise GuardViolation(
                        f"EXPLICIT_PERCENTAGE_PARTIAL_CLOSE percentages invalid "
                        f"(close={cp!r} retain={rp!r}) ({where})")
            for k, v in o.items():
                if k in REQUIRED_STAMP:
                    # stamp keys are exempt from the token scan ONLY when they carry the safe
                    # value — a nested trade_ready:True is a violation (red-team finding 5)
                    if v != REQUIRED_STAMP[k]:
                        raise GuardViolation(f"unsafe stamp value {k}={v!r} at depth ({where})")
                elif str(k).lower() == QUANTITY_BASE_KEY:
                    # the exact ratified key, admitted ONLY with a supported value; any other
                    # base (original-campaign/account/broker/lots/unknown/None) fails closed
                    if v not in SUPPORTED_QUANTITY_BASES:
                        raise GuardViolation(f"unsupported quantity_base {v!r} ({where})")
                else:
                    lk = str(k).lower()
                    for tok in FORBIDDEN_KEY_TOKENS:
                        if tok in lk:
                            raise GuardViolation(f"forbidden token '{tok}' in key '{k}' ({where})")
                walk_keys(v)
        elif isinstance(o, list):
            for v in o:
                walk_keys(v)
    walk_keys(record)
    for k, want in REQUIRED_STAMP.items():
        if record.get(k) != want:
            raise GuardViolation(f"missing/altered stamp {k} ({where})")
    if "acknowledgement_state" in record and record["acknowledgement_state"] not in ACK_ENUM:
        raise GuardViolation(f"acknowledgement_state outside closed enum ({where})")
    blob = json.dumps(record, ensure_ascii=False, default=str)
    for s in SECRET_SUBSTRINGS:
        if s in blob:
            raise GuardViolation(f"secret-like substring in {where}")
    lb = blob.lower()
    for p in FORBIDDEN_VALUE_PATTERNS:
        if p in lb:
            raise GuardViolation(f"forbidden identifier '{p}' inside a value ({where})")
    return record


def verify_project_invariants():
    """Scorers byte-identical, pre-marks frozen, gates unchanged. Raises on any drift."""
    for path, want in SCORER_HASHES.items():
        got = _sha(path)
        if got != want:
            raise GuardViolation(f"scorer artifact drifted: {os.path.basename(path)} {got[:12]}")
    reg = json.load(open(KNOWLEDGE_REGISTER, encoding="utf-8"))
    pm = reg["F_pre_mark_register_frozen"]
    if pm["ledger_sha256_at_registration"] != REGISTERED_LEDGER_SHA:
        raise GuardViolation("knowledge register's registered pre-mark ledger hash changed")
    have = {d["id"]: d for d in pm["frozen_definitions"]}
    for pid, want in FROZEN_PRE_MARKS.items():
        d = have.get(pid)
        if not d or d["zone"] != want["zone"] or d["dir"] != want["dir"] or d["expires"] != want["expires"]:
            raise GuardViolation(f"frozen pre-mark {pid} boundaries/expiry changed")
    if ST_ROOT not in sys.path:
        sys.path.insert(0, ST_ROOT)
    import config as _cfg
    import ctrader_config as _ccfg
    gates = (_cfg.MODE, _cfg.LISTENER_MODE, bool(_cfg.EXECUTION_ENABLED),
             bool(_ccfg.CTRADER_EXECUTION_ENABLED))
    if gates != ("PAPER", "PREVIEW", False, False):
        raise GuardViolation(f"gates changed: {gates}")
    if _sha(CONSTITUTION_PATH) != CONSTITUTION_SHA:
        raise GuardViolation("Follower Constitution v0.1 file changed — requires re-ratification")
    return {"scorers": "UNCHANGED", "pre_marks": "FROZEN", "gates": "PAPER/PREVIEW/False/False",
            "constitution": "FROZEN_RATIFIED"}


def assert_constitution_frozen():
    """Cheap runtime pin (red-team finding 6): callable every cycle by always-on processes."""
    if _sha(CONSTITUTION_PATH) != CONSTITUTION_SHA:
        raise GuardViolation("Follower Constitution v0.1 bytes changed — refusing to run "
                             "(re-ratification required)")


@contextmanager
def ledger_lock(ledger_path):
    """Exclusive single-writer lock for the authoritative follower ledger."""
    lock = ledger_path + ".lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise GuardViolation("another authoritative ledger writer holds the lock")
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield
    finally:
        os.remove(lock)


def append_once(ledger_path, record: dict):
    """Append-only, idempotent. Duplicate check = EXACT logical_hash equality on parsed
    records, performed INSIDE the writer lock (no TOCTOU) — red-team finding 14.
    A stale .lock from a killed process fails closed; remove it manually after verifying
    no writer is running."""
    assert_clean(record, "ledger record")
    lh = record.get("logical_hash")
    if not lh or len(lh) != 64:
        raise GuardViolation("ledger record requires a full 64-hex logical_hash")
    with ledger_lock(ledger_path):
        if os.path.exists(ledger_path):
            with open(ledger_path, encoding="utf-8") as fh:
                for line in fh:
                    try:
                        if json.loads(line).get("logical_hash") == lh:
                            return False
                    except json.JSONDecodeError:
                        raise GuardViolation("corrupt line in follower ledger — refuse to append")
        with open(ledger_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    return True
