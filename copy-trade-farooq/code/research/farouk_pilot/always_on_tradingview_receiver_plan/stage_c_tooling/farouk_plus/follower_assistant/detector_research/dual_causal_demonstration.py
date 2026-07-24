"""Phase 4 — DUAL CAUSAL DEMONSTRATION (RESEARCH-ONLY, offline).

A) TECHNICAL_FIXTURE_NOT_EDGE_EVIDENCE — a hand-built 1m fixture containing one authorised family
   (ASIA_SESSION_FAKEOUT), proving detection + causal feature generation + completed-bar-only scoring.
   Does NOT establish profitability.
B) Pre-registered UNTOUCHED market window — a real XAUUSD 1m window (NOT F001/F002), source-hash frozen
   BEFORE scoring, scored deterministically with an honest result classification.

Writes two artifacts. Neither is edge/prospective/training evidence.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import sys
import time
from decimal import Decimal as D
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import detectors as DET                                           # noqa: E402
import detector_features as F                                    # noqa: E402

PRICE = os.path.join(HERE, "..", "..", "..", "price_data",
                     "XAUUSD_1M_PEPPERSTONE_2026-07-08_to_2026-07-15_CANONICAL.csv")


def _load(path):
    out = []
    for r in csv.reader(open(path, encoding="utf-8-sig")):
        if not r or r[0] in ("time", ""):
            continue
        out.append((int(r[0]), D(r[1]), D(r[2]), D(r[3]), D(r[4])))
    out.sort()
    return out


def _bar(ts, o, h, l, c):
    return (ts, D(str(o)), D(str(h)), D(str(l)), D(str(c)))


# ---- Demonstration A: known-pattern technical fixture -----------------------------------------
def demo_a():
    """Build a bearish Asia-fakeout: Asia 00-06 UTC range, then a London wick ABOVE the Asia high with
    NO body close above, then a first lower-low below the Asia low -> confirmed SHORT fakeout."""
    day = int(datetime(2026, 3, 2, tzinfo=timezone.utc).timestamp())   # arbitrary fixture day
    bars = []
    # Asia session 00:00-05:59 UTC: range roughly 1990-2010
    for i in range(360):
        t = day + i * 60
        bars.append(_bar(t, 2000, 2010 if i % 30 == 0 else 2003, 1990 if i % 40 == 0 else 1997, 2000))
    # London 06:00+: a 15m-scale wick ABOVE asia_high(2010) that fails to close above
    base = day + 360 * 60
    for i in range(15):
        bars.append(_bar(base + i * 60, 2008, 2018 if i == 7 else 2009, 2006, 2007))  # wick to 2018, close 2007<2010
    # then reversal down to a first LOWER LOW below asia_low(1990); descend well past 1990 and add
    # trailing bars so the lower-low sits in a COMPLETED 15m bucket (detector drops the final open one)
    base2 = base + 15 * 60
    for i in range(45):
        px = 2005 - i * 1.5                      # 2005 -> ~1939, clearly through 1990
        bars.append(_bar(base2 + i * 60, px + 1, px + 1, px - 1, px))
    tail = base2 + 45 * 60
    for i in range(30):                          # flat trailing bars -> LL bucket completes
        bars.append(_bar(tail + i * 60, 1940, 1941, 1939, 1940))
    matches = DET.detect_asia_fakeout(bars)
    shorts = [m for m in matches if m["direction"] == "SHORT"]
    confirmed = [m for m in shorts if m["confirmed"]]
    return {
        "demonstration": "A_KNOWN_PATTERN_TECHNICAL_FIXTURE",
        "label": "TECHNICAL_FIXTURE_NOT_EDGE_EVIDENCE",
        "eligible_for_training": False, "eligible_for_prospective_evidence": False,
        "family": "ASIA_SESSION_FAKEOUT",
        "asia_fakeout_short_detected": len(shorts) > 0,
        "asia_fakeout_short_confirmed": len(confirmed) > 0,
        "match_sample": ({k: shorts[0][k] for k in ("direction", "asia_high", "asia_low", "confirmed", "first_lower_low_at")}
                         if shorts else None),
        "causal_note": "detector uses completed candles only (resample drops open bar; failed_close on completed bars)",
        "profitability": "NOT ESTABLISHED (fixture only)",
        "review_only": True, "observation_only": True,
    }


# ---- Demonstration B: pre-registered untouched market window ----------------------------------
def demo_b(select_ts):
    """Pre-register ONE untouched real window (a full UTC day NOT used by F001/F002 which were 07-14),
    freeze its source-hash BEFORE scoring, then score deterministically with an honest result."""
    m1 = _load(PRICE)
    # selection method: earliest full UTC day in the canonical file that is NOT 2026-07-14 (F001/F002)
    days = sorted({datetime.fromtimestamp(b[0], timezone.utc).date() for b in m1})
    chosen = next(d for d in days if d.isoformat() != "2026-07-14"
                  and sum(1 for b in m1 if datetime.fromtimestamp(b[0], timezone.utc).date() == d) > 300)
    window = [b for b in m1 if datetime.fromtimestamp(b[0], timezone.utc).date() == chosen]
    # PRE-REGISTER: freeze the window source hash BEFORE any scoring
    src_bytes = "".join(",".join(str(x) for x in b) + ";" for b in window).encode()
    window_hash = hashlib.sha256(src_bytes).hexdigest()
    registration = {
        "source_file": os.path.basename(PRICE),
        "instrument": "XAUUSD", "timezone": "UTC", "timestamp_semantics": "bar OPEN epoch seconds (close=open+60)",
        "window_utc_day": chosen.isoformat(), "window_bar_count": len(window),
        "selection_method": "earliest full UTC day in canonical file that is NOT 2026-07-14 (F001/F002 excluded)",
        "selection_timestamp_utc": datetime.fromtimestamp(select_ts, timezone.utc).isoformat(),
        "window_source_sha256": window_hash,
        "warmup_note": "detectors self-warm from the window's own Asia session; no external context injected",
        "authorised_families": ["FVG_CONTINUATION_5M", "ASIA_SESSION_FAKEOUT"],
    }
    # SCORE (deterministic, completed-bar only)
    fvg = DET.detect_fvg_continuation_5m(window)
    asia = DET.detect_asia_fakeout(window)
    confirmed_asia = [m for m in asia if m.get("confirmed")]
    if len(window) < 60:
        result = "INSUFFICIENT_CAUSAL_CONTEXT"
    elif fvg or confirmed_asia:
        result = "VALID_AUTHORISED_SETUP_DETECTED"
    else:
        result = "NO_VALID_SETUP"
    return {
        "demonstration": "B_PRE_REGISTERED_UNTOUCHED_WINDOW",
        "registration": registration,
        "result": result,
        "fvg_continuation_matches": len(fvg),
        "asia_fakeout_matches": len(asia), "asia_fakeout_confirmed": len(confirmed_asia),
        "window_substituted": False,
        "f001_f002_used": False,
        "volume_profile": "DATA_UNAVAILABLE (not fabricated)",
        "eligible_for_training": False, "eligible_for_prospective_evidence": False,
        "review_only": True, "observation_only": True,
    }


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    select_ts = int(time.time())
    a = demo_a()
    b = demo_b(select_ts)
    json.dump(a, open(os.path.join(HERE, "demonstration_A_known_fixture_v0_1.json"), "w", encoding="utf-8"), indent=1, default=str)
    json.dump(b, open(os.path.join(HERE, "demonstration_B_untouched_window_v0_1.json"), "w", encoding="utf-8"), indent=1, default=str)
    print("DEMO A:", a["family"], "short_detected=", a["asia_fakeout_short_detected"],
          "confirmed=", a["asia_fakeout_short_confirmed"], "|", a["label"])
    print("DEMO B: window", b["registration"]["window_utc_day"], "bars", b["registration"]["window_bar_count"],
          "hash", b["registration"]["window_source_sha256"][:16], "-> RESULT:", b["result"])
    print("  fvg matches:", b["fvg_continuation_matches"], "asia confirmed:", b["asia_fakeout_confirmed"])


if __name__ == "__main__":
    main()
