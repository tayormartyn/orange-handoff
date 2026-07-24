"""Phase 3 — ISOLATED LIFECYCLE INTEGRATION DEMONSTRATION (RESEARCH-ONLY).

Exercises the REAL evidence-watcher lifecycle (source capture -> proposal normalization -> campaign
correlation -> market sync -> blind hypothesis -> automatic router hierarchy -> automatic freeze ->
immutable ledger append) end to end. The freeze is produced by the genuine watcher run_cycle, NOT by
a manual freeze_router call. All records are record_class=SYNTHETIC_INTEGRATION_TEST, written to a
SEPARATE integration-test ledger; the genuine prospective ledger must stay absent/unchanged.
"""
from __future__ import annotations

import io
import json
import os
import sqlite3
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FA = os.path.dirname(HERE)
for p in (HERE, FA):
    if p not in sys.path:
        sys.path.insert(0, p)
import evidence_schema as es                                      # noqa: E402
import evidence_watcher as ew                                     # noqa: E402
import strategy_router as sr                                      # noqa: E402
from market_events import BarStream                               # noqa: E402

PASS = 0
FAIL = 0


def ok(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {name}")


GENUINE_PROSPECTIVE = os.path.join(HERE, "router_freeze_v0_1.jsonl")


def _real_prospective_state():
    # ALWAYS the genuine fixed path (not the possibly-reassigned sr.ROUTER_FREEZE_LEDGER)
    p = GENUINE_PROSPECTIVE
    if not os.path.exists(p):
        return ("ABSENT", 0, None)
    import hashlib
    data = open(p, "rb").read()
    return ("PRESENT", sum(1 for _ in open(p, encoding="utf-8")), hashlib.sha256(data).hexdigest())


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    # capture the GENUINE prospective ledger identity BEFORE (it must not change)
    REAL_PROSPECTIVE = os.path.join(HERE, "router_freeze_v0_1.jsonl")
    before = _real_prospective_state()
    print(f"[before] genuine prospective ledger: {before[0]} lines={before[1]} sha={before[2]}")

    TMP = tempfile.mkdtemp(prefix="router_integ_")
    DB = os.path.join(TMP, "ev.db")
    FWD = os.path.join(TMP, "fwd.jsonl")
    ILOG = os.path.join(TMP, "ingest.jsonl")
    INTEG = os.path.join(HERE, "router_freeze_integration_test_v0_1.jsonl")
    if os.path.exists(INTEG):
        os.remove(INTEG)

    # redirect the whole evidence world to temp (hermetic) — proves no genuine-ledger contamination
    es.PRE_TRADE_LEDGER = ew.snapshots.es.PRE_TRADE_LEDGER = os.path.join(TMP, "pre.jsonl")
    es.BLIND_HYP_LEDGER = os.path.join(TMP, "blind.jsonl")
    es.MGMT_LEDGER = os.path.join(TMP, "mgmt.jsonl")
    es.SECONDFEED_LEDGER = os.path.join(TMP, "sf.jsonl")
    es.COVERAGE_LEDGER = os.path.join(TMP, "cov.jsonl")
    es.FORWARD_LEDGER = FWD
    ew.FWD_LEDGER = FWD
    ew.INGEST_LOG = ILOG
    ew.CURSOR = os.path.join(TMP, "cursor.json")
    ew.EVIDENCE_DB = DB
    # route router freezes to the ISOLATED integration ledger + force the SYNTHETIC class via the seam
    sr.ROUTER_FREEZE_LEDGER = INTEG
    sr.RECORD_CLASS_OVERRIDE = "SYNTHETIC_INTEGRATION_TEST"
    # sandbox the activation marker too (MUST NOT clobber the live watcher's genuine marker)
    _saved_marker = sr.ACTIVATION_MARKER
    sr.ACTIVATION_MARKER = os.path.join(TMP, "activation.json")
    sr.write_activation_marker(pid=-1, activation_ts=1_700_000_000)

    SID = "XAU-F903-INTEG"
    SIG = 1784240000 - (1784240000 % 60)      # 1m boundary
    from datetime import datetime, timezone

    def iso(ts):
        return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # synthetic evidence DB — schema + text format matching the working watcher harness
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE prospective_message_evidence(
      telegram_message_id TEXT, telegram_posted_at_utc TEXT, listener_received_at_utc TEXT,
      raw_text TEXT, raw_text_hash TEXT, message_event_type TEXT, message_revision_number INTEGER,
      telegram_sender_username TEXT)""")
    con.execute("INSERT INTO prospective_message_evidence VALUES(?,?,?,?,?,?,?,?)",
                ("46001", iso(SIG), iso(SIG + 1),
                 "seascalperfarouk Posted in 🪙・gold-trades\n\nXAUUSD BUY 4007-4019 sl 3985",
                 "h" * 64, "CREATED", 1, "seascalperfarouk"))
    con.commit(); con.close()
    # forward ledger: the XAU_F_SETUP the wire would have created
    open(FWD, "w", encoding="utf-8").write(json.dumps({
        "record_type": "XAU_F_SETUP", "setup_id": SID, "message_ids": [46001],
        "timestamp_utc": iso(SIG + 3), "direction": "LONG"}) + "\n")
    # ingestion log: causal 1m market-events strictly before the signal
    with open(ILOG, "w", encoding="utf-8") as fh:
        for i in range(60):
            t = SIG - (60 - i) * 60
            b = {"schema": "market_event_v0_1", "kind": "ACCEPTED", "event_ts": t,
                 "provider": "PEPPERSTONE_TV_BAR_FEED", "revision": 1, "logical_hash": f"h{i}",
                 "bar": {"instrument": "XAUUSD", "provider": "PEPPERSTONE_TV_BAR_FEED",
                         "timeframe": "1m", "event_ts": t, "receive_ts": t + 60,
                         "open": "4021.0", "high": "4022.0", "low": "4020.0", "close": "4021.5",
                         "bid": None, "ask": None, "source_id": "test", "sequence": i, "revision": 1}}
            fh.write(json.dumps(b) + "\n")

    # make F903 analytical + firewall OPEN (no outcome) so the sweep will freeze it
    _orig_analytical = ew.bq.is_analytical
    ew.bq.is_analytical = lambda s: True

    try:
        # === RUN THE REAL LIFECYCLE (no manual freeze_router / no manual ledger write) ===
        acts1 = ew.run_cycle(db_path=DB, now_ts=SIG + 700)
        froze = [a for a in acts1 if a and a.startswith("ROUTER_FREEZE(")]
        ok("automatic freeze occurred through the real lifecycle", len(froze) == 1)
        ok("no manual freeze invocation (came from run_cycle actions)", any("ROUTER_FREEZE" in a for a in acts1))
        recs = [json.loads(l) for l in open(INTEG, encoding="utf-8")] if os.path.exists(INTEG) else []
        ok("exactly one synthetic freeze created", len(recs) == 1)
        if recs:
            r = recs[0]
            ok("record_class = SYNTHETIC_INTEGRATION_TEST", r["record_class"] == "SYNTHETIC_INTEGRATION_TEST")
            ok("not prospective-eligible", r["eligible_for_prospective_evidence"] is False)
            ok("not training-eligible", r["eligible_for_training"] is False)
            ok("not performance-attribution-eligible", r["eligible_for_performance_attribution"] is False)
            env = r["hash_envelope"]
            ok("decision precedes outcome (no outcome at freeze)", env["outcome_data_available_at_freeze"] is False)
            ok("market cutoff <= decision", env["market_data_cutoff_timestamp"] <= env["decision_timestamp"])
            ok("hash envelope complete (10 contracts + gates + lanes)",
               len(env["contract_versions_sha256"]) == 10 and env["gate_snapshot"]["mode"] == "PAPER")
            ok("VP DATA_UNAVAILABLE", r["supplemental_contracts"]["volume_profile"]["status"] == "VOLUME_PROFILE_DATA_UNAVAILABLE")
            ok("replay whitelist = 2 authorised families", env["replay_family_whitelist"] == ["FVG_CONTINUATION_5M", "ASIA_SESSION_FAKEOUT"])
            ok("lanes isolated (A frozen)", env["lane_refs"]["A_FOLLOWER"]["semantics"] == "FROZEN_AND_KNOWN")
            ok("canonical hash reproduces", es.logical_hash(r) == r["logical_hash"])

        # === idempotency: same event again -> no second freeze ===
        ew.run_cycle(db_path=DB, now_ts=SIG + 800)
        recs2 = sum(1 for _ in open(INTEG, encoding="utf-8")) if os.path.exists(INTEG) else 0
        ok("idempotent: repeat event creates no second freeze", recs2 == 1)
        # === restart re-derivation: fresh cursor -> still no duplicate ===
        ew.CURSOR = os.path.join(TMP, "cursor2.json")
        ew.run_cycle(db_path=DB, now_ts=SIG + 900)
        recs3 = sum(1 for _ in open(INTEG, encoding="utf-8")) if os.path.exists(INTEG) else 0
        ok("restart/reprocess creates no duplicate", recs3 == 1)

        after = _real_prospective_state()
        ok("genuine prospective ledger UNCHANGED (isolation)", after == before)
        print(f"[after]  genuine prospective ledger: {after[0]} lines={after[1]} sha={after[2]}")
        print(f"[integ]  test ledger lines={recs3} path={INTEG}")
    finally:
        ew.bq.is_analytical = _orig_analytical
        sr.RECORD_CLASS_OVERRIDE = None
        sr.ACTIVATION_MARKER = _saved_marker

    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
