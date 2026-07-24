"""Causal top-down XAU reconstruction (RESEARCH-ONLY, deterministic).

For a given signal timestamp it builds D1/H4/H1/M15/M5/M1 context using ONLY completed bars
strictly before the signal (a forming HTF candle at the signal is excluded), reusing the existing
smc_features. It emits candidate zones (D1/H4/H1 OB+FVG), a fail-closed ranking (evidence orderings
only; numeric weights UNKNOWN), an Orange primary/alternative hypothesis, and a comparison vs a
published Farouk zone. It cannot touch the strict follower, lanes, outcomes, pre-marks, scorers,
Constitution, or live processes. Pepperstone is the only provider used.
"""
from __future__ import annotations

import csv
import os
import sys
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import smc_features as smc                                        # noqa: E402

PRICE = os.path.join(HERE, "..", "..", "..", "price_data")
D1_FILE = os.path.join(PRICE, "XAUUSD_1D_PEPPERSTONE_2022-11-13_to_2026-07-14_CANONICAL.csv")
M1_FILE = os.path.join(PRICE, "XAUUSD_1M_PEPPERSTONE_2026-07-08_to_2026-07-15_CANONICAL.csv")
UNKNOWN = smc.UNKNOWN
TF_SECONDS = {"M5": 300, "M15": 900, "H1": 3600, "H4": 14400}


def load_ohlc(path):
    out = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for r in csv.reader(fh):
            if not r or r[0] in ("time", ""):
                continue
            out.append((int(r[0]), D(r[1]), D(r[2]), D(r[3]), D(r[4])))
    out.sort()
    return out


def resample(m1, tf_seconds):
    """1m -> tf bars (UTC-floored buckets). Bar ts = bucket start; completed = start+tf <= last 1m end."""
    buckets = {}
    for t, o, h, l, c in m1:
        b = (t // tf_seconds) * tf_seconds
        if b not in buckets:
            buckets[b] = [o, h, l, c]
        else:
            x = buckets[b]
            x[1] = max(x[1], h); x[2] = min(x[2], l); x[3] = c
    return [(b, v[0], v[1], v[2], v[3]) for b, v in sorted(buckets.items())]


def completed_before(bars, signal_ts, tf_seconds):
    """Only bars whose CLOSE (start+tf) <= signal_ts — excludes the forming candle."""
    return [b for b in bars if b[0] + tf_seconds <= signal_ts]


def signal_price(m1, signal_ts):
    """Last COMPLETED 1m close before the signal (bar close = start+60 <= signal) — never the
    forming minute whose close is post-signal (red-team #1 fix)."""
    done = [b for b in m1 if b[0] + 60 <= signal_ts]
    return done[-1][4] if done else UNKNOWN


def zone_candidates(bars, signal_ts, tf_label):
    """ALL causal OB + FVG candidates from a timeframe (max_n=None: no recency truncation — red-team
    #4 fix), tagged with tf + a mitigation check (later pre-signal bar re-touched the zone?).
    NOTE: mitigation has NO age bound (threshold UNKNOWN) so in practice most older zones read
    mitigated — the caller must NOT treat 'fresh-first' as doing real work (red-team #8)."""
    obs = smc.candidate_order_blocks(bars, signal_ts, max_n=None)
    fvgs = smc.candidate_fvgs(bars, signal_ts, max_n=None)
    caus = [b for b in bars if b[0] < signal_ts]
    out = []

    def mitigated(lo, hi, after_ts):
        return any(after_ts < b[0] and not (b[3] > hi or b[2] < lo) for b in caus)

    for src, kind_key in ((obs, "kind"), (fvgs, "kind")):
        if src == UNKNOWN:
            continue
        for z in src:
            lo, hi = D(str(z["zone_low"] if "zone_low" in z else z["gap_low"])), \
                     D(str(z["zone_high"] if "zone_high" in z else z["gap_high"]))
            out.append({"tf": tf_label, "type": z[kind_key], "zone_low": str(min(lo, hi)),
                        "zone_high": str(max(lo, hi)), "at_ts": z["at_ts"],
                        "mitigated": mitigated(min(lo, hi), max(lo, hi), z["at_ts"]),
                        "body_basis": "origin-candle body (DR-204/VR-11)"})
    return out


def reconstruct(signal_ts, direction_hint_from_post):
    m1 = load_ohlc(M1_FILE)
    d1 = load_ohlc(D1_FILE)
    price = signal_price(m1, signal_ts)
    # causal per-tf bar sets
    tf_bars = {"D1": completed_before(d1, signal_ts, 86400), "M1": [b for b in m1 if b[0] < signal_ts]}
    for lbl, sec in TF_SECONDS.items():
        tf_bars[lbl] = completed_before(resample(m1, sec), signal_ts, sec)
    # causal history summary
    history = {lbl: {"bars": len(bs), "earliest": (bs[0][0] if bs else None),
                     "latest_close": (bs[-1][0] + (86400 if lbl == "D1" else TF_SECONDS.get(lbl, 60))
                                      if bs else None)}
               for lbl, bs in tf_bars.items()}
    # D1 context (native, completed)
    d1c = tf_bars["D1"]
    d1_bias = smc.htf_bias(d1c, signal_ts, ema_len=20) if len(d1c) >= 20 else {"htf_bias": UNKNOWN}
    d1_swings_h, d1_swings_l = smc.swing_points(d1c, signal_ts, lookback=2)
    d1_ctx = {
        "completed_daily_bars": len(d1c),
        "last_completed_daily": ({"ts": d1c[-1][0], "o": str(d1c[-1][1]), "h": str(d1c[-1][2]),
                                  "l": str(d1c[-1][3]), "c": str(d1c[-1][4])} if d1c else UNKNOWN),
        "recent_swing_highs": [(t, str(p)) for t, p in d1_swings_h[-3:]] or UNKNOWN,
        "recent_swing_lows": [(t, str(p)) for t, p in d1_swings_l[-3:]] or UNKNOWN,
        "directional_bias": d1_bias.get("htf_bias", UNKNOWN),
        "external_liquidity": {"prior_daily_high": str(max((b[2] for b in d1c[-10:]), default=UNKNOWN))
                               if d1c else UNKNOWN,
                               "prior_daily_low": str(min((b[3] for b in d1c[-10:]), default=UNKNOWN))
                               if d1c else UNKNOWN},
        "premium_discount": UNKNOWN,   # needs a defined dealing range; not evidence-fixed -> fail closed
        "daily_ob_fvg": zone_candidates(d1c, signal_ts, "D1"),
        "unknowns": ["premium/discount dealing-range definition", "daily mitigation-age threshold"],
    }
    # H4 / H1 candidates
    h4 = zone_candidates(tf_bars["H4"], signal_ts, "H4")
    h1 = zone_candidates(tf_bars["H1"], signal_ts, "H1")
    h1_choch = smc.latest_choch_bos(tf_bars["H1"], signal_ts)
    h1_sweeps = smc.latest_sweeps(tf_bars["H1"], signal_ts)
    asia = smc.asia_high_low(tf_bars["M15"], signal_ts)
    # candidate register (D1+H4+H1) — FULL causal universe (no recency truncation)
    universe = d1_ctx["daily_ob_fvg"] + h4 + h1
    universe_total = len(universe)
    frac_mitigated = round(sum(1 for z in universe if z["mitigated"]) / max(universe_total, 1), 3)
    for z in universe:
        lo, hi = D(z["zone_low"]), D(z["zone_high"])
        if price != UNKNOWN:
            if price > hi:
                z["price_relation"] = "ABOVE"; z["distance_pips"] = str((price - hi) * 10)
            elif price < lo:
                z["price_relation"] = "BELOW"; z["distance_pips"] = str((lo - price) * 10)
            else:
                z["price_relation"] = "INSIDE"; z["distance_pips"] = "0"
        else:
            z["price_relation"] = UNKNOWN; z["distance_pips"] = UNKNOWN
    # RANKING — HONEST: mitigation is an ANNOTATION only (no age threshold => fresh-first is
    # meaningless: the sole 'fresh' zones are ancient far-away levels, e.g. a 2554 OB never revisited).
    # The only defensible, non-fabricated ordering is NEAREST-TO-SIGNAL-PRICE. This is explicitly weak
    # corroboration: Farouk signals when spot is already at his zone, so the nearest zone is near his
    # zone by construction (red-team #8).
    def rank_key(z):
        return abs(float(z["distance_pips"])) if z["distance_pips"] not in (UNKNOWN,) else 9e9
    ranked = sorted(universe, key=rank_key)
    primary = ranked[0] if ranked else UNKNOWN
    return {
        "signal_ts": signal_ts, "signal_price": str(price) if price != UNKNOWN else UNKNOWN,
        "causal_history": history, "d1_context": d1_ctx,
        "h4_candidates": h4, "h1_candidates": h1,
        "h1_choch_bos": h1_choch, "h1_sweeps": h1_sweeps, "m15_asia": asia,
        "candidate_universe_total": universe_total, "fraction_mitigated": frac_mitigated,
        "candidate_register_nearest15": ranked[:15],
        "orange_primary_zone": primary,
        "orange_alternative_zones": ranked[1:6],
        "ranking_basis": "NEAREST-TO-SIGNAL-PRICE only. Mitigation is annotation, NOT a ranking key "
                         "(age-threshold UNKNOWN => fresh-first surfaces only ancient far zones). "
                         "Confluence weights UNKNOWN -> not scored. This ordering is WEAK corroboration "
                         "(spot is at the zone when Farouk signals, so nearest~=published by construction).",
        "ranking_is_nearest_to_price_only": True,
        "rules_used": ["DR-204 (OB/sweep)", "DR-201 (FVG)", "VR-11 (body-anchored)", "VR-15 (fresh>mitigated)",
                       "DR-502 (HTF>LTF)"],
        "unknowns": ["ranking weights", "premium/discount range", "exact zone-boundary discretion",
                     "mitigation-age threshold", "A-grade formula"],
        "review_only": True, "executable": False, "trade_ready": False, "observation_only": True,
    }


def compare_published(recon, direction, zlo, zhi):
    p = recon["orange_primary_zone"]
    if p == UNKNOWN:
        return {"verdict": "INSUFFICIENT_EVIDENCE"}
    plo, phi = D(p["zone_low"]), D(p["zone_high"])
    zlo, zhi = D(str(zlo)), D(str(zhi))
    overlap = max(D(0), min(phi, zhi) - max(plo, zlo))
    reg = recon["candidate_register_nearest15"]
    # nearest ANY candidate to the published zone
    def near(z):
        a, b = D(z["zone_low"]), D(z["zone_high"])
        if b < zlo:
            return (zlo - b)
        if a > zhi:
            return (a - zhi)
        return D(0)
    nearest = min(reg, key=near) if reg else UNKNOWN
    nd = near(nearest) if nearest != UNKNOWN else UNKNOWN
    verdict = ("MATCH" if overlap > 0 and abs(phi - zhi) < D(5) and abs(plo - zlo) < D(5)
               else "PARTIAL_MATCH" if overlap > 0
               else "NEAR" if nd != UNKNOWN and nd <= D(20)
               else "DISJOINT")
    return {"published_zone": f"{zlo}-{zhi}", "published_direction": direction,
            "orange_primary": f"{p['zone_low']}-{p['zone_high']} ({p['tf']} {p['type']})",
            "primary_overlap_usd": str(overlap),
            "nearest_candidate_to_published": (f"{nearest['zone_low']}-{nearest['zone_high']} "
                                               f"({nearest['tf']} {nearest['type']})" if nearest != UNKNOWN else UNKNOWN),
            "nearest_distance_pips": str(nd * 10) if nd != UNKNOWN else UNKNOWN,
            "primary_zone_overlap_verdict": verdict,
            "direction_agreement": "N/A — the engine emits zones, not a directional call; do NOT read "
                                   "the primary zone's OB/FVG polarity as a direction (F001 primary is a "
                                   "BEARISH_FVG yet the trade is LONG). Any 'direction-consistent' narrative "
                                   "is post-hoc, not an engine output.",
            "match_caveat": "the signal price is at/inside the published zone (Farouk signals when spot is "
                            "already at his zone), and the ranking is degenerate NEAREST-TO-PRICE "
                            "(fresh-first inert, all candidates mitigated). So a nearest-zone overlap with "
                            "the published zone is largely BUILT-IN, NOT strong independent corroboration.",
            "information_orange_lacked": ["Farouk's private fills/personal stop", "his zone-ranking weights",
                                          "mitigation-age threshold", "intrabar order",
                                          "any post-signal data (excluded by firewall)"]}


if __name__ == "__main__":
    import io, json
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    F001 = int(__import__("datetime").datetime(2026, 7, 14, 8, 38, 6,
               tzinfo=__import__("datetime").timezone.utc).timestamp())
    F002 = int(__import__("datetime").datetime(2026, 7, 14, 13, 26, 21,
               tzinfo=__import__("datetime").timezone.utc).timestamp())
    for name, sig, direction, zlo, zhi in [("XAU-F001", F001, "LONG", 4007, 4019),
                                           ("XAU-F002", F002, "SHORT", 4084, 4094)]:
        r = reconstruct(sig, direction)
        cmp_ = compare_published(r, direction, zlo, zhi)
        print(f"\n===== {name} (signal price {r['signal_price']}) =====")
        print("causal history:", {k: v["bars"] for k, v in r["causal_history"].items()})
        print("D1 bias:", r["d1_context"]["directional_bias"], "| daily bars:", r["d1_context"]["completed_daily_bars"])
        print("H1 CHoCH/BOS:", r["h1_choch_bos"]["latest_choch_bos"])
        print("Asia H/L:", r["m15_asia"])
        print(f"candidate universe: {r['candidate_universe_total']} | frac_mitigated {r['fraction_mitigated']} "
              f"| ranking=nearest-to-price-only")
        print("  primary:", (f"{r['orange_primary_zone']['tf']} {r['orange_primary_zone']['type']} "
                             f"{r['orange_primary_zone']['zone_low']}-{r['orange_primary_zone']['zone_high']} "
                             f"mitig={r['orange_primary_zone']['mitigated']}" if r['orange_primary_zone'] != UNKNOWN else "UNKNOWN"))
        print("comparison:", json.dumps(cmp_, ensure_ascii=False))
