"""Two offline/replay-only documented detectors (RESEARCH-ONLY). Completed candles only; no
forming candle; no future bar; no execution. Emit a documented-sequence match with evidence and
UNKNOWN where a threshold is undocumented. NOT wired to anything live.
"""
from __future__ import annotations

import os
import sys
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import detector_features as F                                    # noqa: E402

UNKNOWN = "UNKNOWN"


def _load(path):
    import csv
    out = []
    for r in csv.reader(open(path, encoding="utf-8-sig")):
        if not r or r[0] in ("time", ""):
            continue
        out.append((int(r[0]), D(r[1]), D(r[2]), D(r[3]), D(r[4])))
    out.sort()
    return out


def detect_fvg_continuation_5m(m1, up_to_ts=None):
    """DR-202: bottoming -> bullish 5m FVG -> body close above -> retrace into FVG -> bullish
    completed confirmation -> (target next bearish OB). Bearish mirror: NOT emitted (documentary
    evidence is bullish-only in DR-202 -> UNKNOWN, per spec)."""
    if up_to_ts:
        m1 = [b for b in m1 if b[0] + 60 <= up_to_ts]
    bars5 = F.resample_1m(m1, 300)
    if len(bars5) < 6:
        return []
    obs = F.order_blocks(bars5)
    matches = []
    fs = F.fvgs(bars5)
    idx = {b[0]: i for i, b in enumerate(bars5)}
    for fv in fs:
        if fv["kind"] != "BULLISH_FVG":
            continue
        fi = idx.get(fv["at"])
        if fi is None or fi + 1 >= len(bars5):
            continue
        # BODY close above the FVG on a subsequent bar
        conf_i = next((j for j in range(fi + 1, len(bars5)) if bars5[j][4] > fv["high"]), None)
        if conf_i is None:
            continue
        # retracement back INTO the FVG after the close-above
        retr_i = next((j for j in range(conf_i + 1, len(bars5))
                       if bars5[j][3] <= fv["high"] and bars5[j][3] >= fv["low"]), None)
        if retr_i is None or retr_i + 1 >= len(bars5):
            continue
        # bullish completed confirmation candle at/after retrace
        conf2 = next((bars5[j] for j in range(retr_i, len(bars5))
                      if F.hammer_or_star(bars5[j]) == "HAMMER" or bars5[j][4] > bars5[j][1]), None)
        if conf2 is None:
            continue
        tgt = next((o for o in obs if o["kind"] == "BEARISH_OB" and o["at"] > fv["at"]), None)
        matches.append({"family": "FVG_CONTINUATION_5M", "direction": "LONG",
                        "fvg": {"low": str(fv["low"]), "high": str(fv["high"]), "at": fv["at"]},
                        "body_close_above_at": bars5[conf_i][0], "retrace_at": bars5[retr_i][0],
                        "confirmation_at": conf2[0], "entry": f"{fv['low']}-{fv['high']} (retrace-fill)",
                        "stop": "beyond FVG (DR-201)", "target": (f"bearish OB at {tgt['at']}" if tgt else UNKNOWN),
                        "displacement_threshold": UNKNOWN, "grade": "A if FVG+pattern (DR-207)",
                        "bearish_mirror": "UNKNOWN (DR-202 documents bullish only)"})
    return matches


def detect_asia_fakeout(m1, up_to_ts=None):
    """DR-205 bearish: Asia H/L frozen -> London/NY wick above Asia high, body fails to close above
    -> reversal -> first LL below Asia low -> short. Bullish mirror emitted symmetrically."""
    if up_to_ts:
        m1 = [b for b in m1 if b[0] + 60 <= up_to_ts]
    if not m1:
        return []
    bars15 = F.resample_1m(m1, 900)
    matches = []
    from datetime import datetime, timezone
    days = sorted({datetime.fromtimestamp(b[0], timezone.utc).date() for b in m1})
    for day in days:
        day_ts = int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp())
        ar = F.asia_range(m1, day_ts)
        if ar["asia_high"] == UNKNOWN:
            continue
        ah, al = ar["asia_high"], ar["asia_low"]
        post = [b for b in bars15 if datetime.fromtimestamp(b[0], timezone.utc).date() == day
                and datetime.fromtimestamp(b[0], timezone.utc).hour >= 6]
        # bearish fakeout above Asia high
        fk = next((b for b in post if F.failed_close(b, ah, "high")), None)
        if fk is not None:
            ll = F.first_lower_low(post, al, fk[0])
            matches.append({"family": "ASIA_SESSION_FAKEOUT", "direction": "SHORT", "day": str(day),
                            "asia_high": str(ah), "asia_low": str(al), "fakeout_at": fk[0],
                            "first_lower_low_at": ll, "confirmed": ll is not None,
                            "entry": "short retracement", "stop": f"above failed high {ah}",
                            "target": "next major liquidity (DR-205)", "grade": "A+++ if +LL+engulfing (DR-207)",
                            "asia_window": ar["window"]})
        # bullish mirror below Asia low
        fkb = next((b for b in post if F.failed_close(b, al, "low")), None)
        if fkb is not None:
            hh = F.first_higher_high(post, ah, fkb[0])
            matches.append({"family": "ASIA_SESSION_FAKEOUT", "direction": "LONG", "day": str(day),
                            "asia_high": str(ah), "asia_low": str(al), "fakeout_at": fkb[0],
                            "first_higher_high_at": hh, "confirmed": hh is not None,
                            "entry": "long retracement", "stop": f"below failed low {al}",
                            "target": "next major liquidity (DR-205 mirror)", "grade": "A+++ if +HH+engulfing",
                            "asia_window": ar["window"]})
    return matches


if __name__ == "__main__":
    import io, json
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    PRICE = os.path.join(HERE, "..", "..", "..", "price_data",
                         "XAUUSD_1M_PEPPERSTONE_2026-07-08_to_2026-07-15_CANONICAL.csv")
    m1 = _load(PRICE)
    fvg = detect_fvg_continuation_5m(m1)
    asia = detect_asia_fakeout(m1)
    print(f"FVG_CONTINUATION_5M matches: {len(fvg)}")
    for m in fvg[:3]:
        print("  ", json.dumps({k: m[k] for k in ("direction", "fvg", "confirmation_at", "target")}, default=str))
    print(f"ASIA_SESSION_FAKEOUT matches: {len(asia)}")
    for m in asia[:5]:
        print("  ", json.dumps({k: m[k] for k in ("direction", "day", "asia_high", "asia_low", "confirmed")}, default=str))
