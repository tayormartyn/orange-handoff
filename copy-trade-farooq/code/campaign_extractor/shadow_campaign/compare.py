"""
Shadow model comparison on IDENTICAL quote paths — passive ladders vs Qualified Strike & Trap, across
configurable residence / penetration / slippage / fill-assumption thresholds. SHADOW ONLY. A model is
NEVER declared superior merely because it deploys more risk.
"""
from __future__ import annotations

import sc_config as CFG
import strike_trap as ST
import passive_ladder as PL
import campaign as CAMP


def compare_models(*, direction, low, high, quote, quote_path, provider_ts_ms, now_ms,
                   quote_health_state, provider_stop, balance, slippage_points=None,
                   approval_latency_s=0, strike_outcome="FILLED", cfg=None):
    slip = CFG.MAX_STRIKE_SLIPPAGE_POINTS if slippage_points is None else slippage_points
    price = ST.exec_price(direction, quote)
    za = ST.zone_path_analysis(quote_path, direction, low, high)
    results = []

    for m in ("PASSIVE_EQUAL", "PASSIVE_50_30_20", "PASSIVE_60_25_15", "PASSIVE_70_20_10", "PASSIVE_FRONT_ONLY"):
        ladder = PL.passive_ladder(m, direction=direction, low=low, high=high, quote=quote,
                                   provider_stop=provider_stop, balance=balance)
        fill = PL.shadow_fill_on_path(ladder, quote_path, direction, low, high)
        risk = round(sum(t["reserved_risk"] for t in ladder["tranches"] if t["status"] == "PASSIVE_VALID"), 4)
        results.append({"model": m, "routing_mode": "PASSIVE", "front_edge_marketable": ladder["front_edge_marketable"],
                        "tranches_placed": fill["tranches_placed"], "tranches_filled": fill["tranches_filled"],
                        "total_risk_deployed": risk, "blockers": []})

    r = ST.route(direction=direction, low=low, high=high, quote=quote, quote_path=quote_path,
                 provider_ts_ms=provider_ts_ms, now_ms=now_ms, quote_health_state=quote_health_state,
                 approval_latency_s=approval_latency_s, cfg=cfg)
    st_row = {"model": "QUALIFIED_STRIKE_TRAP_60_25_15", "routing_mode": r["routing_mode"],
              "inside_zone_at_provider": None, "inside_zone_now": (low <= price <= high),
              "first_touch": za["first_touch"], "residence": None, "penetration": r.get("evidence", {}).get("penetration_ratio"),
              "first_traversal_verified": za["first_traversal"], "second_touch_blocked": za["second_touch"],
              "blockers": r["blockers"]}
    if r["routing_mode"] == CFG.INSIDE_ZONE_QUALIFIED_STRIKE_TRAP:
        camp = CAMP.run_shadow_campaign(direction=direction, low=low, high=high, quote=quote,
                                        provider_stop=provider_stop, balance=balance,
                                        slippage_points=slip, strike_outcome=strike_outcome)
        st_row.update({"strike_eligibility": True, "strike_result": camp["result"],
                       "strike_slippage_points": camp.get("strike", {}).get("SLIPPAGE_POINTS"),
                       "shadow_t1_risk": camp.get("actual_t1_risk"), "campaign_vwap": camp.get("vwap"),
                       "traps_placed": len(camp.get("placed_traps", [])),
                       "total_risk_deployed": (camp.get("ledger", {}) or {}).get("FULL_FILL_MAXIMUM_RISK"),
                       "atomic": camp.get("atomic")})
    else:
        st_row.update({"strike_eligibility": False, "total_risk_deployed": 0.0})
    results.append(st_row)

    return {"identical_quote_path": True, "quote_path_points": len(quote_path or []),
            "model_version": CFG.STRIKE_TRAP_MODEL_VERSION, "results": results,
            "note": "SHADOW ONLY. No model declared superior solely because it deploys more risk. "
                    "No broker execution; no atomic execution claim."}


def sweep_thresholds(*, direction, low, high, quote, quote_path, provider_ts_ms, now_ms,
                     quote_health_state, provider_stop, balance):
    """Shadow-sweep residence / penetration / slippage / fill-assumption grids (no production values)."""
    rows = []
    for res in CFG.RESIDENCE_GRID:
        for pen in CFG.PENETRATION_GRID:
            for slip in CFG.SLIPPAGE_GRID:
                for fa in CFG.FILL_ASSUMPTIONS:
                    cfg = {"MAX_INSIDE_ZONE_RESIDENCE_SECONDS": res, "MAX_STRIKE_PENETRATION_RATIO": pen}
                    r = ST.route(direction=direction, low=low, high=high, quote=quote, quote_path=quote_path,
                                 provider_ts_ms=provider_ts_ms, now_ms=now_ms,
                                 quote_health_state=quote_health_state, approval_latency_s=0, cfg=cfg)
                    rows.append({"residence_max": res, "penetration_max": pen, "slippage_ceiling": slip,
                                 "fill_assumption": fa, "routing_mode": r["routing_mode"],
                                 "blockers": r["blockers"]})
    return {"sweeps": rows, "note": "shadow evidence for later threshold selection — not production-fixed"}
