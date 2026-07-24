"""Additive evidence layer — shared schema, hashing, UNKNOWN handling, chronological firewall.

CAPTURE / RESEARCH ONLY. No broker/demo/execution surface. Every record is append-only and
carries provenance timestamps + a logical hash. Nothing here can mutate a frozen follower
outcome, the constitution, scorers, gates or pre-marks (guard-enforced at write time).

The CHRONOLOGICAL FIREWALL is the core discipline: PRE_TRADE_SNAPSHOT and BLIND_HYPOTHESIS
must be committed while the firewall is OPEN for a campaign — i.e. before ANY outcome,
result-claim, or retrospective-video record exists for it. `assert_firewall_open` enforces this.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
for p in (HERE, PARENT):
    if p not in sys.path:
        sys.path.insert(0, p)
import guards                                                      # noqa: E402

SCHEMA_VERSION = "evidence_layer_v0_1"
UNKNOWN = "UNKNOWN"                       # explicit fail-closed sentinel (never null-guessed)

EVIDENCE_DIR = HERE
PRE_TRADE_LEDGER = os.path.join(HERE, "pre_trade_snapshots_v0_1.jsonl")
BLIND_HYP_LEDGER = os.path.join(HERE, "blind_hypotheses_v0_1.jsonl")
MGMT_LEDGER = os.path.join(HERE, "management_snapshots_v0_1.jsonl")
COVERAGE_LEDGER = os.path.join(HERE, "stream_coverage_v0_1.jsonl")
SECONDFEED_LEDGER = os.path.join(HERE, "second_feed_divergence_v0_1.jsonl")
BTC_LEDGER = os.path.join(HERE, "btc_capture_v0_1.jsonl")
SOL_LEDGER = os.path.join(HERE, "sol_capture_v0_1.jsonl")

FORWARD_LEDGER = os.path.join(PARENT, "..", "forward_validation_ledger_v0_2.jsonl")

# record types / markers that CLOSE the firewall for a campaign (genuine outcome/hindsight).
# NOTE: a live TRACKER_SNAPSHOT is real-time tracking, NOT hindsight -> it must NOT close it.
FIREWALL_CLOSING_TOKENS = ("outcome", "result_claim", "retrospective", "video", "final_close",
                           "adjudicat", "expectancy", "partial_match")

STAMP = {"review_only": True, "executable": False, "trade_ready": False, "observation_only": True}


class FirewallViolation(Exception):
    pass


def logical_hash(record: dict) -> str:
    core = {k: v for k, v in record.items()
            if k not in ("logical_hash", "evidence_commit_ts", "provenance")}
    return hashlib.sha256(json.dumps(core, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def stamp(record: dict) -> dict:
    record.update(STAMP)
    record["schema_version"] = SCHEMA_VERSION
    return record


def finalize(record: dict) -> dict:
    """Stamp, hash, guard. Never mutates a frozen outcome — these are NEW records only."""
    stamp(record)
    record["logical_hash"] = logical_hash(record)
    guards.assert_clean(record, record.get("record_type", "evidence"))
    return record


def append_once(ledger_path: str, record: dict) -> bool:
    return guards.append_once(ledger_path, record)


def _scan_ledgers_for_campaign(setup_id: str, extra_paths=()):
    hits = []
    for path in (FORWARD_LEDGER, PRE_TRADE_LEDGER, BLIND_HYP_LEDGER, MGMT_LEDGER, *extra_paths):
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if setup_id and setup_id in line:
                    try:
                        hits.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return hits


def firewall_state(setup_id: str) -> str:
    """OPEN until any outcome/hindsight record for this campaign exists, else CLOSED."""
    for rec in _scan_ledgers_for_campaign(setup_id):
        blob = json.dumps(rec, default=str).lower()
        rt = str(rec.get("record_type", "")).lower()
        # a PARTIAL_MATCH / adjudication / result / video record closes the firewall
        if any(tok in rt for tok in FIREWALL_CLOSING_TOKENS):
            return "CLOSED"
        # a management_timing_8c with FINAL_CLOSE or a result claim also closes it
        if "final_close" in blob or "trade closed" in blob or "retrospective_commentary" in blob:
            return "CLOSED"
    return "OPEN"


def assert_firewall_open(setup_id: str, what: str):
    st = firewall_state(setup_id)
    if st != "OPEN":
        raise FirewallViolation(
            f"cannot commit {what} for {setup_id}: chronological firewall is {st} "
            "(outcome/hindsight already recorded — blind evidence must precede it)")
    return st
