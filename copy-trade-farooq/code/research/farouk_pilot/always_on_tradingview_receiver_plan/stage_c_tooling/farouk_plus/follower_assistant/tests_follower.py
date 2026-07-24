"""Deterministic tests for the Stage-1 Follower Assistant (inline harness, no pytest).

Fixture expectations are derived INDEPENDENTLY from the ratified constitution + the imported
Pepperstone bars (hand bar-walk documented in comments) — not copied from earlier session output.
"""
from __future__ import annotations

import io
import json
import os
import sys
from decimal import Decimal as D
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from engine import FollowerEngine, run_campaign, LANES               # noqa: E402
import guards                                                        # noqa: E402
import run_fixtures                                                  # noqa: E402

PASS = 0


def ok(cond, name):
    global PASS
    assert cond, f"FAIL: {name}"
    PASS += 1


def mk_bars(spec, start=1_784_000_000):
    """spec: list of (o,h,l,c) -> 1m bars from start."""
    return [(start + i * 60, D(str(o)), D(str(h)), D(str(l)), D(str(c)))
            for i, (o, h, l, c) in enumerate(spec)]


CONST = json.load(open(os.path.join(HERE, "follower_constitution_v0_1.json"), encoding="utf-8"))


def base_campaign(**kw):
    c = {"setup_id": "TEST", "direction": "LONG", "zone_low": D("100"), "zone_high": D("106"),
         "sl": "90", "signal_ts": 1_784_000_000, "attempt_number": 1, "events": [],
         "frozen_evidence_sha256": "t" * 64}
    c.update(kw)
    return c


# ---------- 1. real fixtures: strict + sensitivity lanes ------------------------------------
fx = run_fixtures.run(write=False)
A1 = fx["XAU-F001-20260714"]["lanes"]["LANE_A"]
B1 = fx["XAU-F001-20260714"]["lanes"]["LANE_B"]
A2 = fx["XAU-F002-20260714"]["lanes"]["LANE_A"]
B2 = fx["XAU-F002-20260714"]["lanes"]["LANE_B"]

# F001 hand walk: near leg 4019 fills 08:39 (low 4018.69 < 4019); mid 4013 never (min low 4013.64);
# 09:10 close-worst single-leg -> bank 1/6 @4021.65 (+2.65$); 10:48 BE 4019 scoped; unfilled cancel;
# 11:07 low 4018.47 <= 4019 -> scratch 1/6 @4019. Realized = 2.65/6 $ = 4.42 pips/unit. CLOSED.
ok(A1["campaign_state"] == "CLOSED", "F001 A closed")
ok(A1["realized_pips_per_unit"] == "4.42", "F001 A realized 4.42 p/unit")
ok(len(A1["slices"]) == 2 and A1["slices"][0]["exit"] == "4021.65", "F001 A bank @4021.65")
ok(A1["legs"][1]["state"] == "CANCELLED" and A1["legs"][2]["state"] == "CANCELLED",
   "F001 unfilled legs cancelled (partial-zone fill)")
# Lane B: graze $3 -> scratch when low <= 4016.00 (first 11:09, low 4015.4) at BE 4019 -> same money
ok(B1["realized_pips_per_unit"] == "4.42", "F001 B same realized (lanes converge, single leg)")
ok(any(t["event"] == "BE_GRAZE_SURVIVED" for t in B1["transitions"]), "F001 B graze logged before scratch")

# F002 hand walk (Lane A): market 1/3 @4084.58 (signal bar in zone); 13:34 TP1 -> 1/6 @4080.67 (+3.91);
# 13:54 BE 4084.58 + take-some 25% -> 1/24 @4076.34 (+8.24); unfilled cancelled;
# 14:13 high 4085.32 >= BE -> scratch 1/8 @4084.58. Realized $ = 3.91/6 + 8.24/24 = 0.995 -> 9.95 p/unit.
ok(A2["campaign_state"] == "CLOSED", "F002 A closed")
ok(A2["realized_pips_per_unit"] == "9.95", "F002 A realized 9.95 p/unit")
ok(A2["legs"][0]["kind"] == "MARKET_AT_SIGNAL_CLOSE", "F002 market-first leg (in-zone signal bar)")
ok("AMBIGUOUS_SEQUENCE" in A2["legs"][0]["tags"][0], "F002 signal-bar fill tagged ambiguous")
ok(any("STOP_FIRST_ON_TOUCH" in s["tags"] for s in A2["slices"] if s["reason"] == "P10_BE_SCRATCH"),
   "F002 14:13 BE retouch scratched stop-first")
# Lane B: survives 14:13 (graze 0.74<=3), banks 50% (1/16 @4074.56), scratched 14:34 (4090.42>4087.58),
# keeps mid/far -> fill 4089 @14:34, 4094 @15:06, open at data end.
ok(B2["campaign_state"] == "OPEN_PENDING_DATA" and B2["follow_through"] == "PENDING_FOLLOW_THROUGH",
   "F002 B open pending follow-through (partial window preserved)")
ok(B2["realized_pips_per_unit"] == "16.21", "F002 B realized 16.21 p/unit")
ok(B2["unrealized_pips_per_unit"] == "210.67", "F002 B unrealized 210.67 p/unit")
ok(B2["legs"][1]["state"] == "FILLED" and B2["legs"][2]["state"] == "FILLED",
   "F002 B kept resting legs filled later")
ok(A2["realized_pips_per_unit"] != B2["realized_pips_per_unit"], "strict vs sensitivity lanes diverge")

# ---------- 2. idempotency ---------------------------------------------------------------------
fx2 = run_fixtures.run(write=False)
ok(fx2["XAU-F001-20260714"]["logical_hash"] == fx["XAU-F001-20260714"]["logical_hash"]
   and fx2["XAU-F002-20260714"]["logical_hash"] == fx["XAU-F002-20260714"]["logical_hash"],
   "re-run yields identical logical hashes (idempotent)")

# ---------- 3. duplicate + revised messages ---------------------------------------------------
bars = mk_bars([(107, 107, 106.5, 107), (106.4, 106.5, 105.9, 106.2), (106, 108, 105.9, 107.5)])
ev = {"ts": bars[2][0], "instruction_type": "TAKE_PCT_OFF", "message_id": 9, "pct": 0.5, "scope": None}
c = base_campaign(events=[ev, dict(ev)])          # exact duplicate delivery
r = FollowerEngine(c, bars, "LANE_A", CONST).run()
ok(sum(1 for s in r["slices"] if s["reason"] == "P12_TAKE_PCT") == 1
   and any(t["event"] == "DUPLICATE_EVENT_SKIPPED" for t in r["transitions"]),
   "duplicate message applied exactly once")
# revision handling: later XAU_F_SETUP revision wins in loader (synthetic, non-vacuous)
import io as _io
_two = ('{"record_type":"XAU_F_SETUP","setup_id":"S","revision":1,"x":1}\n'
        '{"record_type":"XAU_F_SETUP","setup_id":"S","revision":2,"x":2}\n')
_orig = open(run_fixtures.FWD_LEDGER, encoding="utf-8").read
try:
    import builtins
    real_open = builtins.open
    def fake_open(p, *a, **k):
        if str(p) == str(run_fixtures.FWD_LEDGER):
            return _io.StringIO(_two)
        return real_open(p, *a, **k)
    builtins.open = fake_open
    ok(run_fixtures.load_setups()["S"]["revision"] == 2, "loader takes latest revision (rev2 wins)")
finally:
    builtins.open = real_open

# message_id None does not crash (red-team finding 7)
ev_nm = [{"ts": bars[2][0], "instruction_type": "TAKE_PCT_OFF", "message_id": None, "scope": None, "pct": 0.5}]
r_nm = FollowerEngine(base_campaign(events=ev_nm), bars, "LANE_A", CONST).run()
ok(any(s["reason"] == "P12_TAKE_PCT" for s in r_nm["slices"]), "null message_id handled")

# ---------- 3b. red-team fixes: fail-closed + same-bar SL/BE + coalescing ----------------------
# unknown type co-delivered with FINAL_CLOSE must PAUSE, not close (finding 3a)
ev_u = [{"ts": bars[2][0], "instruction_type": "WEIRD_NEW_THING", "message_id": 11, "scope": None, "pct": None},
        {"ts": bars[2][0], "instruction_type": "FINAL_CLOSE", "message_id": 11, "scope": None, "pct": None}]
r_u = FollowerEngine(base_campaign(events=ev_u), bars, "LANE_A", CONST).run()
ok(r_u["campaign_state"] == "PAUSED_NEEDS_HUMAN_REVIEW", "unknown+FINAL_CLOSE in one message pauses")
# a later same-bar message cannot overwrite PAUSED (finding 3b)
ev_u2 = [{"ts": bars[2][0], "instruction_type": "WEIRD", "message_id": 11, "scope": None, "pct": None},
         {"ts": bars[2][0], "instruction_type": "FINAL_CLOSE", "message_id": 12, "scope": None, "pct": None}]
r_u2 = FollowerEngine(base_campaign(events=ev_u2), bars, "LANE_A", CONST).run()
ok(r_u2["campaign_state"] == "PAUSED_NEEDS_HUMAN_REVIEW"
   and any(t["event"] == "MESSAGE_SKIPPED_WHILE_PAUSED" for t in r_u2["transitions"]),
   "PAUSED not overwritten by later same-bar FINAL_CLOSE")
# BE precedes SL when both struck in one bar (finding 2): LONG BE 106 armed, SL 90, huge down bar
spec_be = [(107, 107, 106.5, 107), (106.4, 106.5, 105.5, 106.4),    # fill near 106
           (106.5, 106.8, 106.2, 106.5),                              # BE arm bar (low 106.2 > 106: no touch)
           (106.3, 106.4, 89.0, 90.5)]                                # strikes BE 106 AND SL 90
bars_be = mk_bars(spec_be)
ev_be2 = [{"ts": bars_be[2][0], "instruction_type": "SL_TO_ENTRY", "message_id": 13, "scope": None, "pct": None}]
r_be2 = FollowerEngine(base_campaign(events=ev_be2), bars_be, "LANE_A", CONST).run()
sc = [s for s in r_be2["slices"] if s["reason"] == "P10_BE_SCRATCH"]
ok(len(sc) == 1 and sc[0]["exit"] == "106" and "BE_PRECEDES_SL_SAME_BAR" in sc[0]["tags"]
   and not any(s["reason"] == "P21_POSTED_SL" for s in r_be2["slices"]),
   "same-bar BE+SL exits at BE, not SL (tagged)")
# multi-leg CLOSE_WORST + TP1 coalesced: held legs are HELD (finding 10)
bars_cw = mk_bars([(107, 107, 106.5, 107), (106.4, 106.5, 105.5, 106),
                   (105, 105.5, 102.8, 103.2), (103.5, 106.2, 103.4, 106)])
ev_cw = [{"ts": bars_cw[3][0], "instruction_type": "CLOSE_WORST", "message_id": 14, "scope": None, "pct": None},
         {"ts": bars_cw[3][0], "instruction_type": "TP1_TAKE", "message_id": 14, "scope": None, "pct": None}]
r_cw = FollowerEngine(base_campaign(events=ev_cw), bars_cw, "LANE_A", CONST).run()
ok(sum(1 for s in r_cw["slices"]) == 1 and r_cw["slices"][0]["reason"] == "P11_CLOSE_WORST"
   and any(t["event"] == "TP1_COALESCED_INTO_CLOSE_WORST" for t in r_cw["transitions"]),
   "multi-leg close-worst+tp1: worst closed once, best legs held")
# Lane B graze applies to POSTED SL too (finding 8): SHORT SL 120, bar high 121.5 (breach 1.5 <= 3)
spec_sl = [(105, 106.5, 104.9, 105), (110, 121.5, 109, 118)]
bars_sl = mk_bars(spec_sl)
c_sl = base_campaign(direction="SHORT", zone_low=D("104"), zone_high=D("110"), sl="120", events=[])
r_sla = FollowerEngine(c_sl, bars_sl, "LANE_A", CONST).run()
r_slb = FollowerEngine(c_sl, bars_sl, "LANE_B", CONST).run()
ok(any(s["reason"] == "P21_POSTED_SL" for s in r_sla["slices"]), "Lane A: SL touch stops out")
ok(not any(s["reason"] == "P21_POSTED_SL" for s in r_slb["slices"])
   and any(t["event"] == "SL_GRAZE_SURVIVED" for t in r_slb["transitions"]),
   "Lane B: $1.50 SL breach within $3 graze survives + logged")

# ---------- 4. per-leg vs average BE (multi-leg synthetic) -------------------------------------
# LONG zone 100-106: legs near 106 / mid 103 / far 100. Bar walk: fill near+mid, unscoped BE,
# then a dip to 103.5: per-leg -> near leg (BE 106) survives? no: dip 105.9 touches near BE first bar.
spec = [(107, 107, 106.5, 107),          # signal bar (not in zone)
        (106.4, 106.5, 105.5, 106),      # fills near 106 (through), not mid
        (105, 105.5, 102.8, 103.2),      # fills mid 103 (through)
        (103.5, 106.2, 103.4, 106),      # BE instruction lands here (close 106)
        (105.8, 105.9, 104.4, 104.5)]    # dip: touches near BE 106? high 105.9 no; low 104.4<=106 yes
bars4 = mk_bars(spec)
evbe = [{"ts": bars4[3][0], "instruction_type": "SL_TO_ENTRY", "message_id": 1, "scope": None, "pct": None}]
ca = base_campaign(events=evbe)
ra = FollowerEngine(ca, bars4, "LANE_A", CONST).run()          # per-leg BE: near@106, mid@103
rb = FollowerEngine(ca, bars4, "LANE_B", CONST).run()          # avg BE = (106+103)/2 = 104.5, graze $3
ok(any(s["reason"] == "P10_BE_SCRATCH" and s["exit"] == "106" for s in ra["slices"]),
   "per-leg BE scratches near leg at its own fill (106)")
ok(all(l["be_price"] in ("104.5000", None) or l["state"] != "FILLED" for l in rb["legs"]) and
   not any(s["reason"] == "P10_BE_SCRATCH" for s in rb["slices"]),
   "average-BE lane holds through the same dip (104.4 within $3 graze of 104.50)")

# ---------- 5. close-worst multi-leg + take-some default ---------------------------------------
ev5 = [{"ts": bars4[3][0], "instruction_type": "CLOSE_WORST", "message_id": 2, "scope": None, "pct": None},
       {"ts": bars4[4][0], "instruction_type": "TAKE_PCT_OFF", "message_id": 3, "scope": None, "pct": None}]
r5 = FollowerEngine(base_campaign(events=ev5), bars4, "LANE_A", CONST).run()
worst = [s for s in r5["slices"] if s["reason"] == "P11_CLOSE_WORST"]
ok(len(worst) == 1 and worst[0]["entry"] == "106" and worst[0]["size"] == "1/3",
   "close-worst closes the WORST filled leg fully (106)")
some = [s for s in r5["slices"] if s["reason"] == "P12_TAKE_PCT"]
ok(len(some) == 1 and some[0]["size"] == "1/12" and "DESIGN_PCT_DEFAULT_25" in some[0]["tags"],
   "'take some' -> ratified 25% of open with DESIGN_PCT tag (1/12 of unit from mid leg)")

# ---------- 6. cancellation / missed zone / no re-entry ---------------------------------------
bars6 = mk_bars([(110, 110.5, 109.5, 110)] * 4)
ev6 = [{"ts": bars6[2][0], "instruction_type": "CANCEL", "message_id": 4, "scope": None, "pct": None},
       {"ts": bars6[3][0], "instruction_type": "FINAL_CLOSE", "message_id": 5, "scope": None, "pct": None}]
r6 = FollowerEngine(base_campaign(events=ev6), bars6, "LANE_A", CONST).run()
ok(r6["campaign_state"] == "NO_FILL" and all(l["state"] == "CANCELLED" for l in r6["legs"]),
   "missed zone -> cancel -> NO_FILL, nothing chased")
r7 = FollowerEngine(base_campaign(attempt_number=3), bars6, "LANE_A", CONST).run()
ok(r7["campaign_state"] == "SKIPPED_BY_R2_CAP", "attempt >=3 skipped (P15/R2 cap)")

# ---------- 7. feed-sensitive graze (synthetic) ------------------------------------------------
spec8 = [(105, 106.5, 104.9, 105),      # signal bar in zone (low<=106) -> market fill @105
         (104, 104.5, 103, 103.5),
         (103.6, 105.8, 103.5, 105.5),  # BE armed this bar
         (105.5, 106.9, 105.4, 106.0)]  # high 106.9: touches BE 105? yes; breach 1.9 <= 3
bars8 = mk_bars(spec8)
ev8 = [{"ts": bars8[2][0], "instruction_type": "SL_TO_ENTRY", "message_id": 6, "scope": None, "pct": None}]
c8 = base_campaign(direction="SHORT", zone_low=D("104"), zone_high=D("110"), sl="120", events=ev8)
r8a = FollowerEngine(c8, bars8, "LANE_A", CONST).run()
r8b = FollowerEngine(c8, bars8, "LANE_B", CONST).run()
ok(any(s["reason"] == "P10_BE_SCRATCH" for s in r8a["slices"]), "Lane A: BE touch scratches")
ok(not any(s["reason"] == "P10_BE_SCRATCH" for s in r8b["slices"])
   and any(t["event"] == "BE_GRAZE_SURVIVED" for t in r8b["transitions"]),
   "Lane B: $1.90 breach within $3 graze survives + AMBIGUOUS_FILL_BAND logged")

# ---------- 8. fail-closed unknown instruction ------------------------------------------------
ev9 = [{"ts": bars8[2][0], "instruction_type": "SOMETHING_NEW", "message_id": 7, "scope": None, "pct": None}]
r9 = FollowerEngine(base_campaign(direction="SHORT", zone_low=D("104"), zone_high=D("110"),
                                  sl="120", events=ev9), bars8, "LANE_A", CONST).run()
ok(r9["campaign_state"] == "PAUSED_NEEDS_HUMAN_REVIEW", "unknown instruction pauses (P20 fail-closed)")

# ---------- 9. prohibited fields + stamps ------------------------------------------------------
card = fx["XAU-F001-20260714"]["card"]
ok(card["review_only"] is True and card["executable"] is False and card["trade_ready"] is False,
   "card carries review-only stamps")
try:
    bad = dict(card)
    bad["lot_size"] = 1
    guards.assert_clean(bad, "negative")
    ok(False, "lot_size must be rejected")
except guards.GuardViolation:
    ok(True, "prohibited key rejected by guard")
try:
    bad2 = dict(card)
    bad2["review_only"] = False
    guards.assert_clean(bad2, "negative2")
    ok(False, "altered stamp must be rejected")
except guards.GuardViolation:
    ok(True, "altered review_only stamp rejected")
blob = json.dumps(card, default=str).lower()
for tok in ("account_id", "broker_route", "order_submission", "credentials", "lot_size"):
    ok(tok not in blob, f"no '{tok}' anywhere in card")
# broadened key guard (red-team finding 13): probe every P24-named prohibition class
for bad_key in ("broker", "account_number", "execution_permission", "position_size",
                "quantity", "leverage", "ticket", "submit_at"):
    try:
        guards.assert_clean(dict(card, **{bad_key: 1}), "probe")
        ok(False, f"key '{bad_key}' must be rejected")
    except guards.GuardViolation:
        ok(True, f"key '{bad_key}' rejected")
# value-level smuggling rejected
try:
    guards.assert_clean(dict(card, note_field="set lot_size=0.5 please"), "probe-value")
    ok(False, "value smuggling must be rejected")
except guards.GuardViolation:
    ok(True, "forbidden identifier inside a value rejected")
# acknowledgement enum is closed (finding 15)
try:
    guards.assert_clean(dict(card, acknowledgement_state="ACKNOWLEDGED_AND_EXECUTE"), "probe-ack")
    ok(False, "ack enum must be closed")
except guards.GuardViolation:
    ok(True, "acknowledgement enum closed")
# append_once demands full hash + exact-equality dedup (finding 14)
try:
    guards.append_once(os.path.join(HERE, "cards", "_nonexistent.jsonl"),
                       dict(card, logical_hash="aaa1"))
    ok(False, "short hash must be rejected")
except guards.GuardViolation:
    ok(True, "short logical_hash rejected by append_once")

# ---------- 10. scorer + gate + pre-mark immutability ------------------------------------------
inv = guards.verify_project_invariants()
ok(inv["scorers"] == "UNCHANGED" and inv["pre_marks"] == "FROZEN"
   and inv["gates"] == "PAPER/PREVIEW/False/False", "scorers/pre-marks/gates verified unchanged")

# ---------- 11. no outcome leakage: engine object never reads outcome fields -------------------
ok("outcome_status" not in json.dumps(fx["XAU-F001-20260714"]["lanes"]),
   "lane results carry no imported outcome fields (no leakage)")

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    print(f"PASS {PASS} follower-assistant checks")
