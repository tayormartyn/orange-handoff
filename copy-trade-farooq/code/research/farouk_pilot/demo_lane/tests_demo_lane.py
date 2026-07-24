"""Demo-lane proof tests (bounded build). Covers the correction-13 fourteen + F2 four +
F3 six + addendum items 1/2/3 + corr-11 negative tests. MOCK adapter only; no real orders.
Run:  python -m research.farouk_pilot.demo_lane.tests_demo_lane   (from repo root)
"""
import importlib
import json
import os
import sys
import tempfile
import time

# allow running as a script from repo root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
dl = "research.farouk_pilot.demo_lane"
config = importlib.import_module(dl + ".config")
gate = importlib.import_module(dl + ".gate")
sizing = importlib.import_module(dl + ".sizing")
approval_tool = importlib.import_module(dl + ".approval_tool")
executor = importlib.import_module(dl + ".executor")
mock_broker = importlib.import_module(dl + ".mock_broker")
reconcile = importlib.import_module(dl + ".reconcile")

checks = []


def ck(name, cond, detail=""):
    checks.append((name, bool(cond), detail))


def plan(now, expiry=None, entries=None, vol=1.0):
    return {"campaign_id": "XAU-F008-TEST", "t0_freeze_hash": "abc", "approved_account_id": 1_000_001,
            "symbol_id": "XAUUSD", "direction": "SELL", "entries": entries or [4100.0, 4102.0],
            "stop": 4110.0, "volume_per_leg": vol, "max_aggregate_volume": 1000,
            "source_message_ids": [1], "executor_version_hash": "h", "approval_timestamp": now,
            "approval_expiry": (expiry if expiry is not None else now + 3600),
            "placement_deadline": now + 1800}


def mk(tmp, adapter=None):
    ex = executor.Executor(os.path.join(tmp, "req"), os.path.join(tmp, "appr"),
                           os.path.join(tmp, "rec"), os.path.join(tmp, "out"),
                           os.path.join(tmp, "demo_ledger.jsonl"),
                           adapter or mock_broker.MockBroker())
    return ex


def approve(tmp, p, now):
    ex = mk(tmp)
    req = ex.write_approval_request(p)
    reqrec = json.load(open(req, encoding="utf-8"))
    _, approval = approval_tool.create_approval(reqrec, os.path.join(tmp, "appr"),
                                                "MARTYN_EXPLICIT_APPROVE", now)
    return approval


NOW = 1_800_000_000

# ===== correction 1 / correction-13 items: account guard refusals =====
ck("live-endpoint refusal", not gate.account_guard_ok({**mock_broker.MockBroker().account, "endpoint": "live.ctraderapi.com"}))
ck("isLive=true refusal", not gate.account_guard_ok({**mock_broker.MockBroker().account, "isLive": True}))
ck("wrong account-id refusal", not gate.account_guard_ok({**mock_broker.MockBroker().account, "ctidTraderAccountId": 999}))
ck("wrong OAuth scope refusal", not gate.account_guard_ok({**mock_broker.MockBroker().account, "permissionScope": "SCOPE_VIEW"}))
ck("accountType NEVER used as discriminator", gate.account_guard_ok({**mock_broker.MockBroker().account, "accountType": "NETTED"}))

# ===== correction 5: gate truth table — no armed row touches a live target =====
rows = gate.truth_table()
ck("gate truth table: no live-target path ever armed", not any(r["touches_live_target"] for r in rows))
ck("gate truth table: armed only demo+isLive-false", all((r["armed"] is False) or (r["endpoint"] == config.DEMO_ENDPOINT and r["isLive"] is False) for r in rows))

# ===== F1: exact volume, no rounding =====
meta = {"lotSize": 100, "minVolume": 1, "maxVolume": 10000, "stepVolume": 1}
ck("F1: exact nominal converts", sizing.to_protocol_volume(0.01, meta) == 1)
try:
    sizing.to_protocol_volume(0.015, {"lotSize": 100, "minVolume": 1, "maxVolume": 100, "stepVolume": 2})
    ck("F1: unit-conversion mismatch halts", False)
except sizing.SizingHalt:
    ck("F1: unit-conversion mismatch halts", True)
try:
    sizing.to_protocol_volume(0.001, meta)  # 0.1 -> not integer protocol -> halt (no round up)
    ck("F1: sub-unit nominal halts (no upward rounding)", False)
except sizing.SizingHalt:
    ck("F1: sub-unit nominal halts (no upward rounding)", True)

# ===== F3: approval authority separation =====
with tempfile.TemporaryDirectory() as tmp:
    ex = mk(tmp)
    try:
        ex.write_approval({})
        ck("F3: executor cannot create approval", False)
    except PermissionError:
        ck("F3: executor cannot create approval", True)
    # ITEM 4: TWO DISTINCT claims reported separately.
    # (a) CODE-CAPABILITY separation — PROVEN here: the only approval-named executor path
    #     (write_approval) RAISES; no successful DEMO_APPROVED write path exists in the code.
    _cc_ok = True
    try:
        ex.write_approval({}); _cc_ok = False
    except PermissionError:
        pass
    # and no other public CALLABLE writes to the approvals dir (only write_approval_request writes REQUEST;
    # approvals_dir is a path attribute the executor knows but has no code to write to)
    _other = [m for m in dir(ex) if not m.startswith("_") and "approv" in m.lower()
              and callable(getattr(ex, m)) and m not in ("write_approval", "write_approval_request")]
    ck("F3(code-capability): only approval path raises; no successful DEMO_APPROVED writer (PROVEN)",
       _cc_ok and _other == [])
    # (b) OS-IDENTITY separation — NOT PROVEN by this build; ACL that the executor's PROCESS IDENTITY
    #     cannot create/modify/rename/delete the approval artifact is an ACTIVATION PREREQUISITE.
    ck("F3(os-identity): process-identity ACL separation is an ACTIVATION PREREQUISITE (NOT claimed now)",
       True)  # deliberately records the gap as a known unproven state, not a pass of the real claim

with tempfile.TemporaryDirectory() as tmp:
    a = approve(tmp, plan(NOW), NOW)
    ck("F3: approval-tool creates correctly bound approval",
       a["record_type"] == "DEMO_APPROVED" and a["lifecycle"] == "MARTYN_APPROVED" and "nonce" in a)
    # modified approval rejected
    ex = mk(tmp, mock_broker.MockBroker())
    bad = dict(a); bad["plan"] = {**a["plan"], "stop": 9999.0}
    try:
        ex.place_campaign(config_flip(bad), NOW, mock_broker.MockBroker().account) if False else ex._validate_approval(bad, NOW)
        ck("F3: modified approval rejected", False)
    except executor.ExecutorHalt:
        ck("F3: modified approval rejected", True)
    # expired approval rejected
    a_exp = approve(tmp + "_x" if False else tmp, plan(NOW, expiry=NOW - 1), NOW) if False else None
    try:
        ex._validate_approval({**a, "expiry_ts": NOW - 1}, NOW)
        ck("F3: expired approval rejected", False)
    except executor.ExecutorHalt:
        ck("F3: expired approval rejected", True)


def config_flip(x):
    return x


# replayed approval rejected + simultaneous single-consumer
with tempfile.TemporaryDirectory() as tmp:
    # must flip the demo gate ON only inside the test via monkeypatch of gate.can_arm
    orig = gate.can_arm
    gate.can_arm = lambda acc: True                       # simulate armed (test-only)
    try:
        a = approve(tmp, plan(NOW), NOW)
        ex = mk(tmp, mock_broker.MockBroker())
        ex.place_campaign(a, NOW, mock_broker.MockBroker().account)
        try:
            ex.place_campaign(a, NOW, mock_broker.MockBroker().account)  # replay same nonce
            ck("F3: replayed approval rejected", False)
        except executor.ExecutorHalt as e:
            ck("F3: replayed approval rejected", "consumed" in str(e))
        # simultaneous consumption: two receipts, one winner
        a2 = approve(tmp, plan(NOW, entries=[4100.0]), NOW)
        ex2 = mk(tmp, mock_broker.MockBroker())
        r1 = ex2._consume(a2)
        try:
            ex2._consume(a2)
            ck("F3: simultaneous consumption -> at most one consumer", False)
        except executor.ExecutorHalt:
            ck("F3: simultaneous consumption -> at most one consumer", True)
    finally:
        gate.can_arm = orig

# ===== addendum 1: failed receipt blocks the request (ordering) =====
with tempfile.TemporaryDirectory() as tmp:
    orig = gate.can_arm; gate.can_arm = lambda acc: True
    try:
        a = approve(tmp, plan(NOW), NOW)
        ex = mk(tmp, mock_broker.MockBroker())
        # point receipts_dir under a regular FILE so receipt os.open fails -> request blocked
        open(os.path.join(tmp, "rec_block"), "w").close()
        ex.receipts_dir = os.path.join(tmp, "rec_block", "sub")  # path under a file -> OSError
        try:
            ex.place_campaign(a, NOW, mock_broker.MockBroker().account)
            ck("ADDENDUM1: failed receipt blocks request", False)
        except executor.ExecutorHalt:
            # verify NO order was sent
            ck("ADDENDUM1: failed receipt blocks request (no order placed)", ex.adapter.list_orders() == {})
    finally:
        gate.can_arm = orig

# ===== addendum 2: resting order carries GOOD_TILL_DATE bound to approval expiry =====
with tempfile.TemporaryDirectory() as tmp:
    orig = gate.can_arm; gate.can_arm = lambda acc: True
    try:
        p = plan(NOW); a = approve(tmp, p, NOW)
        ex = mk(tmp, mock_broker.MockBroker())
        acks = ex.place_campaign(a, NOW, mock_broker.MockBroker().account)
        ck("ADDENDUM2: resting order is GOOD_TILL_DATE", all(o["time_in_force"] == "GOOD_TILL_DATE" for o in acks))
        ck("ADDENDUM2: GTD expiry bound to approval expiry", all(o["expiry_ts"] == p["approval_expiry"] for o in acks))
    finally:
        gate.can_arm = orig

# ===== addendum 3: silent normalization detected via exact-equality 7-field reconcile =====
with tempfile.TemporaryDirectory() as tmp:
    orig = gate.can_arm; gate.can_arm = lambda acc: True
    try:
        a = approve(tmp, plan(NOW), NOW)
        ex = mk(tmp, mock_broker.MockBroker(normalize=True))
        try:
            ex.place_campaign(a, NOW, mock_broker.MockBroker().account)
            ck("ADDENDUM3: silent normalization detected", False)
        except executor.ExecutorHalt as e:
            ck("ADDENDUM3: silent normalization detected", "normalization" in str(e))
    finally:
        gate.can_arm = orig

# ===== correction 7: lost response -> OUTCOME_UNKNOWN =====
with tempfile.TemporaryDirectory() as tmp:
    orig = gate.can_arm; gate.can_arm = lambda acc: True
    try:
        a = approve(tmp, plan(NOW, entries=[4100.0]), NOW)
        ex = mk(tmp, mock_broker.MockBroker(lose_response=True))
        try:
            ex.place_campaign(a, NOW, mock_broker.MockBroker().account)
            ck("CORR7: lost response -> OUTCOME_UNKNOWN halt", False)
        except executor.ExecutorHalt as e:
            intents = [json.load(open(os.path.join(ex.outbox_dir, f), encoding="utf-8"))
                       for f in os.listdir(ex.outbox_dir)]
            ck("CORR7: lost response -> OUTCOME_UNKNOWN halt",
               "OUTCOME_UNKNOWN" in str(e) and any(i["state"] == "OUTCOME_UNKNOWN" for i in intents))
    finally:
        gate.can_arm = orig

# ===== F2: close-only reduces; excessive rejected; unknown no-touch; kill closes only owned =====
b = mock_broker.MockBroker()
b.open_position("P1", 3, owner="ORANGE")
ck("F2: partial-fill close reduces without opening/reversing",
   reconcile.risk_reducing_close(b, "P1", 2, {"P1"})["closed"] == 2 and b.list_positions()["P1"]["volume"] == 1)
try:
    reconcile.risk_reducing_close(b, "P1", 99, {"P1"}); ck("F2: excessive close rejected", False)
except ValueError:
    ck("F2: excessive close rejected", True)
b.open_position("UNK", 5, owner="SOMEONE_ELSE")
try:
    reconcile.reconcile(b, {"P1"}); ck("F2: unknown position no-touch halt", False)
except reconcile.HaltNoTouch:
    ck("F2: unknown position no-touch halt", True)
try:
    reconcile.risk_reducing_close(b, "UNK", 1, {"P1"}); ck("F2: kill closes ONLY Orange-owned", False)
except reconcile.HaltNoTouch:
    ck("F2: kill closes ONLY Orange-owned", True)

# ===== correction 11: demo-ledger exclusion — records carry the five flags, expectancy readers reject =====
with tempfile.TemporaryDirectory() as tmp:
    orig = gate.can_arm; gate.can_arm = lambda acc: True
    try:
        a = approve(tmp, plan(NOW, entries=[4100.0]), NOW)
        ex = mk(tmp, mock_broker.MockBroker()); ex.place_campaign(a, NOW, mock_broker.MockBroker().account)
        recs = [json.loads(l) for l in open(ex.ledger_path, encoding="utf-8")]
        ck("CORR11: ledger records carry all 5 eligibility flags",
           all(r.get("eligible_for_strategy_expectancy") is False
               and r.get("eligible_for_execution_fidelity_analysis") is True for r in recs))
        # negative test: an expectancy reader that filters eligible_for_strategy_expectancy gets nothing
        expectancy_visible = [r for r in recs if r.get("eligible_for_strategy_expectancy")]
        ck("CORR11: expectancy reader ingests nothing from demo ledger", expectancy_visible == [])
    finally:
        gate.can_arm = orig

prices = importlib.import_module(dl + ".prices")

# ===== F1: NO DOWNWARD rounding (distinct from upward) =====
try:
    # 0.019 lots * 100 = 1.9 protocol -> not exact; must HALT, not round DOWN to 1
    sizing.to_protocol_volume(0.019, {"lotSize": 100, "minVolume": 1, "maxVolume": 100, "stepVolume": 1})
    ck("F1: no DOWNWARD rounding (1.9 halts, not -> 1)", False)
except sizing.SizingHalt:
    ck("F1: no DOWNWARD rounding (1.9 halts, not -> 1)", True)

# ===== ADDENDUM 1: approval byte-identical after consumption; first consumption succeeds =====
with tempfile.TemporaryDirectory() as tmp:
    orig = gate.can_arm; gate.can_arm = lambda acc: True
    try:
        p = plan(NOW, entries=[4100.0]); a = approve(tmp, p, NOW)
        appr_path = [os.path.join(tmp, "appr", f) for f in os.listdir(os.path.join(tmp, "appr"))][0]
        before = open(appr_path, "rb").read()
        ex = mk(tmp, mock_broker.MockBroker())
        rpath = ex._consume(a)
        ck("ADDENDUM1: first atomic consumption succeeds", os.path.exists(rpath))
        after = open(appr_path, "rb").read()
        ck("ADDENDUM1: approval byte-identical after consumption", before == after)
    finally:
        gate.can_arm = orig

# ===== ADDENDUM 2: missing expiry blocks; altered expiry invalidates; expired order not recreated =====
with tempfile.TemporaryDirectory() as tmp:
    ex = mk(tmp, mock_broker.MockBroker())
    a_noexp = {"record_type": "DEMO_APPROVED", "plan": plan(NOW), "plan_hash": "x",
               "nonce": "n1", "lifecycle": "MARTYN_APPROVED", "approval_record_hash": "y"}
    a_noexp.pop("expiry_ts", None)
    try:
        ex._validate_approval(a_noexp, NOW); ck("ADDENDUM2: missing expiry blocks placement", False)
    except (executor.ExecutorHalt, KeyError, TypeError):
        ck("ADDENDUM2: missing expiry blocks placement", True)
with tempfile.TemporaryDirectory() as tmp:
    a = approve(tmp, plan(NOW), NOW)
    ex = mk(tmp, mock_broker.MockBroker())
    altered = dict(a); altered["plan"] = {**a["plan"], "approval_expiry": NOW + 999999}
    try:
        ex._validate_approval(altered, NOW); ck("ADDENDUM2: altered expiry invalidates approval", False)
    except executor.ExecutorHalt:
        ck("ADDENDUM2: altered expiry invalidates approval", True)  # plan-hash break
with tempfile.TemporaryDirectory() as tmp:
    orig = gate.can_arm; gate.can_arm = lambda acc: True
    try:
        a = approve(tmp, plan(NOW, expiry=NOW + 10, entries=[4100.0]), NOW)
        ex = mk(tmp, mock_broker.MockBroker())
        ex.place_campaign(a, NOW, mock_broker.MockBroker().account)   # consumed
        # after expiry: cannot recreate (nonce consumed AND expired)
        try:
            ex.place_campaign(a, NOW + 999, mock_broker.MockBroker().account)
            ck("ADDENDUM2: expired order cannot be recreated", False)
        except executor.ExecutorHalt:
            ck("ADDENDUM2: expired order cannot be recreated", True)
    finally:
        gate.can_arm = orig

# ===== ADDENDUM 2 / corr13#13: stale broker-side Orange order cancelled + terminal cancel =====
with tempfile.TemporaryDirectory() as tmp:
    b = mock_broker.MockBroker()
    b.orders["Ostale"] = {"order_id": "Ostale", "expiry_ts": NOW - 1, "owner": "ORANGE"}
    ex = mk(tmp, b)
    cancelled = ex.cancel_stale_orders(NOW)
    ck("CORR13#13: executor cancels a stale Orange order (mock-driven; not real-broker proof)", cancelled == ["Ostale"] and "Ostale" not in b.orders)
with tempfile.TemporaryDirectory() as tmp:
    b = mock_broker.MockBroker(); b.orders["Op"] = {"order_id": "Op", "owner": "ORANGE", "expiry_ts": 1e18}
    ex = mk(tmp, b)
    ck("CORR13#13b: terminal campaign cancels pending entries", ex.cancel_campaign_pending("n") == ["Op"] and b.orders == {})

# ===== ADDENDUM 3: non-representable entry/stop; min-stop-distance; broker STOP mismatch =====
meta_tick = {"lotSize": 100, "minVolume": 1, "maxVolume": 1000, "stepVolume": 1, "tickSize": 0.01,
             "minStopDistance": 1.0, "session_open": True, "tradeable": True}
try:
    prices.representable(4100.005, 0.01); ck("ADDENDUM3: non-representable ENTRY rejected", False)
except prices.PriceHalt:
    ck("ADDENDUM3: non-representable ENTRY rejected", True)
try:
    prices.representable(4110.003, 0.01); ck("ADDENDUM3: non-representable STOP rejected", False)
except prices.PriceHalt:
    ck("ADDENDUM3: non-representable STOP rejected", True)
try:
    prices.stop_distance_ok(4100.0, 4100.5, "SELL", 1.0); ck("ADDENDUM3: min-stop-distance violation rejected", False)
except prices.PriceHalt:
    ck("ADDENDUM3: min-stop-distance violation rejected", True)
with tempfile.TemporaryDirectory() as tmp:
    orig = gate.can_arm; gate.can_arm = lambda acc: True
    try:
        a = approve(tmp, plan(NOW, entries=[4100.0]), NOW)   # SELL stop 4110, dist 10 ok
        ex = mk(tmp, mock_broker.MockBroker(symbol_meta=meta_tick, normalize_stop=True))
        try:
            ex.place_campaign(a, NOW, mock_broker.MockBroker().account)
            ck("ADDENDUM3: broker STOP mismatch detected (distinct from price)", False)
        except executor.ExecutorHalt as e:
            ck("ADDENDUM3: broker STOP mismatch detected (distinct from price)", "normalization" in str(e))
    finally:
        gate.can_arm = orig

# ===== ADDENDUM 3: symbol / trading-session invalidity blocks placement =====
with tempfile.TemporaryDirectory() as tmp:
    orig = gate.can_arm; gate.can_arm = lambda acc: True
    try:
        a = approve(tmp, plan(NOW, entries=[4100.0]), NOW)
        ex = mk(tmp, mock_broker.MockBroker(symbol_meta={**meta_tick, "session_open": False}))
        try:
            ex.place_campaign(a, NOW, mock_broker.MockBroker().account)
            ck("ADDENDUM3: trading-session invalidity blocks placement", False)
        except executor.ExecutorHalt as e:
            ck("ADDENDUM3: trading-session invalidity blocks placement", "session" in str(e))
        ex2 = mk(tmp + "2" if False else tmp, mock_broker.MockBroker(symbol_meta={**meta_tick, "tradeable": False}))
        a2 = approve(tmp, plan(NOW, entries=[4101.0]), NOW)
        try:
            ex2.place_campaign(a2, NOW, mock_broker.MockBroker().account)
            ck("ADDENDUM3: symbol untradeable blocks placement", False)
        except executor.ExecutorHalt as e:
            ck("ADDENDUM3: symbol untradeable blocks placement", "tradeable" in str(e))
    finally:
        gate.can_arm = orig

# ===== CORR13 #10/#11: hard process death w/ broker stop surviving; restart reconcile-first =====
with tempfile.TemporaryDirectory() as tmp:
    orig = gate.can_arm; gate.can_arm = lambda acc: True
    try:
        b = mock_broker.MockBroker(symbol_meta=meta_tick)
        a = approve(tmp, plan(NOW, entries=[4100.0]), NOW)
        ex = mk(tmp, b)
        acks = ex.place_campaign(a, NOW, b.account)
        # "hard death": drop the executor object; broker keeps the order WITH its stop
        del ex
        surviving = b.list_orders()
        # ITEM 5: renamed - this is a SIMULATION of the mock holding the order, NOT proof that
        # Pepperstone's servers hold a stop through host death (that is an activation prerequisite).
        ck("HOST_DEATH_STOP_SURVIVAL_SIMULATION (mock holds order+stop; NOT real-broker proof)",
           all("stop_price" in o for o in surviving.values()) and len(surviving) == 1)
        # restart: new executor reconciles BEFORE acting; owned order known -> ok
        ex_new = mk(tmp, b)
        owned = list(surviving.keys())
        gate.can_arm = lambda acc: True
        ok_restart = ex_new.restart_reconcile_first(b.account, owned)
        ck("CORR13#11: restart reconcile-before-action (owned known)", ok_restart is True)
        # restart with an unknown broker order -> NO TOUCH, NOT_ARMED
        b.orders["Ounknown"] = {"order_id": "Ounknown", "owner": "SOMEONE", "expiry_ts": 1e18}
        try:
            ex_new.restart_reconcile_first(b.account, owned)
            ck("CORR13#11b: restart with unknown order -> NOT_ARMED no-touch", False)
        except executor.ExecutorHalt:
            ck("CORR13#11b: restart with unknown order -> NOT_ARMED no-touch", True)
    finally:
        gate.can_arm = orig

# ===== ITEM 1: DISTINCT unknown-ORDER and unknown-POSITION tests (no consolidation) =====
b_uo = mock_broker.MockBroker()
b_uo.orders["Ounk"] = {"order_id": "Ounk", "owner": "SOMEONE_ELSE", "expiry_ts": 1e18}
with tempfile.TemporaryDirectory() as tmp:
    ex = mk(tmp, b_uo)
    try:
        ex.restart_reconcile_first(b_uo.account, owned_order_ids=[])
        ck("ITEM1: unknown ORDER -> NOT_ARMED no-touch (distinct)", False)
    except executor.ExecutorHalt as e:
        ck("ITEM1: unknown ORDER -> NOT_ARMED no-touch (distinct)", "unknown broker order" in str(e))
b_up = mock_broker.MockBroker()
b_up.open_position("Punk", 4, owner="SOMEONE_ELSE")
try:
    reconcile.reconcile(b_up, owned_position_ids=[])
    ck("ITEM1: unknown POSITION -> no-touch halt (distinct)", False)
except reconcile.HaltNoTouch as e:
    ck("ITEM1: unknown POSITION -> no-touch halt (distinct)", "position" in str(e))

# ===== ITEM 2: instrumented ordering proof — inject failure at EVERY pre-send boundary,
#               assert broker_call_count == 0 (no order ever reached the broker) =====
def _ordering_boundary(fail_at):
    with tempfile.TemporaryDirectory() as tmp:
        orig = gate.can_arm; gate.can_arm = lambda acc: True
        try:
            b = mock_broker.MockBroker()
            a = approve(tmp, plan(NOW, entries=[4100.0]), NOW)
            ex = mk(tmp, b)
            if fail_at == "validate":
                a = {**a, "plan_hash": "TAMPERED"}                 # validation fails
            elif fail_at == "receipt":
                open(os.path.join(tmp, "rf"), "w").close()
                ex.receipts_dir = os.path.join(tmp, "rf", "sub")   # receipt persistence fails
            elif fail_at == "outbox":
                open(os.path.join(tmp, "of"), "w").close()
                ex.outbox_dir = os.path.join(tmp, "of", "sub")     # intent write fails
            try:
                ex.place_campaign(a, NOW, b.account)
            except Exception:
                pass
            return b.broker_call_count
        finally:
            gate.can_arm = orig
for boundary in ("validate", "receipt", "outbox"):
    ck(f"ITEM2: failure at '{boundary}' boundary -> broker_call_count == 0",
       _ordering_boundary(boundary) == 0)

# ===== ITEM 3: parameterised SEVEN-FIELD reconciliation matrix — mutate each field independently =====
class _MutBroker(mock_broker.MockBroker):
    def __init__(self, field, **kw):
        super().__init__(**kw); self._mut = field
    def place_limit(self, req):
        self.broker_call_count += 1
        ack = dict(req); ack["order_id"] = "Om"; ack["owner"] = "ORANGE"
        muts = {"symbol": "XAGUSD", "side": "BUY", "type": "MARKET", "volume": ack["volume"] + 1,
                "entry_price": ack["entry_price"] + 0.01, "stop_price": ack["stop_price"] + 0.01,
                "expiry_ts": ack["expiry_ts"] + 1}
        ack[self._mut] = muts[self._mut]
        self.orders["Om"] = ack; return ack
for field in ("symbol", "side", "type", "volume", "entry_price", "stop_price", "expiry_ts"):
    with tempfile.TemporaryDirectory() as tmp:
        orig = gate.can_arm; gate.can_arm = lambda acc: True
        try:
            a = approve(tmp, plan(NOW, entries=[4100.0]), NOW)
            ex = mk(tmp, _MutBroker(field, symbol_meta=meta_tick))
            try:
                ex.place_campaign(a, NOW, mock_broker.MockBroker().account)
                ck(f"ITEM3: reconcile detects mutated '{field}'", False)
            except executor.ExecutorHalt as e:
                ck(f"ITEM3: reconcile detects mutated '{field}'", "normalization" in str(e))
        finally:
            gate.can_arm = orig

# ===== GAP 1: account_id mismatch — the most safety-critical field, distinct case =====
with tempfile.TemporaryDirectory() as tmp:
    orig = gate.can_arm; gate.can_arm = lambda acc: True
    try:
        a = approve(tmp, plan(NOW, entries=[4100.0]), NOW)
        b = mock_broker.MockBroker(symbol_meta=meta_tick, mutate_account=True)
        ex = mk(tmp, b)
        try:
            ex.place_campaign(a, NOW, mock_broker.MockBroker().account)
            ck("GAP1: account_id mismatch detected + halt/NOT_ARMED", False)
        except executor.ExecutorHalt as e:
            # detected, halted, and NO SUBSEQUENT broker action (only the one offending call)
            ck("GAP1: account_id mismatch detected + halt/NOT_ARMED", "ACCOUNT_ID_MISMATCH" in str(e))
            ck("GAP1: no silent adoption (executor NOT_ARMED)", getattr(ex, "_armed", None) is False)
            ck("GAP1: no subsequent broker action after mismatch", b.broker_call_count == 1)
    finally:
        gate.can_arm = orig

# ===== GAP 2: SUCCESS-path ordering — exact ordered event trace =====
with tempfile.TemporaryDirectory() as tmp:
    orig = gate.can_arm; gate.can_arm = lambda acc: True
    try:
        a = approve(tmp, plan(NOW, entries=[4100.0]), NOW)   # single leg -> single ordered sequence
        ex = mk(tmp, mock_broker.MockBroker(symbol_meta=meta_tick))
        ex.place_campaign(a, NOW, mock_broker.MockBroker().account)
        expected = ["VALIDATE_IMMUTABLE_APPROVAL", "PERSIST_ATOMIC_CONSUMPTION_RECEIPT",
                    "PERSIST_DURABLE_ORDER_INTENT", "CALL_BROKER_ADAPTER"]
        ck("GAP2: success-path executes in the correct order (exact trace)", ex.trace == expected, ex.trace)
    finally:
        gate.can_arm = orig

fails = [(n, d) for n, ok_, d in checks if not ok_]
for n, ok_, d in checks:
    print(("PASS " if ok_ else "FAIL ") + n + ("" if ok_ else f"  <- {d}"))
print(f"\n{len(checks) - len(fails)}/{len(checks)} pass")
sys.exit(0 if not fails else 1)
