"""READ_ONLY_DEMO_PREFLIGHT_v0_1 configuration. NO credentials here.

Distinct from demo_lane/config.py in ONE safety-critical way: that config's REQUIRED_SCOPE
is SCOPE_TRADE (the ratified demo-execution lane would place demo orders). THIS preflight
tool is view-only, so the granted permission it REQUIRES is SCOPE_VIEW, and it REFUSES
SCOPE_TRADE. Emitting OAuth 'trading' is impossible here — only 'accounts' is emitted.
"""
import os

# --- endpoint: demo only (no live path exists in this tool) ---
DEMO_ENDPOINT = "demo.ctraderapi.com"

# --- OAuth scope emitted to the broker (view-only). 'trading' is NEVER emitted. ---
OAUTH_EMIT_SCOPE = "accounts"                 # cTrader view-only scope

# --- the GRANTED permission this tool requires (view-only) and the one it refuses ---
REQUIRED_GRANTED_SCOPE = "SCOPE_VIEW"         # accounts / view-only
REFUSED_GRANTED_SCOPE = "SCOPE_TRADE"         # trading — out of scope; refuse and report

# --- account allowlist (Pepperstone demo). The real ctidTraderAccountId is provided by
#     Martyn via env; the default is the demo_lane placeholder. It is REDACTED in output. ---
ALLOWED_CTID_TRADER_ACCOUNT_ID = int(
    os.environ.get("ORANGE_PREFLIGHT_ALLOWED_CTID", "1000001"))
EXPECTED_BROKER_ENVIRONMENT = "PEPPERSTONE_DEMO"

# --- the symbol we read (resolved to a numeric symbolId on the live read) ---
GOLD_SYMBOL = os.environ.get("CTRADER_GOLD_SYMBOL", "XAUUSD")

# --- CANDIDATE nominal quantities to CONVERT AND REPORT ONLY. This is NOT a ratified
#     ladder and NOTHING here selects one. Bidirectional per OQ-13; Martyn ratifies a
#     specific figure knowingly after seeing the exact conversions. Overridable via env. ---
def candidate_nominal_lots():
    raw = os.environ.get("ORANGE_PREFLIGHT_CANDIDATE_LOTS")
    if raw:
        return [float(x) for x in raw.split(",") if x.strip()]
    return [0.01, 0.02, 0.05, 0.10, 0.20, 0.50, 1.00]

# --- where the token cache lives (view-only). Reused from the existing view-only auth. ---
TOKEN_FILE = os.path.join("data", "ctrader_token.json")

# --- a live read is DISABLED unless Martyn has performed the accounts-scope OAuth grant
#     AND explicitly opts in. Absent that, the tool runs in dry-run (mock) proof mode. ---
LIVE_READ_OPT_IN = os.environ.get("ORANGE_PREFLIGHT_LIVE_READ", "0") == "1"

TOOL_VERSION = "READ_ONLY_DEMO_PREFLIGHT_v0_1"
