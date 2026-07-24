"""
Qualified Strike & Trap — SHADOW-ONLY analytical model (v1.0.0). Deterministic. It NEVER enables,
constructs or transmits a broker order/amend/close/cancel, issues a permit/lease, or claims atomic
execution. It models an inside-zone execution routing decision and the shadow strike/trap sequence so
different thresholds can be compared on identical quote paths.

Executable price side: BUY -> current ASK, SELL -> current BID (used consistently). Midpoint is only
ever labelled analytics — never an execution decision.
"""
from __future__ import annotations

import sc_config as CFG

# ---- states (append-only / irreversible where appropriate) ----
STATES = ("INSIDE_ZONE_DETECTED", "INSIDE_ZONE_QUALIFICATION_PENDING", "INSIDE_ZONE_QUALIFIED",
          "INSIDE_ZONE_BLOCKED", "FIRST_TOUCH_LATCHED", "STRIKE_APPROVAL_PENDING", "STRIKE_SHADOW_SENT",
          "STRIKE_SHADOW_FILLED", "STRIKE_SHADOW_PARTIAL_FILL", "STRIKE_SHADOW_REJECTED",
          "STRIKE_RECONCILIATION_REQUIRED", "STRIKE_FILLED_PROTECTION_PENDING",
          "STRIKE_PROVISIONALLY_PROTECTED", "EXACT_STOP_AMEND_PENDING", "EXACT_STOP_CONFIRMED",
          "PROTECTION_FAILED", "TRAPS_CALCULATED", "TRAPS_ARMED_SHADOW", "TRAP_PARTIALLY_FILLED_SHADOW",
          "ALL_TRANCHES_FILLED_SHADOW", "PROFIT_SIDE_EXIT", "UNFILLED_TRAPS_CANCELLED",
          "SECOND_TOUCH_BLOCKED", "CAMPAIGN_COMPLETED_SHADOW", "CAMPAIGN_ABORTED")


def exec_price(direction, quote):
    """The executable quote side. BUY buys at the ASK; SELL sells at the BID. Never midpoint."""
    return quote["ask"] if direction.upper() == "BUY" else quote["bid"]


def midpoint(quote):
    return round((quote["bid"] + quote["ask"]) / 2, 5)     # LABELLED ANALYTICS ONLY


def penetration_ratio(direction, low, high, price):
    """How deep the executable price has entered from the FRONT (entry) edge, normalised by zone width.
    SELL front edge = low (price rises into the zone); BUY front edge = high (price falls into it)."""
    width = high - low
    if width <= 0:
        return None
    if direction.upper() == "SELL":
        return round(max(0.0, min(1.0, (price - low) / width)), 4)
    return round(max(0.0, min(1.0, (high - price) / width)), 4)


def _region(direction, price, low, high):
    """inside / stop / profit for the executable price. SELL: stop is ABOVE, profit BELOW. BUY: stop
    BELOW, profit ABOVE."""
    if low <= price <= high:
        return "inside"
    d = direction.upper()
    if d == "SELL":
        return "stop" if price > high else "profit"
    return "stop" if price < low else "profit"


def zone_path_analysis(quote_path, direction, low, high):
    """Deterministic traversal analysis over the executable-side price of the quote path."""
    pts = sorted([q for q in (quote_path or [])
                  if q.get("ts_ms") is not None and exec_price(direction, q) is not None],
                 key=lambda q: q["ts_ms"])
    regions = [_region(direction, exec_price(direction, q), low, high) for q in pts]
    inside_idx = [i for i, r in enumerate(regions) if r == "inside"]
    touched = bool(inside_idx)
    # contiguous inside runs
    runs = 0
    prev = None
    for r in regions:
        if r == "inside" and prev != "inside":
            runs += 1
        prev = r
    currently_inside = bool(regions) and regions[-1] == "inside"
    stop_breached = "stop" in regions
    # first exit side after the first inside run
    first_exit_side = None
    if inside_idx:
        for r in regions[inside_idx[0] + 1:]:
            if r != "inside":
                first_exit_side = r
                break
    profit_exited = first_exit_side == "profit"
    traversed = ("profit" in regions) and ("stop" in regions)
    second_touch = runs > 1
    first_traversal = currently_inside and runs == 1
    first_touch = None
    if inside_idx:
        q = pts[inside_idx[0]]
        first_touch = {"ts_ms": q["ts_ms"], "bid": q["bid"], "ask": q["ask"],
                       "exec_price": exec_price(direction, q),
                       "penetration": penetration_ratio(direction, low, high, exec_price(direction, q))}
    return {"touched": touched, "currently_inside": currently_inside, "inside_run_count": runs,
            "stop_breached": stop_breached, "profit_exited": profit_exited, "traversed": traversed,
            "second_touch": second_touch, "first_traversal": first_traversal, "first_touch": first_touch,
            "points": len(pts)}


def quote_path_coverage_ok(quote_path, provider_ts_ms, now_ms, max_gap_s=None):
    max_gap = (CFG.MAX_QUOTE_GAP_SECONDS if max_gap_s is None else max_gap_s) * 1000
    pts = sorted([q for q in (quote_path or []) if q.get("ts_ms") is not None], key=lambda q: q["ts_ms"])
    if len(pts) < 2:
        return False, "ISOLATED_OR_NO_QUOTES"
    gaps = [pts[i + 1]["ts_ms"] - pts[i]["ts_ms"] for i in range(len(pts) - 1)]
    lead = pts[0]["ts_ms"] - (provider_ts_ms or pts[0]["ts_ms"])
    tail = (now_ms or pts[-1]["ts_ms"]) - pts[-1]["ts_ms"]
    if max(gaps) > max_gap or lead > max_gap or tail > max_gap:
        return False, "QUOTE_PATH_UNVERIFIED"
    return True, None


def first_touch_latch(quote_path, direction, low, high, provider_ts_ms):
    """Establish the FIRST touch from quote history even before approval. Irreversible zone_consumed."""
    za = zone_path_analysis(quote_path, direction, low, high)
    ft = za["first_touch"]
    if not ft:
        return None
    return {"event": "FIRST_TOUCH_LATCHED", "first_touch_ts_ms": ft["ts_ms"], "bid": ft["bid"],
            "ask": ft["ask"], "executable_side_price": ft["exec_price"],
            "zone_penetration_at_first_touch": ft["penetration"],
            "provider_message_age_at_touch_s": (round((ft["ts_ms"] - provider_ts_ms) / 1000.0, 1)
                                                if provider_ts_ms is not None else None),
            "campaign_generation": 1, "zone_consumed": True}


# ---- Market-Range strike (shadow) ----
def strike_shadow(direction, quote, *, slippage_points, requested_price=None, shadow_fill_offset=None):
    """Model a Market-Range strike. Returns requested/best/worst allowed fill, a shadow fill, slippage,
    and a rejection flag. A Market-Range strike may be filled / partially / rejected / uncertain — this
    NEVER assumes a full fill."""
    d = direction.upper()
    base = exec_price(direction, quote)
    req = requested_price if requested_price is not None else base
    slip = slippage_points * CFG.POINT
    if d == "BUY":                              # buying: worse = higher fill
        best, worst = req, round(req + slip, 5)
    else:                                       # selling: worse = lower fill
        best, worst = req, round(req - slip, 5)
    # a deterministic shadow fill somewhere in [best, worst] (default = worst = conservative)
    fill = worst if shadow_fill_offset is None else (
        round(req + shadow_fill_offset * CFG.POINT, 5) if d == "BUY" else round(req - shadow_fill_offset * CFG.POINT, 5))
    outside = (fill > worst) if d == "BUY" else (fill < worst)
    slip_pts = round(abs(fill - req) / CFG.POINT, 1)
    return {"STRIKE_REQUESTED_PRICE": req, "BEST_ALLOWED_FILL": best, "WORST_ALLOWED_FILL": worst,
            "SHADOW_FILL_PRICE": (None if outside else fill), "SLIPPAGE_POINTS": slip_pts,
            "REJECTED_OUTSIDE_RANGE": bool(outside), "slippage_ceiling_points": slippage_points,
            "execution_state": "REJECTED_OUTSIDE_RANGE" if outside else "SHADOW_FILL_UNCERTAIN"}


def worst_fill_price(direction, quote, slippage_points):
    return strike_shadow(direction, quote, slippage_points=slippage_points)["WORST_ALLOWED_FILL"]


# ---- worst-fill risk sizing ----
def _risk(distance, lots):
    return round(abs(distance) * lots * CFG.CONTRACT_OZ_PER_LOT, 4)


def size_worst_fill_risk(direction, *, quote, provider_stop, balance, slippage_points,
                         cost_allowance=0.0, total_risk_pct=None):
    """T1 volume from the WORST permitted fill (greatest distance to the shared stop). Enforces
    T1 worst-fill risk + T1 cost <= 60% of total, reserves T2/T3, full campaign <= the canonical
    campaign cap (risk_policy v2.0.0 = 1.0%)."""
    total_pct = CFG.TOTAL_CAMPAIGN_RISK_PCT if total_risk_pct is None else total_pct if False else total_risk_pct
    total_budget = round(balance * total_pct, 4)
    strike_budget = round(total_budget * CFG.STRIKE_ALLOC, 4)
    worst = worst_fill_price(direction, quote, slippage_points)
    dist = abs(worst - provider_stop)                       # worst-fill distance to the shared stop
    if dist <= 0:
        return {"ok": False, "reason": "STRIKE_RISK_NORMALIZATION_FAILED", "worst_fill": worst}
    # largest step-valid lot whose worst-fill risk + cost <= strike budget (round DOWN)
    max_lots_by_risk = (strike_budget - cost_allowance) / (dist * CFG.CONTRACT_OZ_PER_LOT)
    lots = (int(max_lots_by_risk / CFG.LOT_STEP)) * CFG.LOT_STEP
    lots = round(lots, 2)
    if lots < CFG.MIN_LOT:
        return {"ok": False, "reason": "STRIKE_RISK_NORMALIZATION_FAILED", "worst_fill": worst,
                "strike_budget": strike_budget}
    t1_worst_risk = _risk(dist, lots)
    return {"ok": True, "worst_fill": worst, "t1_lots": lots, "t1_worst_fill_risk": t1_worst_risk,
            "t1_cost_allowance": cost_allowance, "strike_budget": strike_budget,
            "total_budget": total_budget, "worst_fill_distance": round(dist, 5),
            "within_60pct": t1_worst_risk + cost_allowance <= strike_budget + 1e-9}


# ---- provisional relative stop (never looser than provider absolute stop) ----
def provisional_stop(direction, *, best_fill, worst_fill, provider_stop):
    """A conservative RELATIVE stop valid across the permitted fill range: distance from the fill to the
    provider absolute stop, taken at the fill bound that gives the LARGEST (loosest) raw distance — then
    the provisional stop price at each fill bound is at most as far as the provider stop (never looser)."""
    d = direction.upper()
    # relative distance measured from the WORST fill (closest to stop for a losing move) keeps it tight
    if d == "BUY":                              # stop below; worst fill = highest => nearest to stop below
        rel = min(abs(best_fill - provider_stop), abs(worst_fill - provider_stop))
        stop_at_best = round(best_fill - rel, 5)
        stop_at_worst = round(worst_fill - rel, 5)
        tighter = stop_at_best >= provider_stop and stop_at_worst >= provider_stop
    else:                                       # SELL: stop above
        rel = min(abs(best_fill - provider_stop), abs(worst_fill - provider_stop))
        stop_at_best = round(best_fill + rel, 5)
        stop_at_worst = round(worst_fill + rel, 5)
        tighter = stop_at_best <= provider_stop and stop_at_worst <= provider_stop
    if rel <= 0:
        return {"ok": False, "reason": "STRIKE_PROTECTION_UNAVAILABLE"}
    return {"ok": True, "provisional_stop_distance": round(rel, 5), "stop_at_best_fill": stop_at_best,
            "stop_at_worst_fill": stop_at_worst, "provider_absolute_stop": provider_stop,
            "provisional_tighter_or_equal": tighter, "exact_post_fill_amendment_required": True}


# ---- qualification ----
def qualify(*, direction, low, high, quote, quote_path, provider_ts_ms, now_ms, quote_health_state,
            approval_latency_s, first_touch_consumed_elsewhere=False, duplicate=False, conflicting=False,
            residence_seconds=None, cfg=None):
    """Returns (eligible, blockers, evidence). Fail-closed."""
    c = cfg or {}
    def g(k, d):
        return c.get(k, d)
    blockers = []
    ev = {}
    price = exec_price(direction, quote)
    ev["executable_price"] = price
    ev["midpoint_analytics_only"] = midpoint(quote)

    if provider_ts_ms is None:
        blockers.append("PROVIDER_TIMESTAMP_UNVERIFIED")
    elif (now_ms - provider_ts_ms) / 1000.0 > g("FRESH_SIGNAL_TTL_SECONDS", CFG.FRESH_SIGNAL_TTL_SECONDS):
        blockers.append("SIGNAL_TTL_EXCEEDED")
    if quote_health_state != "QUOTES_ACTIVE":
        blockers.append("QUOTE_HEALTH_NOT_ACTIVE")
    cov_ok, cov_reason = quote_path_coverage_ok(quote_path, provider_ts_ms, now_ms,
                                                max_gap_s=g("MAX_QUOTE_GAP_SECONDS", CFG.MAX_QUOTE_GAP_SECONDS))
    if not cov_ok:
        blockers.append("QUOTE_PATH_UNVERIFIED")

    za = zone_path_analysis(quote_path, direction, low, high)
    ev["traversal"] = za
    if not (low <= price <= high):
        blockers.append("NOT_INSIDE_ZONE")
    if not za["first_traversal"]:
        blockers.append("INSIDE_ZONE_NOT_FIRST_TRAVERSAL")
    if za["second_touch"]:
        blockers.append("SECOND_TOUCH_BLOCKED")
    if za["profit_exited"]:
        blockers.append("ZONE_ALREADY_EXITED")
    if za["traversed"]:
        blockers.append("ZONE_ALREADY_TRAVERSED")
    if za["stop_breached"]:
        blockers.append("STOP_SIDE_BREACHED")
    if first_touch_consumed_elsewhere:
        blockers.append("INSIDE_ZONE_NOT_FIRST_TRAVERSAL")
    if duplicate:
        blockers.append("CAMPAIGN_DUPLICATED")
    if conflicting:
        blockers.append("CONFLICTING_INSTRUCTION")

    spread = quote["ask"] - quote["bid"]
    ev["spread"] = round(spread, 3)
    if spread > g("MAX_STRIKE_SPREAD", CFG.MAX_STRIKE_SPREAD):
        blockers.append("STRIKE_SPREAD_EXCEEDED")
    if now_ms - quote["ts_ms"] > CFG.QUOTE_STALE_MS if hasattr(CFG, "QUOTE_STALE_MS") else False:
        blockers.append("QUOTE_STALE")
    if approval_latency_s is not None and approval_latency_s > g("MAX_APPROVAL_LATENCY_SECONDS", CFG.MAX_APPROVAL_LATENCY_SECONDS):
        blockers.append("APPROVAL_LATENCY_EXCEEDED")
    pen = penetration_ratio(direction, low, high, price)
    ev["penetration_ratio"] = pen
    if pen is not None and pen > g("MAX_STRIKE_PENETRATION_RATIO", CFG.MAX_STRIKE_PENETRATION_RATIO):
        blockers.append("STRIKE_PENETRATION_EXCEEDED")
    if residence_seconds is not None and residence_seconds > g("MAX_INSIDE_ZONE_RESIDENCE_SECONDS", CFG.MAX_INSIDE_ZONE_RESIDENCE_SECONDS):
        blockers.append("INSIDE_ZONE_RESIDENCE_EXCEEDED")

    blockers = sorted(set(blockers))
    return (not blockers), blockers, ev


def route(*, direction, low, high, quote, quote_path, provider_ts_ms, now_ms, quote_health_state,
          approval_latency_s=0, cfg=None, **qual):
    """Deterministic routing: PRE_TOUCH_PASSIVE_LADDER / INSIDE_ZONE_QUALIFIED_STRIKE_TRAP /
    INSIDE_ZONE_BLOCKED / ZONE_CONSUMED."""
    price = exec_price(direction, quote)
    za = zone_path_analysis(quote_path, direction, low, high)
    if not za["touched"] and not (low <= price <= high):
        return {"routing_mode": CFG.PRE_TOUCH_PASSIVE_LADDER, "blockers": [], "traversal": za}
    if za["second_touch"] or (za["touched"] and not za["currently_inside"] and (za["profit_exited"] or za["traversed"] or za["stop_breached"])):
        return {"routing_mode": CFG.ZONE_CONSUMED, "blockers": ["SECOND_TOUCH_BLOCKED"], "traversal": za}
    eligible, blockers, ev = qualify(direction=direction, low=low, high=high, quote=quote,
                                     quote_path=quote_path, provider_ts_ms=provider_ts_ms, now_ms=now_ms,
                                     quote_health_state=quote_health_state,
                                     approval_latency_s=approval_latency_s, cfg=cfg, **qual)
    if eligible:
        return {"routing_mode": CFG.INSIDE_ZONE_QUALIFIED_STRIKE_TRAP, "blockers": [], "evidence": ev,
                "traversal": za}
    return {"routing_mode": CFG.INSIDE_ZONE_BLOCKED, "blockers": blockers,
            "human_review_required": True, "no_campaign_action": True, "evidence": ev, "traversal": za}


# ---- passive trap tranches (T2/T3) ----
def passive_traps(*, direction, low, high, quote, remaining_risk, provider_stop, balance):
    """T2 (25%) and T3 (15%) placed DEEPER in the zone; must be genuinely passive at construction."""
    d = direction.upper()
    price = exec_price(direction, quote)
    total_budget = balance * CFG.TOTAL_CAMPAIGN_RISK_PCT
    out = []
    # deeper toward the far (stop-side) boundary
    if d == "BUY":                              # buy limits BELOW current market, deeper = lower
        t2_level, t3_level = round(low + (high - low) * 0.33, 2), round(low + (high - low) * 0.10, 2)
        passive2, passive3 = t2_level < price, t3_level < price
    else:                                       # sell limits ABOVE current market, deeper = higher
        t2_level, t3_level = round(low + (high - low) * 0.67, 2), round(low + (high - low) * 0.90, 2)
        passive2, passive3 = t2_level > price, t3_level > price
    for tag, level, alloc, passive in (("T2", t2_level, CFG.TRAP_T2_ALLOC, passive2),
                                       ("T3", t3_level, CFG.TRAP_T3_ALLOC, passive3)):
        inside = low <= level <= high
        budget = round(total_budget * alloc, 4)
        dist = abs(level - provider_stop)
        lots = round((int((budget / (dist * CFG.CONTRACT_OZ_PER_LOT)) / CFG.LOT_STEP)) * CFG.LOT_STEP, 2) if dist > 0 else 0
        if not passive:
            out.append({"tag": tag, "level": level, "status": "TRAP_LEVEL_NO_LONGER_PASSIVE",
                        "do_not_place_child": True, "released_risk": budget})
        elif not inside:
            out.append({"tag": tag, "level": level, "status": "TRAP_OUTSIDE_ZONE", "do_not_place_child": True,
                        "released_risk": budget})
        elif lots < CFG.MIN_LOT:
            out.append({"tag": tag, "level": level, "status": "TRAP_RISK_TOO_SMALL", "do_not_place_child": True,
                        "released_risk": budget})
        else:
            out.append({"tag": tag, "level": level, "lots": lots, "reserved_risk": round(_risk(dist, lots), 4),
                        "status": "PASSIVE_VALID", "inside_zone": True,
                        "child_id": f"trap-{direction}-{tag}-{int(level * 100)}",
                        "uses_shared_stop": provider_stop})
    return out


# ---- risk ledger ----
def risk_ledger(*, balance, strike_actual_risk=0.0, trap_reserved=0.0, trap_consumed=0.0,
                released=0.0, cost_allowance=0.0, strike_target=None, strike_worst=None):
    total = round(balance * CFG.TOTAL_CAMPAIGN_RISK_PCT, 4)
    consumed = strike_actual_risk + trap_consumed + cost_allowance
    available = round(total - strike_actual_risk - trap_reserved - cost_allowance + released, 4)
    return {"TOTAL_CAMPAIGN_RISK": total, "STRIKE_TARGET_RISK": strike_target,
            "STRIKE_WORST_FILL_RISK": strike_worst, "STRIKE_ACTUAL_CONSUMED_RISK": strike_actual_risk,
            "TRAP_RESERVED_RISK": trap_reserved, "TRAP_CONSUMED_RISK": trap_consumed,
            "RELEASED_RISK": released, "AVAILABLE_RISK": available, "COST_ALLOWANCE": cost_allowance,
            "FULL_FILL_MAXIMUM_RISK": round(consumed + trap_reserved, 4),
            "within_full_cap": round(consumed + trap_reserved, 4) <= total + 1e-9,
            "unrealised_profit_adds_capacity": False}


def profit_side_exit(traps):
    """T1 filled, price exits profit-side before traps fill: cancel unfilled traps, release their risk,
    preserve T1, mark zone consumed permanently. No momentum add-on."""
    released = round(sum(t.get("reserved_risk", 0.0) for t in traps if t.get("status") == "PASSIVE_VALID"), 4)
    return {"event": "PROFIT_SIDE_EXIT", "cancelled_unfilled_traps": [t.get("tag") for t in traps],
            "released_risk": released, "t1_preserved": True, "zone_consumed": True,
            "re_entry_blocked": True, "momentum_add_on_permitted": False}
