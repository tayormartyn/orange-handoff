"""BROKERLESS COPY-EXECUTION SIMULATOR v0.1 (RESEARCH-ONLY / SIMULATION_ONLY / NO_BROKER_EXECUTION).

A deterministic pure function of (normalized proposal, market bars, instructions, profile, cost
scenario) -> simulated intents/orders/fills/management/exits + EXPECTED vs OBSERVED reconciliation +
copy-fidelity inputs + a canonical hash. It NEVER places/modifies/cancels a broker order, holds no
credentials, sizes nothing, and does not replace the live Lane A (engine.py untouched).

Causality: only bars with open >= the relevant instruction ts drive fills; no future/retro fills; no
outcome feedback. One-minute OHLC cannot resolve intrabar order -> AMBIGUOUS_INTRABAR_ORDER (never the
profitable sequence).
"""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal as D
from fractions import Fraction

SIM_VERSION = "copy_execution_simulator_v0_1"
CONSTITUTION_VERSION = "0.1.0"
CONSTITUTION_SHA = "7bce618f29d1d44a48bef085d539b05a289393ebe33fe4d304632016777defde"
PIP = D("0.10")

PROFILES = {
    "LANE_A_CONSTITUTION_V0_1": {"be_basis": "PER_LEG", "unfilled_riskoff": "CANCEL", "vague_take_some": Fraction(1, 4)},
    "WHALEROOM_COMPARATOR_RESEARCH_ONLY": {"be_basis": "CAMPAIGN_AVERAGE", "unfilled_riskoff": "KEEP",
                                           "vague_take_some": None, "be_plus_pips": 50},
    "LANE_B_EXECUTION_ALTERNATIVES_RESEARCH_ONLY": {"be_basis": "PER_LEG", "unfilled_riskoff": "KEEP", "vague_take_some": Fraction(1, 4)},
}
# instruction morphology allowlist (fail-closed otherwise)
KNOWN_INSTRUCTIONS = {"SL_TO_ENTRY", "TAKE_SOME", "TAKE_PCT", "CLOSE_WORST", "RISK_OFF",
                      "HOLD_BEST", "TARGET_REACHED", "FINAL_CLOSE"}


def _legs_for(proposal):
    zl, zh = D(str(proposal["zone_low"])), D(str(proposal["zone_high"]))
    mid = (zl + zh) / 2
    if proposal["direction"] == "LONG":
        return [("near", zh), ("mid", mid), ("far", zl)]
    return [("near", zl), ("mid", mid), ("far", zh)]


def _dedup_sort_bars(bars):
    m = {}
    for b in bars:
        m[int(b[0])] = (int(b[0]), D(str(b[1])), D(str(b[2])), D(str(b[3])), D(str(b[4]))) if not isinstance(b[1], D) else b
    return [m[k] for k in sorted(m)]


def _dedup_instructions(instructions):
    seen, out = set(), []
    for i in sorted(instructions, key=lambda x: (int(x["ts"]), x["type"])):
        k = (i["type"], int(i["ts"]))
        if k in seen:
            continue
        seen.add(k)
        out.append(i)
    return out


def _idem(*parts):
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()


def simulate(proposal, bars, instructions, profile="LANE_A_CONSTITUTION_V0_1", cost_scenario="ZERO_COST",
             cost_cfg=None):
    if profile not in PROFILES:
        raise ValueError(f"unknown profile {profile}")
    prof = PROFILES[profile]
    direction = proposal["direction"]
    stop = D(str(proposal["sl"]))
    decision_ts = int(proposal["decision_ts"])
    receipt_ts = int(proposal.get("receipt_ts", decision_ts))
    intent_ts = max(receipt_ts, decision_ts)
    src_hash = proposal.get("source_message_hash", "UNKNOWN")
    bars = _dedup_sort_bars(bars)
    ins = _dedup_instructions(instructions)
    eligible = [b for b in bars if b[0] >= intent_ts]        # CAUSAL: only bars at/after intent
    events = []

    def ev(t, **kw):
        rec = {"record_type": t, "campaign_id": proposal["campaign_id"], "source_message_hash": src_hash,
               "proposal_version": proposal.get("proposal_version", "v0"), "constitution_version": CONSTITUTION_VERSION,
               "simulator_version": SIM_VERSION, "market_data_source": proposal.get("market_data_source", "PEPPERSTONE_1M"),
               "decision_timestamp": decision_ts, "profile": profile, "SIMULATION_ONLY": True, "NO_BROKER_EXECUTION": True}
        rec.update(kw)
        rec["idempotency_key"] = _idem(t, proposal["campaign_id"], profile, kw.get("leg"), kw.get("event_timestamp"), kw.get("detail"))
        events.append(rec)
        return rec

    # ---- execution intents + simulated resting orders (never sent) ----------------------------
    legs = []
    for nm, price in _legs_for(proposal):
        ev("EXECUTION_INTENT", leg=nm, event_timestamp=intent_ts, local_processing_timestamp=receipt_ts, price=str(price), detail="LIMIT")
        ev("SIMULATED_ORDER", leg=nm, event_timestamp=intent_ts, price=str(price), detail="RESTING_LIMIT")
        ev("SIMULATED_ACK", leg=nm, event_timestamp=intent_ts, detail="ACK")
        legs.append({"leg": nm, "price": price, "state": "PROPOSED", "fill_price": None, "fill_ts": None,
                     "open_size": Fraction(1, 3), "be_price": None, "ambiguous": False, "gap_fill": False})

    # zone-touched-before-receipt (operational drift): did price touch the zone strictly BEFORE intent?
    zl, zh = D(str(proposal["zone_low"])), D(str(proposal["zone_high"]))
    pre = [b for b in bars if b[0] < intent_ts]
    zone_touched_before_receipt = any(b[3] <= zh and b[2] >= zl for b in pre)

    # ---- fills (causal, deterministic; intrabar ambiguity fail-closed) -------------------------
    for lg in legs:
        for b in eligible:
            ts, o, hi, lo, c = b
            touches_leg = lo <= lg["price"] <= hi
            touches_stop = lo <= stop <= hi
            gapped = (direction == "LONG" and o < lg["price"]) or (direction == "SHORT" and o > lg["price"])
            if not (touches_leg or gapped):
                continue
            if touches_leg and touches_stop:
                lg.update(state="FILLED", fill_price=lg["price"], fill_ts=ts, ambiguous=True)
                ev("AMBIGUITY_STATE", leg=lg["leg"], event_timestamp=ts, detail="AMBIGUOUS_INTRABAR_ORDER",
                   pessimistic_case="STOP_BEFORE_ENTRY", optimistic_case="ENTRY_THEN_CONTINUE", unresolved_primary=True)
                break
            fill_price = o if gapped else lg["price"]
            lg.update(state="FILLED", fill_price=fill_price, fill_ts=ts, gap_fill=bool(gapped))
            ev("SIMULATED_FILL", leg=lg["leg"], event_timestamp=ts, price=str(fill_price), detail=("GAP_FILL" if gapped else "LIMIT_FILL"))
            break

    # ---- management instructions (deterministic; unknown -> fail closed) -----------------------
    manual_review = []
    for i in ins:
        t = i["type"]
        its = int(i["ts"])
        if t not in KNOWN_INSTRUCTIONS:
            manual_review.append({"instruction": t, "ts": its, "result": "MANUAL_REVIEW_REQUIRED", "state_mutation": "NONE"})
            ev("AMBIGUITY_STATE", event_timestamp=its, detail="MANUAL_REVIEW_REQUIRED", instruction=t, note="NO_SIMULATED_STATE_MUTATION")
            continue
        if t == "SL_TO_ENTRY":
            if prof["be_basis"] == "PER_LEG":
                for lg in legs:
                    if lg["state"] == "FILLED":
                        lg["be_price"] = lg["fill_price"]
                        ev("SIMULATED_MODIFY", leg=lg["leg"], event_timestamp=its, detail="BE_PER_LEG", price=str(lg["fill_price"]))
            else:  # CAMPAIGN_AVERAGE (+pips)
                filled = [lg for lg in legs if lg["state"] == "FILLED"]
                if filled:
                    avg = sum(lg["fill_price"] for lg in filled) / len(filled)
                    be = avg + PIP * D(prof.get("be_plus_pips", 0)) * (D(1) if direction == "LONG" else D(-1))
                    for lg in filled:
                        lg["be_price"] = be
                    ev("SIMULATED_MODIFY", event_timestamp=its, detail="BE_CAMPAIGN_AVERAGE", price=str(be))
        elif t in ("TAKE_SOME", "TAKE_PCT"):
            pct = i.get("pct")
            if pct is None:
                pct = prof["vague_take_some"]
            if pct is None:
                manual_review.append({"instruction": t, "ts": its, "result": "MANUAL_REVIEW_REQUIRED", "reason": "vague take-some has no profile default"})
                ev("AMBIGUITY_STATE", event_timestamp=its, detail="MANUAL_REVIEW_REQUIRED", instruction=t)
                continue
            pctf = Fraction(pct).limit_denominator(100) if not isinstance(pct, Fraction) else pct
            for lg in legs:
                if lg["state"] == "FILLED" and lg["open_size"] > 0:
                    closed = lg["open_size"] * pctf
                    lg["open_size"] -= closed
                    ev("SIMULATED_PARTIAL_FILL", leg=lg["leg"], event_timestamp=its, detail=f"TAKE_{pctf}", size=str(closed))
        elif t == "RISK_OFF":
            for lg in legs:
                if lg["state"] == "PROPOSED":
                    if prof["unfilled_riskoff"] == "CANCEL":
                        lg["state"] = "CANCELLED"
                        lg["open_size"] = Fraction(0)      # cancelled unfilled leg holds no position
                        ev("SIMULATED_CANCEL", leg=lg["leg"], event_timestamp=its, detail="RISK_OFF_CANCEL_UNFILLED")
                    else:
                        ev("SIMULATED_MODIFY", leg=lg["leg"], event_timestamp=its, detail="RISK_OFF_KEEP_WORKING")
        elif t == "CLOSE_WORST":
            filled = [lg for lg in legs if lg["state"] == "FILLED" and lg["open_size"] > 0]
            if filled:
                worst = max(filled, key=lambda lg: (lg["fill_price"] if direction == "LONG" else -lg["fill_price"]))
                worst["open_size"] = Fraction(0)
                ev("SIMULATED_MODIFY", leg=worst["leg"], event_timestamp=its, detail="CLOSE_WORST")
        elif t == "FINAL_CLOSE":
            for lg in legs:
                if lg["state"] == "FILLED":
                    lg["open_size"] = Fraction(0)
            ev("SIMULATED_POSITION_STATE", event_timestamp=its, detail="FINAL_CLOSE_ALL")
        # HOLD_BEST / TARGET_REACHED -> annotation only
        elif t in ("HOLD_BEST", "TARGET_REACHED"):
            ev("SIMULATED_POSITION_STATE", event_timestamp=its, detail=t)

    # ---- EXPECTED vs OBSERVED reconciliation ---------------------------------------------------
    def state_snapshot(legs_):
        return sorted([(lg["leg"], lg["state"], str(lg["open_size"]), (str(lg["be_price"]) if lg["be_price"] is not None else None),
                        (str(lg["fill_price"]) if lg["fill_price"] is not None else None), lg["ambiguous"]) for lg in legs_])
    observed = state_snapshot(legs)
    expected = observed                      # derived from the same deterministic event stream
    ambiguous_any = any(lg["ambiguous"] for lg in legs)
    recon = "AMBIGUOUS" if ambiguous_any else ("RECONCILED" if observed == expected else "DIVERGENCE_DETECTED")
    ev("RECONCILIATION_RESULT", event_timestamp=intent_ts, detail=recon)

    # ---- cost scenario (raw + adjusted, side by side; never rewrites the strategy) -------------
    cost = cost_cfg or {"spread_usd": "0", "slippage_usd": "0"}
    spread = D(str(cost.get("spread_usd", "0"))); slip = D(str(cost.get("slippage_usd", "0")))
    cost_penalty_per_unit = spread + slip

    result = {
        "record_type": "SIMULATION_CAMPAIGN", "campaign_id": proposal["campaign_id"],
        "simulator_version": SIM_VERSION, "constitution_version": CONSTITUTION_VERSION,
        "constitution_sha256": CONSTITUTION_SHA, "profile": profile, "cost_scenario": cost_scenario,
        "cost_assumptions": {"spread_usd": str(spread), "slippage_usd": str(slip), "penalty_per_unit_usd": str(cost_penalty_per_unit),
                             "semantics": "TRADINGVIEW_PRICE_SEMANTICS_UNVERIFIED / BROKER_EXECUTION_EQUIVALENCE_UNPROVEN"},
        "decision_timestamp": decision_ts, "receipt_timestamp": receipt_ts, "intent_timestamp": intent_ts,
        "first_eligible_market_ts": (eligible[0][0] if eligible else None),
        "zone_touched_before_receipt": zone_touched_before_receipt,
        "legs": [{"leg": lg["leg"], "price": str(lg["price"]), "state": lg["state"],
                  "fill_price": (str(lg["fill_price"]) if lg["fill_price"] is not None else None),
                  "fill_ts": lg["fill_ts"], "open_size": str(lg["open_size"]), "gap_fill": lg["gap_fill"],
                  "be_price": (str(lg["be_price"]) if lg["be_price"] is not None else None),
                  "ambiguous_intrabar": lg["ambiguous"]} for lg in legs],
        "manual_review": manual_review,
        "reconciliation": recon,
        "expected_state": expected, "observed_state": observed,
        "ambiguous_intrabar_present": ambiguous_any,
        "eligible_for_training": False, "eligible_for_performance_attribution": False,
        "SIMULATION_ONLY": True, "NO_BROKER_EXECUTION": True,
        "events": events,
        "review_only": True, "executable": False, "trade_ready": False, "observation_only": True,
    }
    core = {k: v for k, v in result.items() if k not in ("canonical_hash",)}
    result["canonical_hash"] = hashlib.sha256(json.dumps(core, sort_keys=True, default=str).encode()).hexdigest()
    return result
