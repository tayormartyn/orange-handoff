"""cTrader A1 offline tests (A–O). Temp fixtures only; NO real secret used in assertions;
NO connection; NO credential value printed."""
from __future__ import annotations
import hashlib
import json
import os
import shutil
import sys
import tempfile
import tokenize

_HERE = os.path.dirname(os.path.abspath(__file__))
_A1 = os.path.dirname(_HERE)
_CE = os.path.dirname(_A1)
_ROOT = os.path.dirname(_CE)
for p in (_A1, _CE):
    if p not in sys.path:
        sys.path.insert(0, p)

import dotenv_loader as DL
import masked_presence as MP
import scope_validator as SV
import account_validator as AV
import secret_scan as SS
from broker_readonly.source_scan import scan_no_order_code, scan_secret_leaks

A1_SOURCES = ("__init__.py", "dotenv_loader.py", "masked_presence.py", "scope_validator.py",
              "account_validator.py", "secret_scan.py", "run_a1.py")


def _write_env(tmp, lines):
    p = os.path.join(tmp, ".env")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return p


# ===================================================== A — authoritative path resolution
def test_A_path_resolution():
    assert DL.ENV_PATH == os.path.join(_ROOT, ".env")          # explicit, no parent walking
    tmp = tempfile.mkdtemp(prefix="a1A_")
    try:
        p = _write_env(tmp, ["CTRADER_CLIENT_ID=PLACEHOLDER_CLIENT_ID  # set in Windows Credential Manager / DPAPI",
                             "TELEGRAM_API_ID=999"])
        env = DL.load_ctrader_env(p)
        assert "CTRADER_CLIENT_ID" in env and "TELEGRAM_API_ID" not in env   # isolated
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== B — missing credential fails closed
def test_B_missing_fails_closed():
    tmp = tempfile.mkdtemp(prefix="a1B_")
    try:
        env = DL.load_ctrader_env(_write_env(tmp, ["CTRADER_ENV=demo"]))
        assert MP.presence("CTRADER_CLIENT_ID", env) == "MISSING"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== C — empty credential fails closed
def test_C_empty_fails_closed():
    tmp = tempfile.mkdtemp(prefix="a1C_")
    try:
        env = DL.load_ctrader_env(_write_env(tmp, ["CTRADER_CLIENT_SECRET="]))
        assert MP.presence("CTRADER_CLIENT_SECRET", env) == "EMPTY"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== D — masked presence reveals no value
def test_D_masked_no_value():
    secret = "ZZTOPSECRETvalue1234567890"
    env = {"CTRADER_CLIENT_SECRET": secret, "CTRADER_CLIENT_ID": "PLACEHOLDER_CLIENT_ID  # set in Windows Credential Manager / DPAPI"}
    for name in env:
        st = MP.presence(name, env)
        assert st in MP.STATES                  # only an enum is returned
        assert st != env[name] and secret not in st and env[name] not in st
    # malformed shape is classified without echoing the value
    assert MP.presence("CTRADER_CLIENT_ID", {"CTRADER_CLIENT_ID": "not-an-id"}) == "MALFORMED_FORMAT"


# ===================================================== E/F/G — scope validation
def test_E_scope_view_accepted():
    assert SV.returned_scope_is_view_only("SCOPE_VIEW") is True
    assert SV.requested_oauth_scope() == "accounts"            # 'view' -> 'accounts', never 'trading'


def test_F_scope_trade_rejected():
    assert SV.returned_scope_is_view_only("SCOPE_TRADE") is False


def test_G_scope_unknown_missing_malformed_rejected():
    for bad in ("SCOPE_VIEW SCOPE_TRADE", "", None, "scope_view", "SCOPE_UNKNOWN",
                " SCOPE_VIEW ", "VIEW", "SCOPE_TRADE SCOPE_VIEW"):
        assert SV.returned_scope_is_view_only(bad) is False


# ===================================================== H — isLive=true rejected
def test_H_islive_true_rejected():
    v = AV.validate_demo_selection([{"account_id": "L1", "isLive": True}])
    assert v["status"] == "REJECTED_LIVE_ONLY" and v["selected"] is None


# ===================================================== I — multiple demo -> human selection
def test_I_multiple_demo_human_selection():
    v = AV.validate_demo_selection([{"account_id": "D1", "isLive": False},
                                    {"account_id": "D2", "isLive": False},
                                    {"account_id": "L1", "isLive": True}])
    assert v["status"] == "NEEDS_HUMAN_SELECTION"
    assert set(v["candidates"]) == {"D1", "D2"} and v["selected"] is None


# ===================================================== J — no account id guessed
def test_J_no_account_guessed():
    for accts in ([], [{"account_id": "D1", "isLive": False}],
                  [{"account_id": "D1", "isLive": False}, {"account_id": "D2", "isLive": False}]):
        assert AV.validate_demo_selection(accts)["selected"] is None
    single = AV.validate_demo_selection([{"account_id": "D1", "isLive": False}])
    assert single["status"] == "SINGLE_DEMO_CANDIDATE" and single["selected"] is None


# ===================================================== K — execution locks remain false
def test_K_execution_locks_false():
    cfg = open(os.path.join(_ROOT, "config.py"), encoding="utf-8").read()
    assert 'MODE = "PAPER"' in cfg and "EXECUTION_ENABLED = False" in cfg
    assert 'LISTENER_MODE = "PREVIEW"' in cfg
    assert "CTRADER_EXECUTION_ENABLED = False" in open(
        os.path.join(_ROOT, "ctrader_config.py"), encoding="utf-8").read()


# ===================================================== L — no order path callable
def test_L_no_order_path():
    assert scan_no_order_code([os.path.join(_CE, "broker_readonly"), _A1]) == []
    from broker_readonly.adapter import BrokerReadOnlyAdapter
    banned = {"place_order", "submit_order", "create_order", "modify_order", "cancel_order",
              "close_position", "execute_trade"}
    assert banned.isdisjoint(dir(BrokerReadOnlyAdapter))


# ===================================================== M — no external connection
def _names(name):
    s = set()
    with open(os.path.join(_A1, name), "rb") as f:
        for tok in tokenize.tokenize(f.readline):
            if tok.type == tokenize.NAME:
                s.add(tok.string)
    return s


def test_M_no_external_connection():
    forbidden = {"socket", "ssl", "urllib", "requests", "websocket", "telethon",
                 "TelegramClient", "iter_download", "download_media", "connect", "iter_messages"}
    for name in A1_SOURCES:
        bad = forbidden & _names(name)
        assert not bad, f"{name} has forbidden network reference {bad}"


# ===================================================== N — Telegram + 5C untouched (no wiring)
def test_N_listener_and_5c_untouched():
    src = open(os.path.join(_ROOT, "module_a_telegram.py"), encoding="utf-8").read()
    assert "ctrader_a1" not in src                  # A1 not wired into the listener
    sys.path.insert(0, _CE)
    from media_capture import config as mc
    assert mc.TELEGRAM_MEDIA_CAPTURE_ENABLED is True   # media capture still enabled
    for db in ("prospective/data/prospective_evidence_v1.db",
               "prospective/data/prospective_media_v1.db"):
        assert os.path.exists(os.path.join(_CE, db))


# ===================================================== O — protected truth unchanged
def test_O_protected_truth():
    import importlib
    sys.path.insert(0, _CE)
    E = importlib.import_module("extractor")
    art = (E.SYSTEM_PROMPT + "\n----USER_TEMPLATE----\n" + E._USER_TEMPLATE
           + "\n----VERSION----\n" + E.PROMPT_VERSION)
    assert hashlib.sha256(art.encode()).hexdigest() == \
        "95bbf6a4b18ebdd7fc4db2a3e1449ab2e7b7e65a7cf16da461d8ea251a802ef4"
    locks = {"fixture_2026-06-17.json": "c8b1c3ebfb46441e113570f798e951ffce35829c4e4b50a052f9c2b8eba20339",
             "fixture_2026-06-24.json": "a230ce7a704b2d301a00451f91c472a30a77f042dbabd9e47c1888ae3bcba4a2",
             "fixture_2026-06-25.json": "22041d7aeb06bd373c21e23cab42eaf8d422b4913625da518bd3dd6d4c649bce"}
    for name, h in locks.items():
        with open(os.path.join(_CE, "phase0", "fixtures", name), encoding="utf-8") as f:
            fx = json.load(f)
        payload = {"authored_campaigns": fx["authored_campaigns"],
                   "expected_truth": {m["message_id"]: m["expected_truth"] for m in fx["messages"]}}
        assert hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
                              ).hexdigest() == h
