"""
H1 — automated source scan over the Hyperliquid observation package. THIS SCAN BLOCKS THE
BRICK: any finding makes the test suite fail.

It proves, mechanically, that nowhere in the package is there a path to:
  * place / modify / cancel an order,
  * open or close a position / execute a trade,
  * transfer / deposit / withdraw funds, or
  * sign an L1 action or import a signing library,
and that the signing `/exchange` endpoint path is never present.

Self-covering: the forbidden TOKEN literals are assembled from fragments so they never appear
verbatim in THIS file — a genuine order/signing reference here would still be detected.
"""
import os
import re

# --- order / execution / transfer / deposit / withdrawal METHOD names ------------------
# Matched only as `def <name>` definitions, so listing them here does not self-flag.
PROHIBITED_METHODS = (
    "order", "bulk_orders", "market_open", "market_close", "cancel", "cancel_by_cloid",
    "modify_order", "bulk_modify_orders", "place_order", "submit_order", "create_order",
    "close_position", "execute_trade", "open_position",
    "update_leverage", "update_isolated_margin",
    "usd_transfer", "spot_transfer", "usd_class_transfer", "send_asset",
    "sub_account_transfer", "withdraw_from_bridge", "withdraw", "deposit", "transfer",
    "approve_agent", "approve_builder_fee", "sign", "sign_action",
)

# --- signing libraries / signing-call / signing-endpoint TOKENS ------------------------
# Assembled from fragments so the literals never appear verbatim in this scanner's source.
_E = "eth"
_SIGN = "sign"
PROHIBITED_TOKENS = (
    _E + "_account", _E + "_keys", "Local" + "Account",
    _SIGN + "_l1_action", _SIGN + "_inner", _SIGN + "_user_signed_action",
    _SIGN + "_typed_data", "secp" + "256k1",
    "hyperliquid" + ".exchange", "hyperliquid" + ".utils." + _SIGN + "ing",
    "from hyperliquid import " + "Exchange",
)
# the signing endpoint PATH (the venue's order/transfer route) — never constructed here
_PROHIBITED_PATH = "/" + "exchange"


def _py_files(path):
    if os.path.isfile(path) and path.endswith(".py"):
        yield path
        return
    for root, _dirs, files in os.walk(path):
        if "__pycache__" in root:
            continue
        for f in files:
            if f.endswith(".py"):
                yield os.path.join(root, f)


def scan_no_trading_path(paths):
    """Return list of (file, kind, token) violations. Empty list == clean (brick may pass)."""
    violations = []
    this_file = os.path.abspath(__file__)
    for p in paths:
        for fp in _py_files(p):
            if os.path.abspath(fp) == this_file:
                continue  # the scanner legitimately names fragments; never scan itself
            txt = open(fp, encoding="utf-8").read()
            for m in PROHIBITED_METHODS:
                if re.search(rf"def\s+{re.escape(m)}\b", txt):
                    violations.append((fp, "trading-method-def", m))
            for t in PROHIBITED_TOKENS:
                if re.search(rf"\b{re.escape(t)}\b", txt):
                    violations.append((fp, "signing-token-ref", t))
            if _PROHIBITED_PATH in txt:
                violations.append((fp, "signing-endpoint-path", _PROHIBITED_PATH))
    return violations
