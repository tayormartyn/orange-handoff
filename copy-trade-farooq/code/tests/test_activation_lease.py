"""One-attempt activation lease + automatic relock tests. NO order is sent; the send state always
returns to disabled. Fake/offline only."""
from __future__ import annotations
import os
import sys
import tempfile

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DE = os.path.join(_ROOT, "campaign_extractor", "demo_executor")
for p in (_ROOT, _DE):
    if p not in sys.path:
        sys.path.insert(0, p)

import config as CFG
import activation_lease as AL
import one_shot_permit as OSP
import mint_trading_token as MTT
import trade_preflight as TP

NOW = 1_800_000_000_000
BIND = dict(account_id=4257941, signal_id="sig-1", proposal_id="demoprop-x", client_order_id="cli-abc",
            permit_id="permit-1")


def _lease(**o):
    d = dict(now_ms=NOW)
    d.update(BIND)
    d.update(o)
    return AL.make_lease(**d)


def _exec(lease, send_fn, state=None, **over):
    kw = dict(send_fn=send_fn, state=state or AL.LeaseState(), now_ms=NOW)
    kw.update(BIND)
    kw.update(over)
    return AL.execute_one_attempt(lease, **kw)


def _sf(final_state):
    return lambda order_sending_enabled: {"final_state": final_state}


def _raiser(order_sending_enabled):
    raise RuntimeError("boom")


# ---- trading-scope OAuth config / preflight ----
def test_trading_scope_config_ready():
    cfg = MTT.evaluate_config(client_id_present=True, client_secret_present=True,
                              redirect="http://localhost/", scope="trading",
                              token_endpoint="https://openapi.ctrader.com/apps/token")
    assert cfg["ready"] and cfg["scope_trading"].startswith("trading") and cfg["no_live_fallback"] is True
    assert MTT.evaluate_config(client_id_present=True, client_secret_present=True,
                               redirect="http://localhost/", scope="accounts",
                               token_endpoint="https://openapi.ctrader.com/apps/token")["ready"] is False


def test_trade_preflight_scope_gate():
    st = lambda scope: (lambda: {"account_id": 4257941, "is_live": False, "currency": "GBP",
                                 "balance": 10000.0, "permission_scope": scope, "environment": "DEMO"})
    assert TP.preflight_trade_permission(fetch_account_state=st("SCOPE_TRADE"),
                                         endpoint_host="demo.ctraderapi.com")["ok"]
    assert not TP.preflight_trade_permission(fetch_account_state=st("SCOPE_VIEW"),
                                             endpoint_host="demo.ctraderapi.com")["ok"]
    assert not TP.preflight_trade_permission(fetch_account_state=st("SCOPE_TRADE"),
                                             endpoint_host="live.ctraderapi.com")["ok"]


# ---- lease binding / single-use / expiry ----
def test_lease_proposal_bound():
    r = _exec(_lease(), _sf("ORDER_ACCEPTED"), proposal_id="OTHER")
    assert not r["attempted"] and r["reason"] == "PROPOSAL_MISMATCH" and r["order_sending_enabled_after"] is False


def test_lease_permit_bound():
    r = _exec(_lease(), _sf("ORDER_ACCEPTED"), permit_id="OTHER")
    assert not r["attempted"] and r["reason"] == "PERMIT_ID_MISMATCH"


def test_lease_single_attempt_only():
    state = AL.LeaseState()
    lease = _lease()
    r1 = _exec(lease, _sf("ORDER_ACCEPTED"), state=state)
    r2 = _exec(lease, _sf("ORDER_ACCEPTED"), state=state)
    assert r1["attempted"] and r2["attempted"] is False and r2["reason"] == "LEASE_ALREADY_CONSUMED"


def test_lease_expired_rejected():
    lease = _lease(now_ms=NOW - AL.LEASE_TTL_MS - 5000)
    r = _exec(lease, _sf("ORDER_ACCEPTED"), now_ms=NOW)
    assert not r["attempted"] and r["reason"] == "LEASE_EXPIRED"


# ---- automatic relock in EVERY terminal path + exception ----
def test_relock_on_every_terminal_state():
    for st in ("ORDER_ACCEPTED", "ORDER_REJECTED", "ORDER_RECONCILIATION_REQUIRED",
               "BROKER_STATE_MISMATCH", "AUTHENTICATION_FAILURE"):
        state = AL.LeaseState()
        lease = _lease()
        r = _exec(lease, _sf(st), state=state)
        assert r["attempted"] and r["final_state"] == st
        assert r["order_sending_enabled_after"] is False and r["activation_lease"] == "CONSUMED_OR_CLOSED"
        assert r["send_gate"] == "DISABLED" and state.is_closed(lease.lease_id)


def test_relock_on_network_exception():
    state = AL.LeaseState()
    lease = _lease()
    r = _exec(lease, _raiser, state=state)
    assert r["attempted"] and r["final_state"] == "NETWORK_EXCEPTION"
    assert r["order_sending_enabled_after"] is False and state.is_closed(lease.lease_id)
    assert CFG.ORDER_SENDING_ENABLED is False           # persistent gate never left True


# ---- replay / emergency-disable ----
def test_replay_rejected():
    r = _exec(_lease(), _sf("ORDER_ACCEPTED"), fresh_signal=False)
    assert not r["attempted"] and r["reason"] == "STALE_OR_REPLAY_SIGNAL_INELIGIBLE"


def test_emergency_disable_overrides_permit_and_lease():
    tmp = tempfile.mkdtemp()
    try:
        df = os.path.join(tmp, "DEMO_EXECUTION_DISABLED"); open(df, "w").write("x")
        # lease blocked by disable file
        r = _exec(_lease(), _sf("ORDER_ACCEPTED"), disable_path=df)
        assert not r["attempted"] and r["reason"] == "EMERGENCY_DISABLE_FILE_OVERRIDES_EVERYTHING"
        # one-shot permit also blocked by the same disable file
        ok, reason = OSP.validate_permit(
            OSP.make_permit(account_id=4257941, signal_id="sig-1", proposal_id="demoprop-x",
                            client_order_id="cli-abc", now_ms=NOW),
            account_id=4257941, signal_id="sig-1", proposal_id="demoprop-x", client_order_id="cli-abc",
            now_ms=NOW, store=OSP.PermitStore(), disable_path=df)
        assert not ok and reason == "EMERGENCY_DISABLE_FILE_OVERRIDES_EVERYTHING"
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


# ---- permit remains independently required (via the real network gate inside send_fn) ----
def test_permit_still_required_inside_send_fn():
    import network_send as NS
    from models import AccountSnapshot, ApprovedDemoOrderRequest
    import order_transport as OT

    cid = OT.make_client_order_id("sig-1", "demoprop-x", 4257941, 41)
    app = ApprovedDemoOrderRequest("sig-1", "demoprop-x", cid, 4257941, 41, "XAUUSD", "BUY", "LIMIT",
                                   1200, 12, 0.12, 4116.55, None, 4111.55, None, "ST-FAROUK",
                                   "signal=sig-1;proposal=demoprop-x;leg=1", 47.40, 0.005, 390.25, NOW)

    class FT:
        def __init__(self): self.sends = []
        def find_order_by_client_id(self, c): return None
        def send(self, r): self.sends.append(r); return {}
    ft = FT()

    def send_fn(order_sending_enabled):
        return NS.send_new_order(approved=app, transport=ft, account=AccountSnapshot(4257941, False, 10000.0, "GBP", "trade", "DEMO"),
                                 endpoint_host="demo.ctraderapi.com", endpoint_port=5035, permission_scope="SCOPE_TRADE",
                                 permit=None, permit_store=OSP.PermitStore(), quote_fresh=True, signal_fresh=True,
                                 proposal_unexpired=True, replay_status="LIVE", human_approval_completed=True,
                                 order_sending_enabled=order_sending_enabled, now_ms=NOW)
    lease = AL.make_lease(account_id=4257941, signal_id="sig-1", proposal_id="demoprop-x",
                          client_order_id=cid, permit_id="permit-1", now_ms=NOW)
    r = AL.execute_one_attempt(lease, send_fn=send_fn, state=AL.LeaseState(), account_id=4257941,
                               signal_id="sig-1", proposal_id="demoprop-x", client_order_id=cid,
                               permit_id="permit-1", now_ms=NOW)
    # lease granted the attempt, but the network gate still blocked on the missing one-shot permit
    assert r["attempted"] and r["result"]["reason"] == "NETWORK_GATE_BLOCKED" and ft.sends == []
    assert r["order_sending_enabled_after"] is False


# ---- safety ----
def test_no_amend_close_cancel_and_locks():
    import glob
    for pth in glob.glob(os.path.join(_DE, "*.py")):
        if os.path.basename(pth) == "management_adapter.py":
            continue  # authorised gated management adapter (this build)
        src = open(pth, encoding="utf-8").read()
        for bad in ("ProtoOAAmendPositionSLTPReq", "ProtoOAClosePositionReq", "ProtoOACancelOrderReq",
                    "ProtoOAAmendOrderReq"):
            assert bad not in src
    assert CFG.ORDER_SENDING_ENABLED is False
