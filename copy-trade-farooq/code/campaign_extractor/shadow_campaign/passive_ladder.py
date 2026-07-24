"""
Original PASSIVE front-edge limit-ladder models (preserved for shadow comparison). SHADOW ONLY. A
passive limit must stay on the non-marketable side; an already-passed front-edge level is flagged and
never submitted as a fake pending order (and never converted to a market order).
"""
from __future__ import annotations

import sc_config as CFG

MODEL_ALLOCS = {
    "PASSIVE_EQUAL": (1 / 3, 1 / 3, 1 / 3),
    "PASSIVE_50_30_20": (0.50, 0.30, 0.20),
    "PASSIVE_60_25_15": (0.60, 0.25, 0.15),
    "PASSIVE_70_20_10": (0.70, 0.20, 0.10),
    "PASSIVE_FRONT_ONLY": (1.0, 0.0, 0.0),
}


def _risk(dist, lots):
    return round(abs(dist) * lots * CFG.CONTRACT_OZ_PER_LOT, 4)


def passive_ladder(model, *, direction, low, high, quote, provider_stop, balance):
    """Three passive limits front->deep. Front tranche nearest the market edge. Marketable levels are
    flagged NOT-PASSIVE and never placed."""
    allocs = MODEL_ALLOCS[model]
    d = direction.upper()
    total_budget = balance * CFG.TOTAL_CAMPAIGN_RISK_PCT
    price = quote["ask"] if d == "BUY" else quote["bid"]
    width = high - low
    if d == "BUY":                    # buy limits BELOW market; front = high edge, deep = low edge
        levels = [round(high, 2), round(low + width * 0.5, 2), round(low, 2)]
        passive = [lv < price for lv in levels]
    else:                             # sell limits ABOVE market; front = low edge, deep = high edge
        levels = [round(low, 2), round(low + width * 0.5, 2), round(high, 2)]
        passive = [lv > price for lv in levels]
    tranches = []
    for i, (lv, al, pv) in enumerate(zip(levels, allocs, passive)):
        if al <= 0:
            continue
        budget = round(total_budget * al, 4)
        dist = abs(lv - provider_stop)
        lots = round((int((budget / (dist * CFG.CONTRACT_OZ_PER_LOT)) / CFG.LOT_STEP)) * CFG.LOT_STEP, 2) if dist > 0 else 0
        tranches.append({"tag": f"T{i+1}", "level": lv, "alloc": al, "lots": lots,
                         "reserved_risk": _risk(dist, lots) if lots >= CFG.MIN_LOT else 0.0,
                         "passive": pv,
                         "status": "PASSIVE_VALID" if (pv and lots >= CFG.MIN_LOT) else "NOT_PLACED_NOT_PASSIVE",
                         "marketable_would_cross": (not pv)})
    return {"model": model, "direction": direction, "tranches": tranches,
            "front_edge_marketable": (not passive[0]),
            "note": "SHADOW ONLY — a passed front-edge limit is never submitted; never market-converted."}


def shadow_fill_on_path(ladder, quote_path, direction, low, high):
    """Given a quote path, which passive tranches would fill (price reached the level on the exec side)."""
    from strike_trap import exec_price
    filled = 0
    for t in ladder["tranches"]:
        if t["status"] != "PASSIVE_VALID":
            continue
        lv = t["level"]
        hit = any((exec_price(direction, q) <= lv if direction.upper() == "BUY" else exec_price(direction, q) >= lv)
                  for q in quote_path)
        if hit:
            filled += 1
    return {"tranches_filled": filled, "tranches_placed": sum(1 for t in ladder["tranches"] if t["status"] == "PASSIVE_VALID")}
