"""Tests for READ_ONLY_DEMO_PREFLIGHT_v0_1. No network, no OAuth, no order code.
Run:  python research/farouk_pilot/demo_lane/preflight/tests_preflight.py
"""
import os
import re
import sys
import tempfile

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from research.farouk_pilot.demo_lane.preflight import (          # noqa: E402
    preflight_config as cfg, verify, metadata, conversions, credentials, acl, preflight)
from research.farouk_pilot.demo_lane.preflight.mock_read_broker import MockReadOnlyBroker  # noqa: E402

_passed = 0
_failed = 0


def check(name, cond):
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  ok  {name}")
    else:
        _failed += 1
        print(f"FAIL  {name}")


# ---------------- verification ----------------
def good_account(**over):
    a = {"endpoint": "demo.ctraderapi.com", "isLive": False, "ctidTraderAccountId": 1_000_001,
         "broker_environment": "PEPPERSTONE_DEMO", "permissionScope": "SCOPE_VIEW"}
    a.update(over)
    return a


check("verify: good view-only account passes", verify.check(good_account())["ok"] is True)
check("verify: live endpoint refused",
      verify.check(good_account(endpoint="live.ctraderapi.com"))["ok"] is False)
check("verify: isLive True refused", verify.check(good_account(isLive=True))["ok"] is False)
check("verify: wrong account id refused",
      verify.check(good_account(ctidTraderAccountId=9))["ok"] is False)
check("verify: wrong broker env refused",
      verify.check(good_account(broker_environment="OTHER"))["ok"] is False)
check("verify: SCOPE_TRADE grant is NOT view-only-ok",
      verify.check(good_account(permissionScope="SCOPE_TRADE"))["ok"] is False)
check("verify: scope reported AS OBSERVED (trade)",
      verify.observe_scope(good_account(permissionScope="SCOPE_TRADE"))["granted_scope_observed"] == "SCOPE_TRADE")
check("verify: scope classified is_trading",
      verify.observe_scope(good_account(permissionScope="SCOPE_TRADE"))["is_trading"] is True)

# require_view_only raises loudly on a trading grant, and on any field failure
try:
    verify.require_view_only(good_account(permissionScope="SCOPE_TRADE"))
    check("verify: require_view_only refuses SCOPE_TRADE", False)
except verify.PreflightRefusal as e:
    check("verify: require_view_only refuses SCOPE_TRADE", "SCOPE_TRADE" in str(e))
try:
    verify.require_view_only(good_account(isLive=True))
    check("verify: require_view_only refuses isLive True", False)
except verify.PreflightRefusal:
    check("verify: require_view_only refuses isLive True", True)
check("verify: require_view_only passes good account",
      verify.require_view_only(good_account())["ok"] is True)


# ---------------- metadata ----------------
RAW = MockReadOnlyBroker().symbol
md = metadata.normalise(RAW)
check("metadata: symbolId/name carried", md["symbol"]["symbolId"] == 41 and md["symbol"]["name"] == "XAUUSD")
check("metadata: enabled + trading status", md["symbol"]["enabled"] is True and md["symbol"]["trading_status"] == "TRADING")
check("metadata: precision fields", md["precision"]["digits"] == 2 and md["precision"]["pip_position"] == 1)
check("metadata: volume fields", md["volume"]["lot_size"] == 100 and md["volume"]["step_volume"] == 1)
check("metadata: stop distance + unit", md["stop_distance"]["min_stop_distance"] == 1.0 and md["stop_distance"]["min_stop_distance_unit"] == "PRICE")
check("metadata: session normalised open", md["session"]["available"] and md["session"]["status"] == "OPEN")

# missing required field fails closed
try:
    metadata.normalise({k: v for k, v in RAW.items() if k != "lotSize"})
    check("metadata: missing lotSize halts", False)
except metadata.MetadataIncomplete:
    check("metadata: missing lotSize halts", True)

# stop-distance with no unit is flagged, not guessed
md2 = metadata.normalise({**RAW, "minStopDistanceUnit": None})
check("metadata: missing stop-unit flagged UNSPECIFIED",
      md2["stop_distance"]["min_stop_distance_unit"] == "UNSPECIFIED_CONFIRM_BEFORE_USE")
check("metadata: absent session reported UNAVAILABLE",
      metadata.normalise({**RAW, "session": None})["session"]["status"] == "UNAVAILABLE")


# ---------------- conversions (candidates only, no rounding/selection) ----------------
meta = {"lotSize": 100, "minVolume": 1, "maxVolume": 10000, "stepVolume": 1}
tbl = conversions.candidate_table([0.01, 0.10, 1.00], meta)
rows = {r["nominal_lots"]: r for r in tbl["rows"]}
check("conversions: 0.01 -> exact 1", rows[0.01]["status"] == "EXACT" and rows[0.01]["protocol_volume"] == 1)
check("conversions: 0.10 -> exact 10", rows[0.10]["protocol_volume"] == 10)
check("conversions: 1.00 -> exact 100", rows[1.00]["protocol_volume"] == 100)
check("conversions: nothing selected", all(not r["selected"] and not r["recommended"] for r in tbl["rows"]))
# a sub-unit nominal that cannot land exactly HALTS (no rounding either way)
meta_coarse = {"lotSize": 100, "minVolume": 1, "maxVolume": 10000, "stepVolume": 10}
tbl2 = conversions.candidate_table([0.155], meta_coarse)   # 0.155*100=15.5 -> not integer
check("conversions: non-exact nominal HALTs (no rounding)", tbl2["rows"][0]["status"] == "HALT")
tbl3 = conversions.candidate_table([0.15], meta_coarse)    # 15 not a multiple of step 10
check("conversions: off-step nominal HALTs", tbl3["rows"][0]["status"] == "HALT")


# ---------------- credentials (DPAPI + redaction, no secrets in repo) ----------------
blob = credentials.dpapi_protect(b"not-a-real-secret-test-value")
check("credentials: DPAPI blob != plaintext", b"not-a-real-secret-test-value" not in blob)
check("credentials: DPAPI round-trips",
      credentials.dpapi_unprotect(blob) == b"not-a-real-secret-test-value")
red = credentials.redact_account("1234567890")
check("credentials: redaction is hash + last4", red["last4"] == "7890" and len(red["sha256"]) == 64 and "1234567890" != red["sha256"])
check("credentials: blob store is OUTSIDE the repo", credentials.store_is_outside_repo(_REPO_ROOT))
# store/load round-trip (test values only, written outside the repo)
credentials.store_credentials("client_test", "secret_test")
cid, secret = credentials.load_credentials()
check("credentials: store/load round-trip", cid == "client_test" and secret == "secret_test")


# ---------------- ACL provisioning + verifier ----------------
cmds = acl.provisioning_commands("A", "R", "O")
check("acl: executor DENY on approvals emitted", any("/deny" in c and "ORANGE_EXECUTOR" in c and '"A"' in c for c in cmds))
check("acl: approver DENY on outbox emitted", any("/deny" in c and "ORANGE_APPROVER" in c and '"O"' in c for c in cmds))

GOOD_APPROVALS = (
    r'C:\store\approvals ORANGE_APPROVER:(OI)(CI)(F)' "\n"
    r'                    ORANGE_EXECUTOR:(DENY)(OI)(CI)(WD,AD,DC,DE,WA)' "\n"
    r'                    ORANGE_EXECUTOR:(OI)(CI)(RX)' "\n")
va = acl.verify_approvals_acl(GOOD_APPROVALS, "ORANGE_EXECUTOR", "ORANGE_APPROVER")
check("acl: approvals verifier PASS (executor denied, approver writes)", va["ok"] is True)

BAD_APPROVALS = (
    r'C:\store\approvals ORANGE_APPROVER:(OI)(CI)(F)' "\n"
    r'                    ORANGE_EXECUTOR:(OI)(CI)(M)' "\n")   # executor CAN write -> must fail
check("acl: approvals verifier FAILS when executor can write",
      acl.verify_approvals_acl(BAD_APPROVALS, "ORANGE_EXECUTOR", "ORANGE_APPROVER")["ok"] is False)

GOOD_OUTBOX = (
    r'C:\store\outbox ORANGE_EXECUTOR:(OI)(CI)(M)' "\n"
    r'                 ORANGE_APPROVER:(DENY)(OI)(CI)(WD,AD,DC,DE,WA)' "\n")
vo = acl.verify_executor_store_acl(GOOD_OUTBOX, "ORANGE_EXECUTOR", "ORANGE_APPROVER")
check("acl: outbox verifier PASS (executor writes, approver denied)", vo["ok"] is True)
BAD_OUTBOX = (
    r'C:\store\outbox ORANGE_EXECUTOR:(OI)(CI)(M)' "\n"
    r'                 ORANGE_APPROVER:(OI)(CI)(M)' "\n")       # approver CAN write -> place orders
check("acl: outbox verifier FAILS when approver can write",
      acl.verify_executor_store_acl(BAD_OUTBOX, "ORANGE_EXECUTOR", "ORANGE_APPROVER")["ok"] is False)

# verifier parses REAL icacls output (proves the parser before it meets real principals)
with tempfile.TemporaryDirectory() as td:
    real = acl.read_icacls(td)
    parsed = acl.parse_icacls(real)
    check("acl: parses real icacls output (non-empty)", len(parsed) >= 1)


# ---------------- full report (dry-run) ----------------
rep = preflight.build_report(MockReadOnlyBroker())
check("report: view-only verification ok", rep["connection"]["view_only_verification_ok"] is True)
check("report: granted scope observed = SCOPE_VIEW", rep["connection"]["granted_scope_observed"] == "SCOPE_VIEW")
check("report: account redacted (hash+last4, no raw id)",
      rep["connection"]["account_redacted"]["redacted"] and "sha256" in rep["connection"]["account_redacted"])
check("report: not refused", rep["refused"] is None)
check("report: has XAUUSD metadata", rep["xauusd_metadata"]["symbol"]["name"] == "XAUUSD")
check("report: has candidate conversions, none selected",
      all(not r["selected"] for r in rep["candidate_conversions"]["rows"]))
check("report: mode is DRY_RUN_MOCK", rep["mode"] == "DRY_RUN_MOCK")

# a trading-scope grant REFUSES and stops before metadata/candidates
rep_trade = preflight.build_report(MockReadOnlyBroker(account=good_account(permissionScope="SCOPE_TRADE")))
check("report: SCOPE_TRADE refuses", rep_trade["refused"] is not None and "SCOPE_TRADE" in rep_trade["refused"])
check("report: refused report has no candidates", "candidate_conversions" not in rep_trade)
# wrong account refuses
rep_wrong = preflight.build_report(MockReadOnlyBroker(account=good_account(ctidTraderAccountId=42)))
check("report: wrong account refuses", rep_wrong["refused"] is not None)


# ---------------- PROHIBITED-BY-ABSENCE scan across the package source ----------------
PKG_DIR = os.path.dirname(__file__)
FORBIDDEN = [
    "ProtoOANewOrderReq", "ProtoOAClosePositionReq", "ProtoOACancelOrderReq",
    "ProtoOAAmendOrderReq", "place_limit", "place_order", "close_position",
    "cancel_order", "modify_position", "DEMO_EXECUTION_ENABLED = True",
    "EXECUTION_ENABLED = True",
]
src_all = ""
for fn in os.listdir(PKG_DIR):
    if fn.endswith(".py") and fn != "tests_preflight.py":
        src_all += open(os.path.join(PKG_DIR, fn), encoding="utf-8").read() + "\n"
for tok in FORBIDDEN:
    check(f"absence: no '{tok}' in package", tok not in src_all)
# never emits a trading OAuth scope
check("absence: OAuth emit scope is 'accounts' only",
      cfg.OAUTH_EMIT_SCOPE == "accounts" and "trading" not in src_all.lower().split("refuse")[0][:0] + cfg.OAUTH_EMIT_SCOPE)
# the tool imports NONE of the order-capable execution-lane modules
for banned_mod in ("executor", "mock_broker", "approval_tool", "reconcile"):
    check(f"absence: does not import demo_lane.{banned_mod}",
          not re.search(rf"import[^\n]*\b{banned_mod}\b", src_all))


print(f"\n{_passed} passed, {_failed} failed")
sys.exit(1 if _failed else 0)
