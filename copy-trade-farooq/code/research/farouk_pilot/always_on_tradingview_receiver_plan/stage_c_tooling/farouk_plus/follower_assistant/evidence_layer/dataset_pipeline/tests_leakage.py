"""Leakage red-team — ACTIVELY attempts each contamination and asserts it fails closed (RESEARCH-ONLY).
Sandboxes all ledgers to temp; never touches real ledgers.
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


DEC = 1_000_000


def freeze(rclass="PROSPECTIVE", extra_bars=None):
    pre = [bar(DEC - (60 - i) * 60, 4011, 4013, 4009, 4011) for i in range(60)]
    if extra_bars:
        pre = pre + extra_bars
    return R.freeze_router(setup_id="XAU-FTEST", direction="LONG", zone_low="4007", zone_high="4019",
                           sl="3985", decision_ts=DEC, bars=pre, record_class=rclass,
                           raw_source_ref={"pretrade_logical_hash": "abc", "source_message_utc": "z"},
                           activation_ts=DEC - 100)


POST = [bar(DEC + 60, 4015, 4016, 4010, 4015), bar(DEC + 120, 4020, 4055, 4019, 4050)]


def attack_future_bars_in_features():
    # add a FUTURE bar (open after decision) to the freeze input; it must not change the frozen features
    base = freeze()
    poisoned = freeze(extra_bars=[bar(DEC + 600, 9999, 9999, 9999, 9999)])
    ok("future bar cannot change the frozen features (hash unchanged)", base["logical_hash"] == poisoned["logical_hash"])


def attack_outcome_into_features(tmp):
    fz = freeze()
    led = os.path.join(tmp, "o.jsonl")
    OP.attach_outcome(fz, POST, observation_cutoff=DEC + 10000, target=4050, ledger_path=led)
    fl = os.path.join(tmp, "f.jsonl"); open(fl, "w", encoding="utf-8").write(json.dumps(fz, default=str) + "\n")
    feat = DG.generate([fl], led, out_dir=os.path.join(tmp, "d"), now_ts=1)["feature_rows"][0]
    ok("no POST_DECISION_LABEL enters feature export", all(k not in feat for k in DG.LABEL_FIELDS))
    ok("target price 4055 absent from feature export", "4055" not in json.dumps(feat, default=str))


def attack_outcome_mutates_freeze(tmp):
    fz = freeze()
    before = copy.deepcopy(fz)
    led = os.path.join(tmp, "o2.jsonl")
    OP.attach_outcome(fz, POST, observation_cutoff=DEC + 10000, target=4050, ledger_path=led)
    ok("outcome attachment does NOT mutate the freeze", fz == before)
    ok("outcome ledger is separate from any freeze ledger", "outcome" not in R.ROUTER_FREEZE_LEDGER and led != R.ROUTER_FREEZE_LEDGER)


def attack_outcome_alters_candidates_or_tier():
    # deriving the freeze is outcome-independent: candidates + tier + OTE anchors are fixed pre-outcome
    a = freeze(); b = freeze()
    ok("candidate generation is outcome-independent (identical freezes)", a["logical_hash"] == b["logical_hash"])
    ok("source-tier fixed TIER_2 regardless of outcome", a["hierarchy"]["1_source_tier"]["selected_value_if_predetermined"] == "TIER_2_ADVANCED_EDUCATION_METHOD")
    ok("OTE anchor selection stays UNKNOWN (no outcome feedback)", a["supplemental_contracts"]["ote_shadow"]["selected_value_if_predetermined"] == "UNKNOWN")


def attack_f001_f002_training(tmp):
    fz = freeze(rclass="SCHEMA_BACKFILL_NOT_PROSPECTIVE")
    led = os.path.join(tmp, "o3.jsonl")
    rec = OP.attach_outcome(fz, POST, observation_cutoff=DEC + 10000, target=4050, ledger_path=led)
    ok("backfill (F001/F002 class) cannot be training-eligible", rec["eligibility"]["eligible_for_training"] is False)


def attack_straddle_prospective(tmp):
    fz = freeze(rclass="ACTIVATION_STRADDLE")
    led = os.path.join(tmp, "o4.jsonl")
    rec = OP.attach_outcome(fz, POST, observation_cutoff=DEC + 10000, target=4050, ledger_path=led)
    ok("activation-straddle not prospective-eligible", rec["eligibility"]["eligible_for_prospective_evidence"] is False)
    ok("activation-straddle not training-eligible", rec["eligibility"]["eligible_for_training"] is False)


def attack_ambiguous_definitive(tmp):
    fz = freeze()
    amb = [bar(DEC + 60, 4015, 4016, 4010, 4015), bar(DEC + 120, 4015, 4055, 3980, 4000)]
    led = os.path.join(tmp, "o5.jsonl")
    rec = OP.attach_outcome(fz, amb, observation_cutoff=DEC + 10000, target=4050, ledger_path=led)
    ok("ambiguous intrabar cannot become a definitive label", rec["labels"]["definitive_training_label_withheld"] is True
       and rec["labels"]["outcome_status"] == "AMBIGUOUS_INTRABAR_ORDER")
    ok("ambiguous is training-ineligible", rec["eligibility"]["eligible_for_training"] is False)


def attack_duplicate_outcome(tmp):
    fz = freeze()
    led = os.path.join(tmp, "o6.jsonl")
    for _ in range(4):
        OP.attach_outcome(fz, POST, observation_cutoff=DEC + 10000, target=4050, ledger_path=led)
    ok("duplicate outcome attachments fail closed (1 record)", sum(1 for _ in open(led)) == 1)


def attack_lane_contamination(tmp):
    fz = freeze()
    led = os.path.join(tmp, "o7.jsonl")
    rec = OP.attach_outcome(fz, POST, observation_cutoff=DEC + 10000, target=4050, ledger_path=led)
    lc = rec["lane_comparison"]
    ok("Lane A governance NOT modified", lc["lane_A_governance_modified"] is False)
    ok("no weights fitted in lane comparison", lc["weights_fitted"] is False)
    ok("no single-campaign superiority claim", lc["superiority_claim"] == "NONE (single campaign; descriptive only)")


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    tmp = tempfile.mkdtemp(prefix="leak_")
    attack_future_bars_in_features()
    attack_outcome_into_features(tmp)
    attack_outcome_mutates_freeze(tmp)
    attack_outcome_alters_candidates_or_tier()
    attack_f001_f002_training(tmp)
    attack_straddle_prospective(tmp)
    attack_ambiguous_definitive(tmp)
    attack_duplicate_outcome(tmp)
    attack_lane_contamination(tmp)
    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)
