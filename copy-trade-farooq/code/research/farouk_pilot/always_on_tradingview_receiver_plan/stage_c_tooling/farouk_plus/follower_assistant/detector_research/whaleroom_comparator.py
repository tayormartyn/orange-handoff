"""Documented-follower-policy comparator (RESEARCH-ONLY, OFFLINE, NOT_LIVE).

Replays the FROZEN F001/F002 campaign cards under four policies and reports mechanical results.
Does NOT modify Constitution v0.1, does NOT touch the live follower, submits no order. All prices
per-unit pips ($0.10 = 1 pip). Where a documented template needs an input F001/F002 never posted
(TP levels), the result is UNKNOWN — never fabricated.

Precedence (precedence_rule_v0_1): EXPLICIT_POSTED_TELEGRAM_INSTRUCTION > DOCUMENTED_TEMPLATE_DEFAULT,
per action per timestamp.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
FA = os.path.dirname(HERE)
UNKNOWN = "UNKNOWN"
PIP = D("0.10")


def _load_1m(path):
    out = []
    for r in csv.reader(open(path, encoding="utf-8-sig")):
        if not r or r[0] in ("time", ""):
            continue
        out.append((int(r[0]), D(r[1]), D(r[2]), D(r[3]), D(r[4])))
    out.sort()
    return out


def _card(cid):
    return json.load(open(os.path.join(FA, "cards", f"{cid}.json"), encoding="utf-8"))


def _pips(direction, entry, price):
    d = (price - entry) if direction == "LONG" else (entry - price)
    return d / PIP


def replay(card, m1):
    """Deterministic replay of ONE frozen card under all four policies."""
    cid = card["campaign_id"]
    direction = card["direction"]
    legs = card["theoretical_legs"]
    filled = [l for l in legs if l["state"] == "FILLED"]
    cancelled = [l for l in legs if l["state"] == "CANCELLED"]
    n_filled = len(filled)
    avg = (sum(D(l["fill_price"]) for l in filled) / n_filled) if n_filled else None
    stop = D(card["posted_follower_stop"].split()[0])
    # walk bars at/after the campaign source timestamp (no future/forming leakage: completed 1m only)
    from datetime import datetime, timezone
    src = card["source_timestamp_utc"].replace("+00:00", "")
    src_ts = int(datetime.fromisoformat(src).replace(tzinfo=timezone.utc).timestamp())
    fwd = [b for b in m1 if b[0] >= src_ts]

    # MAE/MFE from average across the forward window (raw, using the actual 1m path)
    if avg is not None and fwd:
        mfe = max(_pips(direction, avg, b[2] if direction == "LONG" else b[3]) for b in fwd)
        mae = min(_pips(direction, avg, b[3] if direction == "LONG" else b[2]) for b in fwd)
    else:
        mfe = mae = None

    # +50-from-average reachability & first-touch bar
    plus50_ts = None
    if avg is not None:
        tgt = avg + D("5") if direction == "LONG" else avg - D("5")   # 50 pips = $5
        for b in fwd:
            hit = (b[2] >= tgt) if direction == "LONG" else (b[3] <= tgt)
            if hit:
                plus50_ts = b[0]
                break

    common = {
        "campaign_id": cid, "direction": direction,
        "filled_legs": n_filled, "cancelled_legs": len(cancelled),
        "campaign_average_entry": (str(avg) if avg is not None else UNKNOWN),
        "single_fill_note": ("ONLY 1 OF 3 LEGS FILLED -> average == single fill; "
                             "average-entry machinery collapses to per-leg for this campaign"
                             if n_filled == 1 else f"{n_filled} legs filled"),
        "posted_stop": str(stop),
        "raw_mae_pips_from_avg_UNBOUNDED": (str(mae.quantize(D('0.01'))) if mae is not None else UNKNOWN),
        "raw_mfe_pips_from_avg_UNBOUNDED": (str(mfe.quantize(D('0.01'))) if mfe is not None else UNKNOWN),
        "mfe_window_note": ("UNBOUNDED = path-high over ALL available 1m bars from signal to end-of-data; "
                            "it OVERSTATES what a follower would see at campaign freeze. The frozen card's "
                            "campaign-bounded MFE/MAE is the authoritative pair (below)."),
        "card_frozen_strict_mfe": card["strict_follower_lane"]["mfe_pips"],
        "card_frozen_strict_mae": card["strict_follower_lane"]["mae_pips"],
        "card_frozen_policy_mfe": card["policy_sensitivity_lane"]["mfe_pips"],
        "card_frozen_policy_mae": card["policy_sensitivity_lane"]["mae_pips"],
        "plus50_from_avg_reachable": plus50_ts is not None,
        "plus50_first_bar_ts": plus50_ts,
        "feed_sensitive_events": len(card.get("unresolved_ambiguities", [])),
        "cost_adjustment": "UNKNOWN (spread/commission for follower's broker not in scope; raw only)",
    }

    strict = card["strict_follower_lane"]
    polic = card["policy_sensitivity_lane"]

    policies = {
        "A_CURRENT_STRICT_ORANGE": {
            "be_basis": "PER_LEG", "be_trigger": "posted 'sl to entry'",
            "unfilled_legs": "CANCELLED (risk-off)",
            "realized_pips_per_unit": strict["realized_pips_per_unit"],
            "runner": "none (strict banks & scratches)",
            "source": "FROZEN strict_follower_lane (Constitution v0.1)",
        },
        "B_DOCUMENTED_WHALEROOM_AVERAGE_BE": {
            "be_basis": "CAMPAIGN_AVERAGE", "be_trigger": "+50 pips FROM AVERAGE (DR-306/301)",
            "unfilled_legs": ("would REMAIN WORKING under DR-306 (no 4th losing add); "
                              "but mid/far here were never touched -> same fill set as A"),
            "realized_pips_per_unit": polic["realized_pips_per_unit"],
            "unrealized_pips_per_unit": polic.get("unrealized_pips_per_unit"),
            "runner": "kept (policy-sensitivity lane)",
            "equivalence_to_A": ("MECHANICALLY IDENTICAL to A on this campaign because only 1 leg "
                                 "filled -> average==fill and +50-from-average == +50-from-leg"),
            "source": "FROZEN policy_sensitivity_lane + DR-306/301",
        },
        "C_DOCUMENTED_CONSERVATIVE_TP": {
            "tp_template": "50/30/20 at posted TP1/TP2/TP3 (DR-304)",
            "result": UNKNOWN,
            "reason": "F001/F002 posted NO explicit TP LEVELS -> template inputs absent -> UNKNOWN (not fabricated)",
        },
        "D_DOCUMENTED_ADVANCED_TP": {
            "tp_template": "30/30 + move SL to entry(+50) + runner (DR-304)",
            "thirty_thirty_result": UNKNOWN,
            "thirty_thirty_reason": "no posted TP levels for the 30/30 tranche -> UNKNOWN",
            "runner_mfe_pips_card_bounded": card["policy_sensitivity_lane"]["mfe_pips"],
            "runner_mfe_pips_unbounded_diag": (str(mfe.quantize(D('0.01'))) if mfe is not None else UNKNOWN),
            "runner_note": ("the runner's UNREALIZED MFE is the ONLY quantity approaching the posted "
                            "pip claim; it is UNREALIZED path-high, NOT a realized follower result. A "
                            "runner left open would ultimately exit at its BE/stop, not at MFE."),
        },
    }

    # precedence application record
    precedence_events = []
    for ins in card.get("management_instructions", []):
        if ins["instruction_type"] in ("SL_TO_ENTRY", "TAKE_PCT_OFF", "TP1_TAKE", "FINAL_CLOSE"):
            precedence_events.append({
                "instruction": ins["instruction_type"], "ts": ins.get("timestamp_utc"),
                "pct": ins.get("pct", None),
                "precedence": "EXPLICIT_POSTED overrides DOCUMENTED_TEMPLATE at this action/ts",
            })

    return {**common, "policies": policies, "precedence_events": precedence_events}


def main():
    price = os.path.join(FA, "..", "..", "price_data",
                         "XAUUSD_1M_PEPPERSTONE_2026-07-08_to_2026-07-15_CANONICAL.csv")
    m1 = _load_1m(price)
    out = {
        "comparator_id": "whaleroom_comparator_v0_1",
        "status": "RESEARCH_ONLY / OFFLINE / NOT_LIVE / does NOT modify Constitution v0.1 / no order",
        "precedence_rule": "precedence_rule_v0_1 (EXPLICIT_POSTED > DOCUMENTED_TEMPLATE per action/ts)",
        "campaigns": [replay(_card(c), m1) for c in ("XAU-F001-20260714", "XAU-F002-20260714")],
        "headline_finding": (
            "On BOTH F001 and F002 only 1 of 3 legs filled, so documented average-entry policies "
            "(B/D) are MECHANICALLY IDENTICAL to strict per-leg (A) for these campaigns. Conservative/"
            "Advanced TP templates (C/D 30-30) are UNKNOWN because no TP levels were posted. The posted "
            "~700-pip magnitude corresponds ONLY to an UNREALIZED runner MFE, not any realized follower "
            "policy. The strict-vs-Farouk divergence is therefore NOT explained by BE-basis or TP-template "
            "choice on this data; his private fills/sizing remain UNKNOWN."),
        "review_only": True, "executable": False, "trade_ready": False, "observation_only": True,
    }
    outp = os.path.join(HERE, "whaleroom_comparator_result_v0_1.json")
    json.dump(out, open(outp, "w", encoding="utf-8"), indent=1, default=str)
    sys.stdout = __import__("io").TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    print(f"written {outp}")
    for c in out["campaigns"]:
        print(f"\n{c['campaign_id']} {c['direction']}: filled={c['filled_legs']}/3 "
              f"avg={c['campaign_average_entry']} cardMFE(policy)={c['card_frozen_policy_mfe']} "
              f"unboundedMFE={c['raw_mfe_pips_from_avg_UNBOUNDED']}")
        print("  A strict realized:", c["policies"]["A_CURRENT_STRICT_ORANGE"]["realized_pips_per_unit"])
        print("  B avg-BE realized:", c["policies"]["B_DOCUMENTED_WHALEROOM_AVERAGE_BE"]["realized_pips_per_unit"],
              "| equiv:", c["policies"]["B_DOCUMENTED_WHALEROOM_AVERAGE_BE"]["equivalence_to_A"][:60])
        print("  C conservative:", c["policies"]["C_DOCUMENTED_CONSERVATIVE_TP"]["result"])
        print("  D runner MFE (card-bounded):", c["policies"]["D_DOCUMENTED_ADVANCED_TP"]["runner_mfe_pips_card_bounded"])
    print("\n" + out["headline_finding"])


if __name__ == "__main__":
    main()
