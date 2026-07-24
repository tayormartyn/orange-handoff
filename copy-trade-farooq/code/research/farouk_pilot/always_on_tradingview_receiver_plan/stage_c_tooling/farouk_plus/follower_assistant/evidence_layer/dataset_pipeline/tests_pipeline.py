"""Pipeline tests — fixtures A-E (RESEARCH-ONLY). Sandboxes the outcome ledger to a temp path; never
writes the real ledgers. Proves immutability, idempotency, intrabar fail-closed, forbidden classes,
future-data guard, and dataset reproducibility/tamper-sensitivity.
"""
from __future__ import annotations

import copy
import io
import json
import os
import sys
import tempfile
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
EVDIR = os.path.dirname(HERE)
FA = os.path.dirname(EVDIR)
for p in (HERE, EVDIR, FA):
    if p not in sys.path:
        sys.path.insert(0, p)
import strategy_router as R                                       # noqa: E402
import outcome_pipeline as OP                                    # noqa: E402
import dataset_generator as DG                                   # noqa: E402

PASS = 0
FAIL = 0


def ok(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {name}")


def bar(ts, o, h, l, c):
    return (ts, D(str(o)), D(str(h)), D(str(l)), D(str(c)))


DEC = 1_000_000                          # decision epoch (1m boundary)


def make_freeze(rclass="PROSPECTIVE", direction="LONG", zone=("4007", "4019"), sl="3985"):
    # causal bars strictly before decision (close <= DEC)
    pre = [bar(DEC - (60 - i) * 60, 4011, 4013, 4009, 4011) for i in range(60)]
    return R.freeze_router(setup_id="XAU-FTEST", direction=direction, zone_low=zone[0], zone_high=zone[1],
                           sl=sl, decision_ts=DEC, bars=pre, record_class=rclass,
                           raw_source_ref={"pretrade_logical_hash": "abc", "source_message_utc": "2026-01-01T00:00:00Z"},
                           activation_ts=DEC - 100)


# ---- Fixture A — clean complete outcome -------------------------------------------------------
def fixture_a(tmp):
    fz = make_freeze()
    fz_hash_before = fz["logical_hash"]
    fz_copy = copy.deepcopy(fz)
    # post-decision bars: activate the zone (touch 4007-4019), run UP to target 4050; stop 3985 never hit
    post = [bar(DEC + i * 60, 4015, 4016, 4008, 4015) for i in range(3)]          # activation
    post += [bar(DEC + (3 + i) * 60, 4020 + i, 4055, 4019, 4050) for i in range(5)]  # runs to target in later bars
    bars = post
    ledger = os.path.join(tmp, "out.jsonl")
    rec = OP.attach_outcome(fz, bars, observation_cutoff=DEC + 10000, target=4050, ledger_path=ledger)
    ok("A: freeze immutable (hash unchanged)", fz["logical_hash"] == fz_hash_before and fz == fz_copy)
    ok("A: exactly one outcome record", sum(1 for _ in open(ledger)) == 1)
    ok("A: outcome COMPLETE", rec["labels"]["outcome_status"] == "COMPLETE")
    ok("A: activated", rec["labels"]["activation_result"] == "ACTIVATED")
    ok("A: target-first (stop never hit)", rec["labels"]["target_first"] is True and rec["labels"]["stop_first"] is None)
    ok("A: deterministic MFE present", rec["labels"]["mfe_pips"] is not None)
    # dataset row reproducible
    fl = os.path.join(tmp, "freeze.jsonl")
    open(fl, "w", encoding="utf-8").write(json.dumps(fz, default=str) + "\n")
    r1 = DG.generate([fl], ledger, out_dir=os.path.join(tmp, "d1"), now_ts=1)
    r2 = DG.generate([fl], ledger, out_dir=os.path.join(tmp, "d2"), now_ts=999)
    ok("A: dataset hash reproducible across gen-timestamps", r1["dataset_hash"] == r2["dataset_hash"])
    ok("A: dataset row present", r1["manifest"]["row_count"] == 1)
    return fz, ledger, fl


# ---- Fixture B — same-bar ambiguity -----------------------------------------------------------
def fixture_b(tmp):
    fz = make_freeze()
    # one bar AFTER activation spans BOTH stop(3985) and target(4050) -> ambiguous
    post = [bar(DEC + 60, 4015, 4016, 4010, 4015),                                # activation
            bar(DEC + 120, 4015, 4055, 3980, 4000)]                              # spans 3985 and 4050
    ledger = os.path.join(tmp, "outB.jsonl")
    rec = OP.attach_outcome(fz, post, observation_cutoff=DEC + 10000, target=4050, ledger_path=ledger)
    ok("B: AMBIGUOUS_INTRABAR_ORDER", rec["labels"]["outcome_status"] == "AMBIGUOUS_INTRABAR_ORDER")
    ok("B: no optimistic ordering chosen", rec["labels"]["stop_first"] is None and rec["labels"]["target_first"] is None)
    ok("B: definitive training label withheld", rec["labels"]["definitive_training_label_withheld"] is True)
    ok("B: alternatives recorded", rec["labels"]["intrabar_alternatives"]["ordering_unknown"] is True)
    ok("B: not training-eligible (ambiguous)", rec["eligibility"]["eligible_for_training"] is False)


# ---- Fixture C — duplicate / restart ----------------------------------------------------------
def fixture_c(tmp):
    fz = make_freeze()
    post = [bar(DEC + 60, 4015, 4016, 4010, 4015), bar(DEC + 120, 4020, 4055, 4019, 4050)]
    ledger = os.path.join(tmp, "outC.jsonl")
    r1 = OP.attach_outcome(fz, post, observation_cutoff=DEC + 10000, target=4050, ledger_path=ledger)
    r2 = OP.attach_outcome(fz, post, observation_cutoff=DEC + 10000, target=4050, ledger_path=ledger)   # duplicate
    ok("C: duplicate attach -> no second record", sum(1 for _ in open(ledger)) == 1)
    ok("C: idempotent returns same record", r1["idempotency_key"] == r2["idempotency_key"])
    # restart/reprocess: fresh call, same durable ledger -> still one
    OP.attach_outcome(fz, post, observation_cutoff=DEC + 10000, target=4050, ledger_path=ledger)
    ok("C: restart reprocess -> still one record", sum(1 for _ in open(ledger)) == 1)


# ---- Fixture D — forbidden record classes -----------------------------------------------------
def fixture_d(tmp):
    post = [bar(DEC + 60, 4015, 4016, 4010, 4015), bar(DEC + 120, 4020, 4055, 4019, 4050)]
    for rclass in ("SCHEMA_BACKFILL_NOT_PROSPECTIVE", "SYNTHETIC_INTEGRATION_TEST",
                   "TECHNICAL_FIXTURE_NOT_EDGE_EVIDENCE", "ACTIVATION_STRADDLE"):
        fz = make_freeze(rclass=rclass)
        ledger = os.path.join(tmp, f"outD_{rclass}.jsonl")
        rec = OP.attach_outcome(fz, post, observation_cutoff=DEC + 10000, target=4050, ledger_path=ledger)
        ok(f"D: {rclass} NOT training-eligible", rec["eligibility"]["eligible_for_training"] is False)
        ok(f"D: {rclass} exclusion reason present", len(rec["eligibility"]["exclusion_reasons"]) >= 1)


# ---- Fixture E — future-data attack -----------------------------------------------------------
def fixture_e(tmp):
    fz, ledger, fl = fixture_a(tmp)
    res = DG.generate([fl], ledger, out_dir=os.path.join(tmp, "dE"), now_ts=1)
    feat = res["feature_rows"][0]
    full = res["rows"][0]
    # the feature export must EXCLUDE every POST_DECISION_LABEL field (labels observed after decision)
    label_fields = DG.LABEL_FIELDS
    ok("E: feature export excludes ALL post-decision labels", all(k not in feat for k in label_fields))
    ok("E: mfe/mae (labels) NOT in feature export", "mfe_pips" not in feat and "mae_pips" not in feat)
    ok("E: outcome_status (label) NOT in feature export", "outcome_status" not in feat)
    # a post-decision price (e.g. the 4055 target-run high) must not appear anywhere in the feature row
    blob = json.dumps(feat, default=str)
    ok("E: post-decision price 4055 absent from feature export", "4055" not in blob)
    ok("E: decision-time feature fields ARE present", "session" in feat and "direction" in feat)


# ---- extra: dataset tamper-sensitivity --------------------------------------------------------
def test_dataset_tamper(tmp):
    fz, ledger, fl = fixture_a(tmp)
    base = DG.generate([fl], ledger, out_dir=os.path.join(tmp, "t0"), now_ts=1)["dataset_hash"]
    # tamper: flip a label in the outcome ledger -> dataset hash must change
    lines = open(ledger, encoding="utf-8").read().replace("COMPLETE", "PENDING")
    led2 = os.path.join(tmp, "tampered.jsonl"); open(led2, "w", encoding="utf-8").write(lines)
    t = DG.generate([fl], led2, out_dir=os.path.join(tmp, "t1"), now_ts=1)["dataset_hash"]
    ok("TAMPER: altering an outcome label changes the dataset hash", base != t)


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    tmp = tempfile.mkdtemp(prefix="pipe_")
    fixture_a(tmp); fixture_b(tmp); fixture_c(tmp); fixture_d(tmp); fixture_e(tmp); test_dataset_tamper(tmp)
    print(f"\n{PASS} passed, {FAIL} failed")
    print("TRADINGVIEW_PRICE_SEMANTICS_UNVERIFIED | BROKER_EXECUTION_EQUIVALENCE_UNPROVEN")
    sys.exit(1 if FAIL else 0)
