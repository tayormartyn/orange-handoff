"""Build campaigns from the frozen forward-ledger XAU_F_SETUP records, run both lanes,
emit review cards + append-only follower ledger records. Deterministic and idempotent.

Sources (read-only, never mutated):
  * farouk_plus/forward_validation_ledger_v0_2.jsonl  (XAU_F_SETUP records — frozen evidence)
  * price_data/XAUUSD_1M_PEPPERSTONE_2026-07-14_0730_to_1629_PARTIAL.csv (imported, hash-pinned)
  * follower_constitution_v0_1.json (RATIFIED)
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from engine import run_campaign, sha256_file, sha256_obj          # noqa: E402
import guards                                                     # noqa: E402

FP = os.path.dirname(HERE)
FWD_LEDGER = os.path.join(FP, "forward_validation_ledger_v0_2.jsonl")
OHLC = os.path.join(FP, "..", "price_data",
                    "XAUUSD_1M_PEPPERSTONE_2026-07-14_0730_to_1629_PARTIAL.csv")
CONST = os.path.join(HERE, "follower_constitution_v0_1.json")
FOLLOWER_LEDGER = os.path.join(HERE, "follower_ledger_v0_1.jsonl")
CARD_DIR = os.path.join(HERE, "cards")

BANNER = "NO BROKER ACTION | NO ORDER SUBMISSION | REVIEW-ONLY SHADOW PROPOSAL"


def iso_to_epoch(s):
    return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())


def load_bars(path):
    bars = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for r in csv.reader(fh):
            if r[0] == "time":
                continue
            bars.append((int(r[0]), D(r[1]), D(r[2]), D(r[3]), D(r[4])))
    bars.sort()
    return bars


def load_setups():
    setups = {}
    with open(FWD_LEDGER, encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            if r.get("record_type") == "XAU_F_SETUP":
                setups[r["setup_id"]] = r      # last revision wins (append-only corrections)
    return setups


def campaign_from_setup(rec):
    lo, hi = rec["entry_zone"].split("-")
    sl = rec["sl"].split(" ")[0]                     # leading number; annotation preserved in card
    events = []
    for e in rec["management_timing_8c"]["instruction_events"]:
        events.append({"ts": iso_to_epoch(e["timestamp_utc"]),
                       "instruction_type": e["instruction_type"],
                       "message_id": e.get("message_id"),
                       "scope": e.get("scope"), "pct": e.get("pct"),
                       # explicit percentage scale-out payload (EPPC engine mapping v0.1):
                       # carried through so the engine can verify close/retain reconcile and
                       # never silently defaults an explicit instruction's fraction
                       "close_percentage": e.get("close_percentage"),
                       "retain_percentage": e.get("retain_percentage"),
                       "quantity_base": e.get("quantity_base"),
                       "new_sl": e.get("new_sl")})
    return {
        "setup_id": rec["setup_id"], "direction": rec["direction"],
        "zone_low": min(D(lo), D(hi)), "zone_high": max(D(lo), D(hi)), "sl": sl,
        "signal_ts": iso_to_epoch(rec["timestamp_utc"]),
        "attempt_number": rec["scoring_features_used"]["attempt_number"],
        "events": events,
        "frozen_evidence_sha256": rec["frozen_evidence_sha256"],
        "posted_sl_annotation": rec["sl"],
    }


def make_card(rec, campaign, lanes, prov):
    card = {
        "banner": BANNER,
        "card_type": "REVIEW_ONLY_SHADOW_PROPOSAL",
        "campaign_id": rec["setup_id"],
        "source_timestamp_utc": rec["timestamp_utc"],
        "direction": rec["direction"],
        "zone": rec["entry_zone"],
        "posted_follower_stop": rec["sl"],
        "constitution_version": prov["constitution_version"],
        "constitution_sha256": prov["constitution_sha256"],
        "theoretical_legs": lanes["LANE_A"]["legs"],
        "fill_state": {lk: {"legs": lanes[lk]["legs"], "state": lanes[lk]["campaign_state"]}
                       for lk in ("LANE_A", "LANE_B")},
        "management_state": {
            "instructions_applied": [t for t in lanes["LANE_A"]["transitions"]
                                     if t["event"] in ("BANK", "BE_ARMED", "LEG_CANCELLED", "PAUSED",
                                                       "INSTRUCTION_NOT_APPLICABLE")],
        },
        "strict_follower_status": {
            "state": lanes["LANE_A"]["campaign_state"],
            "realized_pips_per_unit": lanes["LANE_A"]["realized_pips_per_unit"],
            "unrealized_pips_per_unit": lanes["LANE_A"]["unrealized_pips_per_unit"],
            "follow_through": lanes["LANE_A"]["follow_through"],
        },
        "policy_sensitivity_status": {
            "state": lanes["LANE_B"]["campaign_state"],
            "realized_pips_per_unit": lanes["LANE_B"]["realized_pips_per_unit"],
            "unrealized_pips_per_unit": lanes["LANE_B"]["unrealized_pips_per_unit"],
            "follow_through": lanes["LANE_B"]["follow_through"],
            "disclaimer": lanes["lane_b_disclaimer"],
        },
        "unresolved_ambiguities": {lk: lanes[lk]["ambiguities"] for lk in ("LANE_A", "LANE_B")},
        "detector_v0_2_label": rec["detector_v0_2"]["review_label"],
        "detector_v0_3_label": rec["detector_v0_3"]["review_label"],
        "pre_mark_comparisons": rec["pre_mark_comparison"],
        "evidence_links": {
            "message_ids": rec["message_ids"],
            "frozen_evidence_sha256": rec["frozen_evidence_sha256"],
            "media": rec.get("media", []),
            "forward_ledger": "forward_validation_ledger_v0_2.jsonl",
            "ohlc_sha256": prov["ohlc_sha256"],
        },
        "acknowledgement_state": "REVIEW",
        "acknowledgement_note": "REVIEW/ACKNOWLEDGED/REJECTED is an annotation with zero execution consequence",
        "review_only": True, "executable": False, "trade_ready": False, "observation_only": True,
    }
    guards.assert_clean(card, f"card {rec['setup_id']}")
    return card


def card_markdown(card):
    a, b = card["strict_follower_status"], card["policy_sensitivity_status"]
    legs = "\n".join(f"| {l['leg_id'].split('/')[-1]} | {l['price']} | {l['kind']} | {l['state']} | "
                     f"{l['fill_price'] or '—'} | {l['open_size']} |"
                     for l in card["theoretical_legs"])
    ambig = []
    for lk, items in card["unresolved_ambiguities"].items():
        ambig += [f"- {lk}: {i['note']} (bar {i['bar_ts']})" for i in items]
    return f"""# {card['campaign_id']} — REVIEW-ONLY SHADOW PROPOSAL

> **{card['banner']}**

| | |
|---|---|
| Source timestamp | {card['source_timestamp_utc']} |
| Direction / zone | **{card['direction']} {card['zone']}** |
| Posted follower stop | {card['posted_follower_stop']} |
| Constitution | {card['constitution_version']} (`{card['constitution_sha256'][:12]}…`) |
| v0.2 / v0.3 label | {card['detector_v0_2_label']} / {card['detector_v0_3_label']} |
| Pre-marks | {', '.join(f"{k.split('-')[1]}:{v}" for k, v in card['pre_mark_comparisons'].items())} |
| Acknowledgement | **{card['acknowledgement_state']}** (annotation only) |

## Theoretical legs (LANE A)
| leg | price | kind | state | fill | open |
|---|---|---|---|---|---|
{legs}

## Strict follower (LANE A — headline)
state **{a['state']}** · realized **{a['realized_pips_per_unit']} pips/unit** · unrealized {a['unrealized_pips_per_unit'] or '—'} · {a['follow_through']}

## Policy sensitivity (LANE B — never Farouk's actual result)
state **{b['state']}** · realized **{b['realized_pips_per_unit']} pips/unit** · unrealized {b['unrealized_pips_per_unit'] or '—'} · {b['follow_through']}

## Unresolved ambiguities
{chr(10).join(ambig) if ambig else '- none recorded'}

Evidence: msgs {card['evidence_links']['message_ids']} · frozen `{card['evidence_links']['frozen_evidence_sha256'][:12]}…` · OHLC `{card['evidence_links']['ohlc_sha256'][:12]}…`
"""


def run(setup_ids=("XAU-F001-20260714", "XAU-F002-20260714"), write=True):
    constitution = json.load(open(CONST, encoding="utf-8"))
    if constitution.get("status") != "RATIFIED":
        raise guards.GuardViolation("constitution not ratified — fail closed")
    bars = load_bars(OHLC)
    setups = load_setups()
    prov = {"constitution_version": constitution["version"],
            "constitution_sha256": sha256_file(CONST),
            "ohlc_sha256": sha256_file(OHLC),
            "run_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    results = {}
    for sid in setup_ids:
        rec = setups[sid]
        campaign = campaign_from_setup(rec)
        lanes = run_campaign(campaign, bars, constitution)
        card = make_card(rec, campaign, lanes, prov)
        logical = sha256_obj({"setup": sid, "constitution": prov["constitution_sha256"],
                              "evidence": rec["frozen_evidence_sha256"],
                              "ohlc": prov["ohlc_sha256"],
                              "lanes": {k: lanes[k] for k in ("LANE_A", "LANE_B")}})
        ledger_rec = {
            "record_type": "FOLLOWER_CAMPAIGN_RESULT", "schema": "follower_ledger_v0_1",
            "setup_id": sid, "logical_hash": logical, "provenance": prov,
            "lanes": {k: lanes[k] for k in ("LANE_A", "LANE_B")},
            "headline_lane": "LANE_A", "banner": BANNER,
            "review_only": True, "executable": False, "trade_ready": False, "observation_only": True,
        }
        if write:
            os.makedirs(CARD_DIR, exist_ok=True)
            with open(os.path.join(CARD_DIR, f"{sid}.json"), "w", encoding="utf-8") as fh:
                json.dump(card, fh, indent=1, ensure_ascii=False, default=str)
            with open(os.path.join(CARD_DIR, f"{sid}.md"), "w", encoding="utf-8") as fh:
                fh.write(card_markdown(card))
            appended = guards.append_once(FOLLOWER_LEDGER, ledger_rec)
        else:
            appended = None
        results[sid] = {"lanes": lanes, "card": card, "logical_hash": logical,
                        "ledger_appended": appended}
    return results


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    out = run()
    for sid, r in out.items():
        a = r["lanes"]["LANE_A"]
        b = r["lanes"]["LANE_B"]
        print(f"{sid}: LANE_A {a['campaign_state']} realized {a['realized_pips_per_unit']}p/unit "
              f"unreal {a['unrealized_pips_per_unit']} | LANE_B {b['campaign_state']} "
              f"realized {b['realized_pips_per_unit']}p/unit unreal {b['unrealized_pips_per_unit']} "
              f"| hash {r['logical_hash'][:12]} appended={r['ledger_appended']}")
    print("invariants:", guards.verify_project_invariants())
