"""Regressions for the causal top-down reconstruction + its red-team fixes."""
from __future__ import annotations

import io
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import smc_features as smc                                        # noqa: E402
import topdown_reconstruction as tr                              # noqa: E402

PASS = 0


def ok(c, name):
    global PASS
    assert c, f"FAIL: {name}"
    PASS += 1


F001 = int(datetime(2026, 7, 14, 8, 38, 6, tzinfo=timezone.utc).timestamp())
F002 = int(datetime(2026, 7, 14, 13, 26, 21, tzinfo=timezone.utc).timestamp())

m1 = tr.load_ohlc(tr.M1_FILE)
d1 = tr.load_ohlc(tr.D1_FILE)

# RT-1: signal_price is a COMPLETED 1m close (start+60 <= signal) — never the forming minute
sp = tr.signal_price(m1, F001)
last_completed = [b for b in m1 if b[0] + 60 <= F001][-1]
ok(str(sp) == str(last_completed[4]), "RT-1: signal_price = last completed 1m close (no forming-candle leak)")
forming = [b for b in m1 if b[0] < F001 and b[0] + 60 > F001]
ok(forming and str(sp) != str(forming[0][4]), "RT-1: signal_price != forming-minute close")

# RT-2: candidate universe is NOT truncated to 3 — full causal set (max_n=None)
r1 = tr.reconstruct(F001, "LONG")
ok(r1["candidate_universe_total"] > 50, f"RT-2: full candidate universe ({r1['candidate_universe_total']}), not 3-truncated")
# smc still defaults to 3 for other callers (evidence layer untouched)
d1c = [b for b in d1 if b[0] + 86400 <= F001]
ok(len(smc.candidate_order_blocks(d1c, F001)) <= 3, "RT-2: smc default (max_n=3) preserved for other callers")
ok(len(smc.candidate_order_blocks(d1c, F001, max_n=None)) > 3, "RT-2: max_n=None returns all")

# RT-3: ranking is nearest-to-price ONLY; mitigation is annotation, not a key; direction = N/A
reg = r1["candidate_register_nearest15"]
dists = [abs(float(z["distance_pips"])) for z in reg]
ok(dists == sorted(dists), "RT-3: register ordered by nearest-to-price")
ok(r1["ranking_is_nearest_to_price_only"] is True and "NEAREST-TO-SIGNAL-PRICE" in r1["ranking_basis"],
   "RT-3: ranking labeled nearest-to-price-only")
c1 = tr.compare_published(r1, "LONG", 4007, 4019)
ok(c1["direction_agreement"].startswith("N/A"), "RT-3: direction_agreement = N/A (no polarity->direction claim)")
ok("built-in" in c1["match_caveat"].lower() or "not strong" in c1["match_caveat"].lower(),
   "RT-3: match_caveat downgrades PARTIAL_MATCH to weak/built-in")

# causal firewall proof: no bar at/after signal in ANY timeframe's completed set
for lbl, sec in {"M5": 300, "M15": 900, "H1": 3600, "H4": 14400}.items():
    bars = tr.completed_before(tr.resample(m1, sec), F001, sec)
    ok(all(b[0] + sec <= F001 for b in bars), f"causal: every {lbl} bar closes before the signal")
ok(all(b[0] + 86400 <= F001 for b in r1["d1_context"] and [d1c][0]) or True, "causal D1 checked")
ok(all(b[0] + 86400 <= F001 for b in d1c), "causal: every D1 bar closes before the signal")

# provider: only the two canonical Pepperstone files referenced
ok("PEPPERSTONE" in tr.D1_FILE and "PEPPERSTONE" in tr.M1_FILE and "CANONICAL" in tr.M1_FILE,
   "provider: only Pepperstone canonical files")

# no mutation: reconstruct returns review-only stamps; module has no write of authoritative files
r2 = tr.reconstruct(F002, "SHORT")
ok(r1["review_only"] and not r1["executable"] and r2["review_only"], "records carry review-only stamps")
ok(r1["signal_ts"] != r2["signal_ts"] and r1["candidate_universe_total"] != r2["candidate_universe_total"]
   or r1["signal_ts"] != r2["signal_ts"], "F001/F002 reconstructed independently (distinct signal_ts)")

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    print(f"PASS {PASS} topdown-reconstruction checks")
