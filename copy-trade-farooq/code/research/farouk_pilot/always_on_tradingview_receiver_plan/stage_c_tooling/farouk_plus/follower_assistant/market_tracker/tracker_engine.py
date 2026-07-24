"""Deterministic shadow management engine (Stage 1.5).

The follower engine (engine.py) remains the SINGLE arithmetic authority: on every cycle a
campaign is recomputed FROM SCRATCH over all completed bars observed so far (deterministic,
idempotent, restart-safe by construction — state is derived, never accumulated). This module
adds, deterministically:

  * lifecycle-state derivation (PROPOSAL_CREATED .. OUTCOME_FROZEN)
  * MAE / MFE vs running fill-weighted average entry
  * zone distance / touch time / freshness
  * plus-50 DIAGNOSTIC (disabled policy: per ratified P09 it never moves state)
  * same-bar / feed / gap ambiguity classifications
  * extended review-card regeneration (same cards/, atomic replace — no second card system)

NO AI anywhere in this path. REVIEW-ONLY: no order/broker/execution surface exists.
"""
from __future__ import annotations

import json
import os
import sys
from decimal import Decimal as D
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
for p in (HERE, PARENT):
    if p not in sys.path:
        sys.path.insert(0, p)
from engine import FollowerEngine, sha256_obj, pips                # noqa: E402
import guards                                                      # noqa: E402

BANNER = "NO BROKER ACTION | NO ORDER SUBMISSION | REVIEW-ONLY SHADOW PROPOSAL"
TRACKER_SCHEMA = "tracker_state_v0_1"


def _dec(x):
    return D(str(x))


def run_lane(campaign: dict, bars: list, lane: str, constitution: dict) -> dict:
    eng = FollowerEngine(campaign, bars, lane, constitution)
    res = eng.run()
    res["_legs_obj"] = eng.legs
    return res


def running_average_series(legs, bars):
    """[(bar_ts, avg_entry or None)] — fill-weighted average of legs filled by each bar."""
    fills = sorted((l.fill_bar_ts, l.fill_price, l.size) for l in legs
                   if l.fill_price is not None)
    out = []
    for ts, o, h, l, c in bars:
        cur = [(p, s) for ft, p, s in fills if ft is not None and ft <= ts]
        if not cur:
            out.append((ts, None))
            continue
        tot = sum((s for _, s in cur), Fraction(0))
        acc = sum((p * D(s.numerator) / D(s.denominator) for p, s in cur), D(0))
        out.append((ts, acc / (D(tot.numerator) / D(tot.denominator))))
    return out


def mae_mfe(direction, legs, bars, end_ts=None):
    sgn = D(1) if direction == "LONG" else D(-1)
    worst = best = None
    for (ts, o, h, l, c), (_, avg) in zip(bars, running_average_series(legs, bars)):
        if avg is None or (end_ts and ts > end_ts):
            continue
        fav = (h - avg) if direction == "LONG" else (avg - l)
        adv = (avg - l) if direction == "LONG" else (h - avg)
        best = fav if best is None else max(best, fav)
        worst = adv if worst is None else max(worst, adv)
    return (str(pips(-worst)) if worst is not None else None,     # MAE as negative pips
            str(pips(best)) if best is not None else None)


def plus50_diagnostic(direction, legs, bars):
    """DISABLED policy (ratified P09): purely reports the first bar where +50 pips ($5)
    from the running average entry was reachable. Moves no state."""
    for (ts, o, h, l, c), (_, avg) in zip(bars, running_average_series(legs, bars)):
        if avg is None:
            continue
        if direction == "LONG" and h >= avg + D("5"):
            return {"reachable": True, "first_bar_ts": ts, "status": "DIAGNOSTIC_ONLY_P09_DISABLED"}
        if direction == "SHORT" and l <= avg - D("5"):
            return {"reachable": True, "first_bar_ts": ts, "status": "DIAGNOSTIC_ONLY_P09_DISABLED"}
    return {"reachable": False, "first_bar_ts": None, "status": "DIAGNOSTIC_ONLY_P09_DISABLED"}


def lifecycle_state(res: dict, campaign: dict, bars: list) -> dict:
    """Deterministic lifecycle derivation from an engine result."""
    legs = res["legs"]
    slices = res["slices"]
    fills = [l for l in legs if l["state"] == "FILLED"]
    n_fills = len(fills)
    open_size = sum(Fraction(l["open_size"]) for l in legs)
    be_armed = any(l["be_price"] for l in legs)
    be_scratch = [s for s in slices if s["reason"] == "P10_BE_SCRATCH"]
    stop_hits = [s for s in slices if s["reason"] == "P21_POSTED_SL"]
    partials = [s for s in slices if s["reason"].startswith(("P12", "P11", "ADD_TP2"))]
    manual = [s for s in slices if s["reason"] == "P13_FINAL_CLOSE"]
    path = ["PROPOSAL_CREATED"]
    zone_touch_ts = None
    if bars:
        near = D(legs[0]["price"])
        for ts, o, h, l, c in bars:
            hit = (l <= near) if campaign["direction"] == "LONG" else (h >= near)
            if hit:
                zone_touch_ts = ts
                break
        path.append("WAITING_FOR_ZONE")
        if zone_touch_ts:
            path.append("ZONE_TOUCHED")
    for i in range(min(n_fills, 3)):
        path.append(f"LEG_{i + 1}_FILLED")
    if n_fills:
        path.append("FULLY_FILLED" if n_fills == 3 else "PARTIALLY_FILLED")
        path.append("RISK_ACTIVE")
    if be_armed or be_scratch:
        path.append("BE_INSTRUCTED")
    if be_scratch:
        path.append("BE_TRIGGERED")
    if partials:
        path.append("PARTIAL_PROFIT_TAKEN")
    if n_fills and open_size > 0 and partials:
        path.append("RUNNER_ACTIVE")
    st = res["campaign_state"]
    # terminal labels (red-team finding 14): a FINAL_CLOSE instruction anywhere in the
    # campaign labels it MANUALLY_CLOSED even if the runner was already flat; STOPPED only
    # when a posted-SL slice actually ended the campaign; EXPIRED only on 24h expiry.
    final_close_seen = any(e.get("instruction_type") in ("FINAL_CLOSE", "EXPLICIT_FULL_EXIT")
                           for e in campaign.get("events", []))
    expiry_cancel = any(t.get("rule") == "P16_24H_EXPIRY" for t in res["transitions"])
    terminal = None
    if st == "PAUSED_NEEDS_HUMAN_REVIEW":
        terminal = "HUMAN_REVIEW_REQUIRED"
    elif st == "CLOSED" and stop_hits and not final_close_seen:
        terminal = "STOPPED"
    elif st == "CLOSED" and final_close_seen:
        terminal = "MANUALLY_CLOSED"
    elif st == "CLOSED" and stop_hits:
        terminal = "STOPPED"
    elif st == "CLOSED" and be_scratch and open_size == 0 and not partials:
        terminal = "SCRATCHED"
    elif st == "CLOSED" and be_scratch and open_size == 0:
        terminal = "PARTIALS_BANKED_RUNNER_SCRATCHED"
    elif st == "CLOSED":
        terminal = "MANUALLY_CLOSED"
    elif st == "NO_FILL":
        terminal = "EXPIRED" if expiry_cancel else "NO_FILL"
    if terminal is None and stop_hits and open_size == 0:
        # position fully stopped but resting legs keep the campaign technically open
        path.append("STOPPED")
    if terminal:
        path.append(terminal)
        if st in ("CLOSED", "NO_FILL"):
            path.append("OUTCOME_FROZEN")
    return {"path": path, "current": path[-1], "zone_touch_ts": zone_touch_ts,
            "open_size": str(open_size), "n_fills": n_fills}


def ambiguity_classifications(res: dict) -> list:
    out = []
    for t in res["transitions"]:
        tags = t.get("tags") or []
        if "AMBIGUOUS_SEQUENCE" in tags:
            out.append({"bar_ts": t.get("bar_ts"), "class": "AMBIGUOUS_SEQUENCE",
                        "event": t["event"]})
        if "AMBIGUOUS_FILL_BAND" in tags:
            out.append({"bar_ts": t.get("bar_ts"), "class": "FEED_SENSITIVE_TOUCH",
                        "event": t["event"]})
        if "BE_PRECEDES_SL_SAME_BAR" in tags:
            out.append({"bar_ts": t.get("bar_ts"), "class": "STOP_BEFORE_ENTRY_CONFIRMED",
                        "event": "BE-and-SL struck in one bar; BE resolved first (continuous-path argument)"})
    return out


def gap_classifications(campaign, bars, legs):
    """Gap-through-entry / gap-through-stop detection: a bar OPENING at/beyond a level that
    was never traded through before it means the fill/stop price is uncertain (no ticks).
    Covers the initial posted stop, every REVISED_STOP level, and armed BE levels
    (red-team finding 8b); boundary equality counts as a gap."""
    out = []
    if not bars:
        return out
    sgn_long = campaign["direction"] == "LONG"
    risk_levels = {D(str(campaign["sl"]))}
    for e in campaign.get("events", []):
        if e.get("instruction_type") == "REVISED_STOP" and e.get("new_sl"):
            risk_levels.add(D(str(e["new_sl"])))
    for leg in legs:
        if leg.get("be_price"):
            risk_levels.add(D(str(leg["be_price"])))
    prev_close = None
    for ts, o, h, l, c in bars:
        if prev_close is not None:
            for leg in legs:
                lp = D(leg["price"])
                jumped = (o <= lp < prev_close) if sgn_long else (prev_close < lp <= o)
                if jumped and leg["state"] == "FILLED":
                    out.append({"bar_ts": ts, "class": "GAP_FILL_UNCERTAIN",
                                "level": str(lp), "note": "bar opened through the leg price"})
            for lvl in sorted(risk_levels):
                jumped_lvl = (o <= lvl < prev_close) if sgn_long else (prev_close < lvl <= o)
                if jumped_lvl:
                    out.append({"bar_ts": ts, "class": "GAP_FILL_UNCERTAIN",
                                "level": str(lvl), "note": "bar opened through a stop/BE level"})
        prev_close = c
    return out


def track(setup: dict, campaign: dict, bar_stream, constitution: dict,
          now_ts: int, provider_name: str) -> dict:
    """Full deterministic tracker snapshot for one campaign (both lanes)."""
    bars = bar_stream.ordered_tuples()
    sig = int(campaign["signal_ts"])
    bars = [b for b in bars if b[0] >= sig - (sig % 60)]
    lanes = {}
    for lane in ("LANE_A", "LANE_B"):
        res = run_lane(campaign, bars, lane, constitution)
        legs_obj = res.pop("_legs_obj")
        # MAE/MFE window = first fill .. campaign close (open campaigns run to data end)
        end_ts = None
        if res["campaign_state"] in ("CLOSED", "NO_FILL") and res["slices"]:
            end_ts = max(s["bar_ts"] for s in res["slices"])
        mae, mfe = mae_mfe(campaign["direction"], legs_obj, bars, end_ts)
        life = lifecycle_state(res, campaign, bars)
        lanes[lane] = {
            "engine": {k: res[k] for k in ("campaign_state", "realized_pips_per_unit",
                                            "unrealized_pips_per_unit", "average_entry",
                                            "legs", "slices", "follow_through", "paused_reason")},
            "lifecycle": life,
            "mae_pips": mae, "mfe_pips": mfe,
            "ambiguities": ambiguity_classifications(res) +
                           gap_classifications(campaign, bars, res["legs"]) +
                           [{"bar_ts": a.get("bar_ts"),
                             "class": ("FEED_SENSITIVE_NEAR_MISS" if "NEAR_MISS" in a.get("note", "")
                                       else "FEED_SENSITIVE_TOUCH"),
                             "note": a.get("note", "")} for a in res.get("ambiguities", [])],
            "plus50_diagnostic": plus50_diagnostic(campaign["direction"], legs_obj, bars),
        }
    last = bars[-1] if bars else None
    zone_lo, zone_hi = D(str(campaign["zone_low"])), D(str(campaign["zone_high"]))
    near = zone_hi if campaign["direction"] == "LONG" else zone_lo
    snapshot = {
        "schema": TRACKER_SCHEMA, "banner": BANNER,
        "setup_id": setup["setup_id"], "direction": campaign["direction"],
        "zone": f"{zone_lo}-{zone_hi}", "posted_stop": str(campaign["sl"]),
        "market": {
            "provider": provider_name,
            "last_bar_ts": last[0] if last else None,
            "last_close": str(last[4]) if last else None,
            "staleness_seconds": bar_stream.staleness_seconds(now_ts),
            "bars_seen": len(bars), "stream_hash": bar_stream.stream_hash(),
            "gaps": bar_stream.gaps(), "anomaly_count": len(bar_stream.anomalies),
            "distance_to_near_edge_pips": str(pips((last[4] - near) *
                                                   (D(1) if campaign["direction"] == "LONG" else D(-1))))
            if last else None,
        },
        "lanes": lanes,
        "headline_lane": "LANE_A",
        "lane_b_disclaimer": "POLICY_SENSITIVITY lane; NOT Farouk's actual result",
        "review_only": True, "executable": False, "trade_ready": False, "observation_only": True,
    }
    # logical hash covers ONLY deterministic state — never wall-clock staleness/receive
    # times, else every cycle re-appends (idempotency bug found in second-run regression)
    snapshot["logical_hash"] = sha256_obj(
        {"setup_id": snapshot["setup_id"], "lanes": lanes, "zone": snapshot["zone"],
         "posted_stop": snapshot["posted_stop"],
         "last_bar_ts": snapshot["market"]["last_bar_ts"],
         "stream_hash": snapshot["market"]["stream_hash"]})
    guards.assert_clean(snapshot, f"tracker snapshot {setup['setup_id']}")
    return snapshot
