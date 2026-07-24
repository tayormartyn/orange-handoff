"""Order-adapter proof tests (mock-first) - incl. Chuck bounded-fix 1 (emergency-unwind ordering)
and bounded-fix 2 (production gate authority). Proven entirely against MockOrderChannel: no network,
no ctrader_open_api, no real orders; gates stay hard False (arming stubbed in-test via gate.can_arm).
Run:  python -m research.farouk_pilot.demo_lane.tests_order_adapter   (from repo root)
"""
import importlib
import inspect
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
dl = "research.farouk_pilot.demo_lane"
config = importlib.import_module(dl + ".config")
gate = importlib.import_module(dl + ".gate")
approval_tool = importlib.import_module(dl + ".approval_tool")
executor = importlib.import_module(dl + ".executor")
oa = importlib.import_module(dl + ".order_adapter")
moc = importlib.import_module(dl + ".mock_order_channel")
sizing = importlib.import_module(dl + ".sizing")

_p = _f = 0
def ck(name, cond):
    global _p, _f
    print(("  ok  " if cond else "FAIL  ") + name)
    _p += bool(cond); _f += (not cond)

def raises(thunk, exc):
    try:
        thunk(); return False
    except exc:
        return True

NOW = 1000
FAR = 10 ** 12


def make_plan(entries=(4063.00, 4058.00, 4053.00), stop=4040.00, direction="BUY", account_id=47758849):
    return {"record_type": "DEMO_APPROVAL_REQUEST", "campaign_id": "XAU-DEMO-TEST",
            "t0_freeze_hash": "hash0", "approved_account_id": account_id, "symbol_id": "XAUUSD",
            "direction": direction, "entries": list(entries), "stop": stop, "volume_per_leg": 0.01,
            "max_aggregate_volume": 300, "source_message_ids": [1, 2], "executor_version_hash": "h",
            "approval_timestamp": NOW, "approval_expiry": FAR, "placement_deadline": FAR}


def make_executor(channel, *, dispatch=True, **plan_kw):
    d = tempfile.mkdtemp(prefix="oa_test_")
    approvals = os.path.join(d, "approvals")
    _, approval = approval_tool.create_approval(make_plan(**plan_kw), approvals, "MARTYN_EXPLICIT_APPROVE", NOW)
    policy = oa.test_only_policy(True) if dispatch else oa.production_policy()
    adapter = oa.RealOrderAdapter(channel, policy)
    ex = executor.Executor(os.path.join(d, "req"), approvals, os.path.join(d, "rcpt"),
                           os.path.join(d, "out"), os.path.join(d, "ledger.jsonl"), adapter)
    return ex, approval


def armed(fn):
    orig = gate.can_arm
    gate.can_arm = lambda acc: True                # test-only arming; config gate stays False
    try:
        return fn()
    finally:
        gate.can_arm = orig


base_req = {"account_id": 47758849, "symbol": "XAUUSD", "side": "BUY", "type": "LIMIT",
            "volume": 100, "entry_price": 4063.00, "stop_price": 4040.00, "expiry_ts": FAR,
            "time_in_force": "GOOD_TILL_DATE"}

# ================= GATES stay hard False =================
ck("config gates all hard False", not config.EXECUTION_ENABLED and not config.CTRADER_EXECUTION_ENABLED
   and not config.DEMO_EXECUTION_ENABLED)
ex, appr = make_executor(moc.MockOrderChannel())
ck("place_campaign REFUSES (NOT_ARMED) with the real hard-False gate",
   raises(lambda: ex.place_campaign(appr, NOW, {}), executor.ExecutorHalt))

# ================= item 2: PRODUCTION GATE AUTHORITY =================
mock = moc.MockOrderChannel()
ck("for_production dispatch is NOT_ARMED while authoritative gates are False",
   raises(lambda: oa.RealOrderAdapter.for_production(mock).place_limit(base_req), oa.AdapterGateRefused))
ck("for_production takes NO 'enabled' override (only 'channel')",
   list(inspect.signature(oa.RealOrderAdapter.for_production).parameters) == ["channel"])
os.environ["DEMO_EXECUTION_ENABLED"] = "1"          # CLI/env override attempt
ck("env/CLI override does NOT enable production dispatch",
   raises(lambda: oa.RealOrderAdapter.for_production(moc.MockOrderChannel()).place_limit(base_req), oa.AdapterGateRefused))
del os.environ["DEMO_EXECUTION_ENABLED"]
ck("test-only enabled policy WORKS with a MockOrderChannel",
   oa.RealOrderAdapter(moc.MockOrderChannel(), oa.test_only_policy(True)).place_limit(base_req) is not None)
class _NotMock:  # a non-mock channel
    def send_open(self, spec): return {}
ck("test-only enabled policy REFUSES a non-mock channel",
   raises(lambda: oa.RealOrderAdapter(_NotMock(), oa.test_only_policy(True)).place_limit(base_req), oa.AdapterGateRefused))
ck("gates still hard False after item-2 tests", not config.EXECUTION_ENABLED
   and not config.CTRADER_EXECUTION_ENABLED and not config.DEMO_EXECUTION_ENABLED)

# ================= translation / sizing =================
ad = oa.RealOrderAdapter(moc.MockOrderChannel(), oa.test_only_policy(True))
ck("translate builds a LIMIT+GTD+stop spec", (lambda s: s.order_type == "LIMIT"
   and s.time_in_force == "GOOD_TILL_DATE" and s.stop_loss == 4040.00 and s.volume == 100)(ad.translate(base_req)))
ck("LIMIT-only: non-LIMIT opening rejected", raises(lambda: ad.translate({**base_req, "type": "MARKET"}), oa.AdapterHalt))
ck("missing protective stop rejected", raises(lambda: ad.translate({**base_req, "stop_price": None}), oa.AdapterHalt))
ck("exact sizing 0.01 lot -> 100 protocol volume (ratified meta)",
   sizing.to_protocol_volume(0.01, moc.RATIFIED_XAUUSD_META) == 100)

# ================= HAPPY PATH =================
def happy():
    ex, appr = make_executor(moc.MockOrderChannel(fill_mode="PENDING"))
    res = ex.place_campaign(appr, NOW, {})
    ck("happy: 3 legs placed, vol 100 each, stop attached, no alarm",
       len(res) == 3 and all(a["volume"] == 100 and a["stop_attached"] for a in res) and ex._alarms == [])
armed(happy)

# ================= reconciliation (executor single source) =================
def reconc(name, **flags):
    ex, appr = make_executor(moc.MockOrderChannel(fill_mode="PENDING", **flags), entries=(4063.00,))
    ck(name, raises(lambda: ex.place_campaign(appr, NOW, {}), executor.ExecutorHalt))
armed(lambda: reconc("silent ENTRY normalization -> halt", normalize_entry=True))
armed(lambda: reconc("silent STOP normalization -> halt", normalize_stop=True))
def acct():
    ex, appr = make_executor(moc.MockOrderChannel(mutate_account=True, fill_mode="PENDING"), entries=(4063.00,))
    ck("account-id mismatch (GAP1) -> halt + NOT_ARMED",
       raises(lambda: ex.place_campaign(appr, NOW, {}), executor.ExecutorHalt) and ex._armed is False)
armed(acct)
armed(lambda: reconc("lost response -> OUTCOME_UNKNOWN halt", lose_response=True))
armed(lambda: reconc("session closed -> blocked", session_open=False))
armed(lambda: reconc("symbol untradeable -> blocked", tradeable=False))

# ================= 6a-1: STOP-ATTACHMENT FAILURE, PARTIAL fill (cancel-before-close) =============
def sixa1_partial():
    ch = moc.MockOrderChannel(reject_stop=True, fill_mode="PARTIAL", partial_volume=40)
    ex, appr = make_executor(ch, entries=(4063.00,))
    ck("6a-1 partial+no-stop -> UNPROTECTED halt", raises(lambda: ex.place_campaign(appr, NOW, {}), executor.ExecutorHalt))
    ck("6a-1 CANCEL happens BEFORE CLOSE (event trace order)",
       "CANCEL_REMAINING_ENTRY" in ex.trace and "CLOSE_CURRENT_FILLED_QUANTITY" in ex.trace
       and ex.trace.index("CANCEL_REMAINING_ENTRY") < ex.trace.index("CLOSE_CURRENT_FILLED_QUANTITY"))
    ck("6a-1 cancellation confirmed + zero-verify in trace",
       "CONFIRM_CANCELLATION" in ex.trace and "VERIFY_ZERO_PENDING_AND_POSITION" in ex.trace)
    ck("6a-1 CONFIRMED CONTAINMENT: zero pending AND zero position",
       len(ch.list_orders()) == 0 and len(ch.list_positions()) == 0)
    ck("6a-1 alarm raised", any(a["alarm"] == "UNPROTECTED_POSITION_PREVENTED" for a in ex._alarms))
    ck("6a-1 not reconcile-only (containment achieved)", ex._reconcile_only is False)
armed(sixa1_partial)

# ================= 6a: CANCELLATION-OUTCOME-UNKNOWN -> reconciliation, NOT false containment =====
def cancel_unknown():
    ch = moc.MockOrderChannel(reject_stop=True, fill_mode="PARTIAL", partial_volume=40, cancel_outcome_unknown=True)
    ex, appr = make_executor(ch, entries=(4063.00,))
    ck("6a cancel-unknown -> halt", raises(lambda: ex.place_campaign(appr, NOW, {}), executor.ExecutorHalt))
    ck("6a cancel-unknown enters RECONCILE_ONLY (no false containment)", ex._reconcile_only is True)
    ck("6a cancel-unknown did NOT close (no CLOSE in trace)", "CLOSE_CURRENT_FILLED_QUANTITY" not in ex.trace)
    ck("6a cancel-unknown: filled position still present (not falsely contained)", len(ch.list_positions()) == 1)
    ck("6a cancel-unknown alarm is CANCELLATION_OUTCOME_UNKNOWN",
       any(a["alarm"] == "CANCELLATION_OUTCOME_UNKNOWN_RECONCILE_ONLY" for a in ex._alarms))
armed(cancel_unknown)

# ================= 6a: FULLY-FILLED, NO REMAINDER -> close-only branch (no cancel) ===============
def fully_filled():
    ch = moc.MockOrderChannel(reject_stop=True, fill_mode="FULL")
    ex, appr = make_executor(ch, entries=(4063.00,))
    ck("6a full-fill no-stop -> UNPROTECTED halt", raises(lambda: ex.place_campaign(appr, NOW, {}), executor.ExecutorHalt))
    ck("6a full-fill follows CLOSE-ONLY branch (close present, NO cancel)",
       "CLOSE_CURRENT_FILLED_QUANTITY" in ex.trace and "CANCEL_REMAINING_ENTRY" not in ex.trace)
    ck("6a full-fill: zero position after close", len(ch.list_positions()) == 0)
    ck("6a full-fill alarm raised", any(a["alarm"] == "UNPROTECTED_POSITION_PREVENTED" for a in ex._alarms))
armed(fully_filled)

# ================= 6a-1b: PURE PENDING, no fill -> cancel-only (no close) ========================
def pending_only():
    ch = moc.MockOrderChannel(reject_stop=True, fill_mode="PENDING")
    ex, appr = make_executor(ch, entries=(4063.00,))
    ck("6a-1b pending+no-stop -> UNPROTECTED halt", raises(lambda: ex.place_campaign(appr, NOW, {}), executor.ExecutorHalt))
    ck("6a-1b cancel-only (cancel present, NO close)",
       "CANCEL_REMAINING_ENTRY" in ex.trace and "CLOSE_CURRENT_FILLED_QUANTITY" not in ex.trace)
    ck("6a-1b pending cancelled, no position ever opened", len(ch.list_orders()) == 0 and len(ch.list_positions()) == 0)
armed(pending_only)

# ================= close-ONLY risk reduction =================
def close_only():
    ch = moc.MockOrderChannel()
    ch.positions["P1"] = {"volume": 100, "owner": "ORANGE"}
    ad = oa.RealOrderAdapter(ch, oa.test_only_policy(True))
    ck("close_reduce reduces owned", ad.close_reduce("P1", 30)["closed"] == 30 and ch.positions["P1"]["volume"] == 70)
    ck("close_reduce over-close refused", raises(lambda: ad.close_reduce("P1", 9999), ValueError))
    ck("close_reduce non-existent refused", raises(lambda: ad.close_reduce("NOPE", 1), ValueError))
    ch.positions["P2"] = {"volume": 50, "owner": "SOMEONE_ELSE"}
    ck("close_reduce non-owned -> no touch", raises(lambda: ad.close_reduce("P2", 1), PermissionError))
close_only()

# ================= import-safety + single-source principle =================
ck("no ctrader_open_api imported", "ctrader_open_api" not in sys.modules)
ck("no twisted imported", "twisted" not in sys.modules)
_ad_src = open(os.path.join(os.path.dirname(__file__), "order_adapter.py"), encoding="utf-8").read()
_ex_src = open(os.path.join(os.path.dirname(__file__), "executor.py"), encoding="utf-8").read()
ck("adapter does NOT duplicate the seven-field reconciliation (single source in executor)",
   "seven = (" not in _ad_src and "SILENT_NORMALIZATION" not in _ad_src)
ck("the seven-field reconciliation lives in the executor", "seven = (" in _ex_src)

print(f"\n{_p} passed, {_f} failed")
sys.exit(1 if _f else 0)
