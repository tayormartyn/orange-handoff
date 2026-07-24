"""Deterministic tests for the Stage-1.5 shadow market tracker (inline harness)."""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
for p in (HERE, PARENT):
    sys.path.insert(0, p)
import guards                                                      # noqa: E402
import tracker_engine                                              # noqa: E402
from market_events import BarStream, MarketBar, MarketEventError, validate_bar  # noqa: E402
from providers import ReplayCSVProvider, FileTailProvider, DukascopyBarProvider  # noqa: E402

PASS = 0


def ok(cond, name):
    global PASS
    assert cond, f"FAIL: {name}"
    PASS += 1


T0 = 1_784_000_000 - (1_784_000_000 % 60)


def bar(i, o, h, l, c, **kw):
    return validate_bar({"provider": "SYNTHETIC_TEST", "event_ts": T0 + i * 60,
                         "receive_ts": T0 + i * 60 + 60, "open": o, "high": h, "low": l,
                         "close": c, **kw})


CONST = json.load(open(os.path.join(PARENT, "follower_constitution_v0_1.json"), encoding="utf-8"))


def camp(**kw):
    c = {"setup_id": "T", "direction": "LONG", "zone_low": D("100"), "zone_high": D("106"),
         "sl": "90", "signal_ts": T0, "attempt_number": 1, "events": [],
         "frozen_evidence_sha256": "t" * 64}
    c.update(kw)
    return c


def setup_rec(c):
    return {"setup_id": c["setup_id"], "sl": c["sl"],
            "management_timing_8c": {"instruction_events": []},
            "detector_v0_2_label": "WATCH", "detector_v0_3": {"review_label": "WATCH"},
            "pre_mark_comparison": {}}


def snap(c, bars_list, now=None):
    s = BarStream()
    for b in bars_list:
        s.ingest(b)
    return tracker_engine.track(setup_rec(c), c, s, CONST, now or (T0 + 86400), "SYNTHETIC_TEST")


# ---------- market-event contract ---------------------------------------------------------------
s = BarStream()
ok(s.ingest(bar(0, 107, 107.5, 106.5, 107)) == "ACCEPTED", "bar accepted")
ok(s.ingest(bar(0, 107, 107.5, 106.5, 107)) == "DUPLICATE", "duplicate bar detected")
try:
    s.ingest(bar(0, 107, 108, 106.5, 107.5))
    ok(False, "conflict without revision must raise")
except MarketEventError:
    ok(True, "conflicting bar without revision refused (no silent mutation)")
ok(s.ingest(bar(0, 107, 108, 106.5, 107.5, revision=2)) == "REVISED_BAR", "revised bar accepted+flagged")
ok(s.ingest(bar(3, 107, 107.2, 106.8, 107)) == "ACCEPTED" and s.gaps() == [(T0, T0 + 180)],
   "gap detected, not interpolated")
ok(s.ingest(bar(1, 107, 107.2, 106.8, 107)) == "OUT_OF_ORDER_ACCEPTED", "out-of-order flagged")
ok(s.staleness_seconds(T0 + 600) == 600 - 240, "staleness computed")
try:
    validate_bar({"provider": "X", "event_ts": T0 + 7, "open": 1, "high": 2, "low": 0.5, "close": 1})
    ok(False, "non-boundary ts must fail")
except MarketEventError:
    ok(True, "non-1m-boundary timestamp rejected")
try:
    validate_bar({"provider": "X", "event_ts": T0, "open": 5, "high": 4, "low": 4.5, "close": 4.6})
    ok(False, "invalid OHLC must fail")
except MarketEventError:
    ok(True, "inconsistent OHLC rejected")

# ---------- providers ----------------------------------------------------------------------------
TMP = tempfile.mkdtemp(prefix="tracker_test_")
csvp = os.path.join(TMP, "bars.csv")
with open(csvp, "w", encoding="utf-8") as fh:
    fh.write("time,open,high,low,close\n")
    for i in range(5):
        fh.write(f"{T0 + i * 60},100,101,99,100.5\n")
rp = ReplayCSVProvider(csvp, clamp_end_ts=T0 + 120)
got = rp.fetch_completed_bars(0)
ok(len(got) == 2 and got[-1].event_ts == T0 + 60,
   "replay clamp = knowledge point: bar opening AT the clamp excluded (RT-13)")
ft = FileTailProvider(csvp)
got_ft = ft.fetch_completed_bars(0)
ok(len(got_ft) == 4, "file-tail treats newest bar as incomplete")
with open(csvp, "w", encoding="utf-8") as fh:                      # atomic-replacement style rewrite
    fh.write("time,open,high,low,close\n")
    for i in range(7):
        fh.write(f"{T0 + i * 60},100,101,99,100.5\n")
got_ft2 = ft.fetch_completed_bars(T0 + 180)
ok([b.event_ts for b in got_ft2] == [T0 + 240, T0 + 300], "file replacement survived; only new bars")
ticks = [(1000, "4000.100", "4000.300"), (30_000, "4001.000", "4001.200"),
         (61_000, "3999.000", "3999.400")]
dbars = DukascopyBarProvider.aggregate_ticks(ticks, T0, T0 + 7200, "test")
ok(len(dbars) == 2 and dbars[0].bid is not None and "NON_PEPPERSTONE_FEED" in dbars[0].quality_flags
   and dbars[0].open == D("4000.200"), "dukascopy tick aggregation deterministic w/ bid/ask + flags")

# ---------- lifecycle ----------------------------------------------------------------------------
r = snap(camp(), [bar(0, 110, 110.5, 109.5, 110)])
ok(r["lanes"]["LANE_A"]["lifecycle"]["current"] == "WAITING_FOR_ZONE", "fresh arming waits for zone")
ok(r["market"]["distance_to_near_edge_pips"] == "40.00", "zone distance computed (110->106 LONG)")
r = snap(camp(), [bar(0, 110, 110.5, 109.5, 110), bar(1, 107, 107.5, 106.0, 106.5)])
ok(r["lanes"]["LANE_A"]["lifecycle"]["current"] == "ZONE_TOUCHED"
   and r["lanes"]["LANE_A"]["engine"]["legs"][0]["state"] == "PROPOSED",
   "exact boundary touch: ZONE_TOUCHED but Lane A trade-through leg NOT filled")
ok(r["lanes"]["LANE_B"]["lifecycle"]["current"] == "RISK_ACTIVE"
   and r["lanes"]["LANE_B"]["engine"]["legs"][0]["state"] == "FILLED",
   "Lane B touch-fill fills at the exact boundary (lanes diverge)")
ok(any(x["class"] == "FEED_SENSITIVE_TOUCH" for x in r["lanes"]["LANE_B"]["ambiguities"]),
   "boundary fill flagged FEED_SENSITIVE_TOUCH")
bars3 = [bar(0, 110, 110.5, 109.5, 110), bar(1, 106, 106.5, 102.8, 103),
         bar(2, 103, 104, 102.9, 103.5)]
r = snap(camp(), bars3)
ok(r["lanes"]["LANE_A"]["lifecycle"]["n_fills"] == 2
   and "PARTIALLY_FILLED" in r["lanes"]["LANE_A"]["lifecycle"]["path"], "three-leg partial fill (2/3)")
bars_all = bars3 + [bar(3, 103, 103.5, 99.5, 100.2)]
r = snap(camp(), bars_all)
ok(r["lanes"]["LANE_A"]["lifecycle"]["n_fills"] == 3
   and "FULLY_FILLED" in r["lanes"]["LANE_A"]["lifecycle"]["path"], "all legs filled")
r = snap(camp(events=[{"ts": T0 + 120, "instruction_type": "CANCEL", "message_id": 1},
                      {"ts": T0 + 180, "instruction_type": "FINAL_CLOSE", "message_id": 2}]),
         [bar(i, 110, 110.5, 109.5, 110) for i in range(4)])
ok(r["lanes"]["LANE_A"]["engine"]["campaign_state"] == "NO_FILL"
   and "OUTCOME_FROZEN" in r["lanes"]["LANE_A"]["lifecycle"]["path"], "no fill -> frozen NO_FILL")
# stop before fill: price collapses through SL region without entering via limit-through first bar
r = snap(camp(zone_low=D("100"), zone_high=D("106"), sl="99"),
         [bar(0, 110, 110.5, 109.5, 110), bar(1, 98, 98.5, 97.5, 98)])
gaps = r["lanes"]["LANE_A"]["ambiguities"]
ok(any(x["class"] == "GAP_FILL_UNCERTAIN" for x in gaps),
   "gap through entry AND stop flagged GAP_FILL_UNCERTAIN")
ok(r["lanes"]["LANE_A"]["engine"]["realized_pips_per_unit"] == "-2100.00"
   or r["lanes"]["LANE_A"]["engine"]["campaign_state"] in ("CLOSED",),
   "stop after gap-fill resolves deterministically (fills then stops, flagged)")
# stop after fill -> STOPPED lifecycle
r = snap(camp(sl="102"), [bar(0, 107, 107, 105.5, 106), bar(1, 105, 105.5, 101.5, 102.3)])
ok("STOPPED" in r["lanes"]["LANE_A"]["lifecycle"]["path"], "stop after fill -> STOPPED")
ok(r["lanes"]["LANE_A"]["mae_pips"] is not None, "MAE computed")
# revised stop honoured forward-only
ev_rs = [{"ts": T0 + 120, "instruction_type": "REVISED_STOP", "message_id": 3, "new_sl": "104"}]
r = snap(camp(sl="90", events=ev_rs),
         [bar(0, 107, 107, 105.5, 106), bar(1, 106, 106.4, 105.8, 106.2),
          bar(2, 106, 106.2, 105.9, 106), bar(3, 105.5, 105.6, 103.8, 104.2)])
ok(any(s["reason"] == "P21_POSTED_SL" and s["exit"] == "104"
       for s in r["lanes"]["LANE_A"]["engine"]["slices"]), "revised stop 104 used after instruction")
# revised zone -> human review
r = snap(camp(events=[{"ts": T0 + 120, "instruction_type": "REVISED_ZONE", "message_id": 4}]),
         [bar(0, 107, 107, 105.5, 106), bar(1, 106, 106.4, 105.8, 106.2), bar(2, 106, 106.2, 105.9, 106)])
ok(r["lanes"]["LANE_A"]["lifecycle"]["current"] == "HUMAN_REVIEW_REQUIRED", "revised zone fails closed")
# invalidation with open position -> human review; without fills -> NO_FILL
r = snap(camp(events=[{"ts": T0 + 120, "instruction_type": "INVALIDATION", "message_id": 5}]),
         [bar(0, 107, 107, 105.5, 106), bar(1, 106, 106.4, 105.8, 106.2), bar(2, 106, 106.2, 105.9, 106)])
ok(r["lanes"]["LANE_A"]["lifecycle"]["current"] == "HUMAN_REVIEW_REQUIRED",
   "invalidation with open position -> review")
r = snap(camp(events=[{"ts": T0 + 60, "instruction_type": "INVALIDATION", "message_id": 6}]),
         [bar(0, 110, 110.5, 109.5, 110), bar(1, 110, 110.2, 109.8, 110)])
ok(r["lanes"]["LANE_A"]["engine"]["campaign_state"] == "NO_FILL", "invalidation before fill -> NO_FILL")
# TP2 + runner + multiple partials
ev_m = [{"ts": T0 + 120, "instruction_type": "TP1_TAKE", "message_id": 7},
        {"ts": T0 + 180, "instruction_type": "TP2_TAKE", "message_id": 8},
        {"ts": T0 + 240, "instruction_type": "HOLD_RUNNER", "message_id": 9}]
r = snap(camp(events=ev_m), [bar(0, 107, 107, 105.5, 106), bar(1, 106.5, 107, 106.2, 106.8),
                             bar(2, 107, 107.5, 106.9, 107.2), bar(3, 107.4, 108, 107.3, 107.9),
                             bar(4, 108, 108.2, 107.8, 108)])
L = r["lanes"]["LANE_A"]
ok(len([s for s in L["engine"]["slices"]]) == 2 and L["lifecycle"]["current"] == "RUNNER_ACTIVE",
   "TP1+TP2 partials banked, runner active, hold-runner inert")
ok(L["engine"]["unrealized_pips_per_unit"] is not None and L["mfe_pips"] is not None,
   "unrealised + MFE present for open campaign")
ok(L["plus50_diagnostic"]["reachable"] is False or L["plus50_diagnostic"]["status"].startswith("DIAGNOSTIC"),
   "+50 module is diagnostic-only")

# ---------- determinism / restart / leakage ------------------------------------------------------
r1 = snap(camp(events=ev_m), bars_all)
r2 = snap(camp(events=ev_m), bars_all)
ok(r1["logical_hash"] == r2["logical_hash"], "identical replay -> identical snapshot hash")
s1 = BarStream()
for b in bars_all:
    s1.ingest(b)
s2 = BarStream()
for b in bars_all:
    s2.ingest(b)
ok(s1.stream_hash() == s2.stream_hash(), "identical stream hash (restart reconstruction)")
r_clamped = snap(camp(), bars_all[:2])
r_full = snap(camp(), bars_all)
ok(r_clamped["logical_hash"] != r_full["logical_hash"]
   and r_clamped["lanes"]["LANE_A"]["lifecycle"]["n_fills"] <= r_full["lanes"]["LANE_A"]["lifecycle"]["n_fills"],
   "clamped replay sees strictly less (no future data leakage)")
led = os.path.join(TMP, "led.jsonl")
rec = {"logical_hash": "a" * 64, "review_only": True, "executable": False,
       "trade_ready": False, "observation_only": True}
ok(guards.append_once(led, dict(rec)) is True and guards.append_once(led, dict(rec)) is False,
   "no duplicate ledger writes")

# ---------- isolation + immutability -------------------------------------------------------------
ok("telethon" not in sys.modules and "module_a_telegram" not in sys.modules,
   "tracker imports no Telegram/listener code")
try:
    guards.assert_clean(dict(r1, quantity=1), "probe")
    ok(False, "forbidden key must fail")
except guards.GuardViolation:
    ok(True, "forbidden execution key rejected in snapshots")
inv = guards.verify_project_invariants()
ok(inv["scorers"] == "UNCHANGED" and inv["pre_marks"] == "FROZEN"
   and inv["gates"] == "PAPER/PREVIEW/False/False" and inv["constitution"] == "FROZEN_RATIFIED",
   "scorer/gate/pre-mark/constitution immutability verified")

# ---------- red-team fix regressions (RT-1..RT-9) -------------------------------------------------
# RT-1 CRITICAL: restart recovery restores full bar history from the ingestion log
ilog = os.path.join(TMP, "ingest.jsonl")
sA = BarStream(ilog)
for b in [bar(0, 107, 107.5, 106.5, 107), bar(1, 106, 106.5, 105.5, 106)]:
    sA.ingest(b)
sB = BarStream(ilog)
ok(sB.restore() == 2 and sB.stream_hash() == sA.stream_hash(),
   "RT-1: BarStream restored from ingestion log — identical stream hash after restart")
rA = tracker_engine.track(setup_rec(camp()), camp(), sA, CONST, T0 + 9999, "SYNTHETIC_TEST")
rB = tracker_engine.track(setup_rec(camp()), camp(), sB, CONST, T0 + 9999, "SYNTHETIC_TEST")
ok(rA["logical_hash"] == rB["logical_hash"], "RT-1: snapshot identical across simulated restart")

# RT-2 MATERIAL: one poison row cannot stall ingestion
badcsv = os.path.join(TMP, "bad.csv")
with open(badcsv, "w", encoding="utf-8") as fh:
    fh.write("time,open,high,low,close\n")
    fh.write(f"{T0},100,101,99,100.5\n")
    fh.write(f"{T0 + 60},100,99,101,100.5\n")           # high < low: poison
    fh.write(f"{T0 + 120},100,101,99,100.5\n")
rpb = ReplayCSVProvider(badcsv)
good = rpb.fetch_completed_bars(0)
ok(len(good) == 2 and len(rpb.row_errors) == 1,
   "RT-2: poison row skipped + recorded; other bars still ingested")

# RT-3 MATERIAL: gap through a stop banks at the (worse) OPEN, tagged GAP_FILL_UNCERTAIN
r = snap(camp(sl="102"), [bar(0, 107, 107, 105.5, 106), bar(1, 98, 98.5, 97.5, 98)])
sl_slice = [s for s in r["lanes"]["LANE_A"]["engine"]["slices"] if s["reason"] == "P21_POSTED_SL"]
ok(sl_slice and sl_slice[0]["exit"] == "98" and "GAP_FILL_UNCERTAIN" in sl_slice[0]["tags"],
   "RT-3: gap-down stop exits at open 98, not level 102, tagged")

# RT-4 MATERIAL: REVISED_STOP is tested against the instruction bar's own range
ev = [{"ts": T0 + 120, "instruction_type": "REVISED_STOP", "message_id": 20, "new_sl": "104"}]
r = snap(camp(sl="90", events=ev),
         [bar(0, 107, 107, 105.5, 106), bar(1, 106, 106.4, 105.8, 106.2),
          bar(2, 105, 105.5, 103.0, 103.4)])            # instruction bar low 103 < 104
ok(any(s["reason"] == "P21_POSTED_SL" for s in r["lanes"]["LANE_A"]["engine"]["slices"]),
   "RT-4: revised stop enforced within its own instruction bar")

# RT-5 MATERIAL: nested unsafe stamps + spaced value smuggling rejected
try:
    guards.assert_clean({"review_only": True, "executable": False, "trade_ready": False,
                         "observation_only": True,
                         "lanes": {"A": {"trade_ready": True}}}, "probe")
    ok(False, "nested trade_ready=True must fail")
except guards.GuardViolation:
    ok(True, "RT-5: nested unsafe stamp rejected")
try:
    guards.assert_clean({"review_only": True, "executable": False, "trade_ready": False,
                         "observation_only": True, "note": "please use lot size 2"}, "probe")
    ok(False, "spaced value smuggling must fail")
except guards.GuardViolation:
    ok(True, "RT-5b: spaced forbidden phrase in value rejected")

# RT-6 MATERIAL: constitution byte-pin enforced at runtime
guards.assert_constitution_frozen()
ok(True, "RT-6: runtime constitution pin passes on frozen file")
_real = guards.CONSTITUTION_SHA
try:
    guards.CONSTITUTION_SHA = "0" * 64
    try:
        guards.assert_constitution_frozen()
        ok(False, "tampered pin must fail")
    except guards.GuardViolation:
        ok(True, "RT-6b: pin mismatch refuses to run")
finally:
    guards.CONSTITUTION_SHA = _real

# RT-7 MATERIAL: INVALIDATION after fully banked -> CLOSED with result standing (not NO_FILL)
ev = [{"ts": T0 + 120, "instruction_type": "TAKE_PCT_OFF", "message_id": 21, "pct": 1.0},
      {"ts": T0 + 180, "instruction_type": "INVALIDATION", "message_id": 22}]
r = snap(camp(events=ev), [bar(0, 107, 107, 105.5, 106), bar(1, 106.5, 107, 106.2, 106.8),
                           bar(2, 107, 107.5, 106.9, 107.2), bar(3, 107.2, 107.4, 107, 107.1)])
ok(r["lanes"]["LANE_A"]["engine"]["campaign_state"] == "CLOSED"
   and r["lanes"]["LANE_A"]["engine"]["realized_pips_per_unit"] != "0.00",
   "RT-7: invalidation after flat keeps CLOSED + realized result")

# RT-8 MATERIAL: near-miss inside the $3 band flagged; ambiguity notes surfaced in lanes
r = snap(camp(sl="102"), [bar(0, 107, 107, 105.5, 106), bar(1, 105, 105.2, 103.5, 104)])
ok(any(x["class"] == "FEED_SENSITIVE_NEAR_MISS" for x in r["lanes"]["LANE_A"]["ambiguities"]),
   "RT-8: SL near-miss within $3 flagged in lane ambiguities")

# RT-9 MATERIAL: interpreter stop-wording safety net + new patterns
sys.path.insert(0, PARENT)
import interpreter                                                 # noqa: E402
F = "seascalperfarouk Posted in 🪙・gold-trades\n\n`Whale` "
ok(interpreter.type_instructions("move sl to 4100")[0]["instruction_type"] == "REVISED_STOP",
   "RT-9a: 'move sl to 4100' -> REVISED_STOP")
ok(interpreter.type_instructions("sl to breakeven")[0]["instruction_type"] == "SL_TO_ENTRY",
   "RT-9b: 'sl to breakeven' -> SL_TO_ENTRY")
ok(any(i["instruction_type"] == "REVISED_ZONE"
       for i in interpreter.type_instructions("new zone 4100-4110")),
   "RT-9c: 'new zone' -> REVISED_ZONE")
c = interpreter.classify(F + "watch the stop here, decision soon")
ok(c["kind"] == "NEEDS_HUMAN_REVIEW", "RT-9d: unrecognized stop wording fails closed to review")

# ---------- R2 TV bar-feed provider (offline: parse/key/cursor logic; no network) ---------------
from providers import R2TvBarProvider                              # noqa: E402
prov = R2TvBarProvider(worker_dir=TMP, instrument="XAUUSD")
ok(prov._key(1784046540 - 1784046540 % 60) == "bars/XAUUSD/1m/202607141629.json",
   "bar-feed key computation (UTC minute)")
_ts = T0
_rec = {"raw_payload": json.dumps({"schema_version": "tv_bar_v1", "event_type": "XAU_1M_BAR",
        "instrument": "XAUUSD", "symbol": "PEPPERSTONE:XAUUSD", "interval": "1",
        "bar_open_time": "2026-07-14T02:13:20Z", "open": 4060.1, "high": 4060.9,
        "low": 4059.8, "close": 4060.5, "volume": 10, "source": "ORANGE_XAUUSD_1M_BAR_FEED_v1",
        "dedup_id": "PEPPERSTONE:XAUUSD/1784000000000"}),
        "event_type": "XAU_1M_BAR", "parse_status": "PARSED"}
from datetime import datetime as _dt, timezone as _tz
_expected = int(_dt.fromisoformat("2026-07-14T02:13:20+00:00").timestamp())
try:
    prov.parse_rec(_rec, _expected, _expected + 90)
    ok(False, "non-boundary bar_open_time must be rejected by validate_bar")
except Exception:
    ok(True, "bar-feed record with non-1m-boundary open time rejected")
_rec2 = json.loads(json.dumps(_rec))
_inner = json.loads(_rec2["raw_payload"]); _inner["bar_open_time"] = "2026-07-14T02:13:00Z"
_rec2["raw_payload"] = json.dumps(_inner)
_e2 = int(_dt.fromisoformat("2026-07-14T02:13:00+00:00").timestamp())
b = prov.parse_rec(_rec2, _e2, _e2 + 90)
ok(b.provider == "PEPPERSTONE_TV_BAR_FEED" and str(b.open) == "4060.1"
   and b.event_ts == _e2 and "TV_ALERT_DELIVERY" in b.quality_flags,
   "bar-feed record parses to a valid MarketBar")
try:
    prov.parse_rec(_rec2, _e2 + 60, _e2 + 90)
    ok(False, "key/timestamp mismatch must fail")
except Exception:
    ok(True, "key vs bar_open_time mismatch rejected (no misplaced bars)")
_rec3 = json.loads(json.dumps(_rec2))
_inner3 = json.loads(_rec3["raw_payload"]); _inner3["instrument"] = "XAUUSD_TEST"
_rec3["raw_payload"] = json.dumps(_inner3)
try:
    prov.parse_rec(_rec3, _e2, _e2 + 90)
    ok(False, "wrong instrument must fail")
except Exception:
    ok(True, "wrong-instrument bar rejected (test bars can never enter XAUUSD state)")

import shutil
shutil.rmtree(TMP, ignore_errors=True)

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    print(f"PASS {PASS} tracker checks")
