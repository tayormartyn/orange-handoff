"""Read-only cTrader preflight configuration. NO credentials here, ever."""
import os

# --- network authority: DEMO only, single host:port ---
DEMO_HOST = "demo.ctraderapi.com"
DEMO_PORT = 5035
# live is intentionally NOT configurable in this tool — there is no live path.

# --- OAuth scope emitted to the broker (view-only). 'trading' is NEVER emitted. This is a
#     module CONSTANT, never a function parameter: there is no code path that emits any other
#     scope. oauth.build_authorize_url takes NO scope argument (a test asserts this). ---
OAUTH_EMIT_SCOPE = "accounts"          # cTrader view-only scope (HARDCODED, not overridable)

# --- OAuth endpoints (Spotware Connect). The token exchange is Phase-2 gated + lazy. ---
OAUTH_AUTH_URL = "https://connect.spotware.com/apps/auth"
OAUTH_TOKEN_URL = "https://connect.spotware.com/apps/token"
OAUTH_REDIRECT_URI = os.environ.get("ORANGE_PREFLIGHT_REDIRECT_URI", "http://localhost/")

# --- the GRANTED permission this tool requires, and the one it refuses ---
REQUIRED_GRANTED_SCOPE = "SCOPE_VIEW"  # accounts / view-only
REFUSED_GRANTED_SCOPE = "SCOPE_TRADE"  # trading — REFUSE and stop

# --- account allowlist (Pepperstone demo): the real ctidTraderAccountId is NEVER hardcoded or
#     guessed here. It starts UNPINNED and is pinned (allowlist.pin_ctid) only after the first
#     account-list read in Phase 2. While unpinned, the fail-closed guard REFUSES (empty
#     allowlist = no match = stop). The pinned value lives OUTSIDE the repo (see allowlist.py). ---
EXPECTED_ENVIRONMENT = "PEPPERSTONE_DEMO"

# --- the symbol we resolve (must resolve to exactly one id) ---
GOLD_SYMBOL = os.environ.get("CTRADER_GOLD_SYMBOL", "XAUUSD")

# --- Phase 2 gate: a live connection requires the operator's accounts-scope OAuth grant AND
#     an explicit opt-in. Absent that, the tool runs Phase-1 static proof only (no connect). ---
PHASE2_CONNECT_OPT_IN = os.environ.get("ORANGE_PREFLIGHT_CONNECT", "0") == "1"

TOOL_VERSION = "READ_ONLY_CTRADER_PREFLIGHT_v0_1"
