"""Isolation: the adapter imports no broker / execution / order-sending / order-management module, and
neither the execution gates nor risk_policy.py are touched by this package."""
from __future__ import annotations
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fixtures import valid_proposal, NOW, QUOTE_CTX  # noqa: F401
from campaign_extractor.alpha_intake import qst_adapter as A  # noqa: F401

_PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ROOT = os.path.dirname(os.path.dirname(_PKG))

FORBIDDEN_MODULES = (
    "order_transport", "order_request_adapter", "network_send", "submission_firewall",
    "management_adapter", "management_transport", "management_firewall", "management_permit",
    "one_shot_permit", "activation_lease", "mint_trading_token", "trade_preflight",
    "demo_preflight_runner", "expected_margin", "ProtoOA",
)


def test_source_imports_no_broker_execution_or_management():
    for f in glob.glob(os.path.join(_PKG, "*.py")):
        src = open(f, encoding="utf-8").read()
        for bad in FORBIDDEN_MODULES:
            assert bad not in src, (os.path.basename(f), bad)
        for tok in ("send_new_order", "send_management", "SerializeToString", "make_permit",
                    "make_lease", "ORDER_SENDING_ENABLED", "execute_one_attempt"):
            assert tok not in src, (os.path.basename(f), tok)


def test_importing_adapter_pulls_in_no_broker_modules():
    # after importing + evaluating, no forbidden module is present in sys.modules
    A.evaluate(valid_proposal(), now_ms=NOW, quote_ctx=QUOTE_CTX)
    loaded = set(sys.modules)
    for bad in ("order_transport", "network_send", "management_transport", "management_adapter",
                "one_shot_permit", "activation_lease", "submission_firewall"):
        assert bad not in loaded, bad


def test_adapter_never_constructs_a_broker_route_or_authority():
    r = A.evaluate(valid_proposal(), now_ms=NOW, quote_ctx=QUOTE_CTX)
    assert r["audit"]["execution_authority"] is False
    assert r["audit"]["origin"]["provider_route"] is None and r["audit"]["origin"]["broker_route"] is None
    # shadow record is not an executable campaign
    assert r["shadow_qualification_record"]["executable_campaign"] is False


def test_execution_gates_unchanged():
    cfg = open(os.path.join(_ROOT, "config.py"), encoding="utf-8").read()
    cc = open(os.path.join(_ROOT, "ctrader_config.py"), encoding="utf-8").read()
    de = open(os.path.join(_ROOT, "campaign_extractor", "demo_executor", "config.py"), encoding="utf-8").read()
    assert "EXECUTION_ENABLED = False" in cfg and "CTRADER_EXECUTION_ENABLED = False" in cc
    assert "ORDER_SENDING_ENABLED = False" in de and "ORDER_MANAGEMENT_ENABLED = False" in de


def test_risk_policy_unchanged_and_not_touched_by_adapter():
    rp = open(os.path.join(_ROOT, "campaign_extractor", "demo_executor", "risk_policy.py"), encoding="utf-8").read()
    assert 'RISK_POLICY_VERSION = "2.0.0"' in rp
    assert "DEFAULT_CAMPAIGN_RISK_PERCENT = 1.0" in rp and "MAX_CAMPAIGN_RISK_PERCENT = 1.0" in rp
    assert "STRIKE_ALLOC = 0.60" in rp and "TRAP_T2_ALLOC = 0.25" in rp and "TRAP_T3_ALLOC = 0.15" in rp
    # the adapter package must not IMPORT or WRITE risk_policy (docstring mentions are fine)
    import re
    for f in glob.glob(os.path.join(_PKG, "*.py")):
        src = open(f, encoding="utf-8").read()
        assert not re.search(r"^\s*(import|from)\s+risk_policy", src, re.M), os.path.basename(f)
        assert "risk_policy" not in src or "open(" not in src.split("risk_policy")[0][-40:]  # no write path
