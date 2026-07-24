"""
Signal Terminal — configuration.

PAPER MODE ONLY.
This terminal logs what a trade WOULD have been. It does NOT connect to any
exchange, it does NOT place orders, and it does NOT move money.

If you ever feel tempted to switch MODE to "LIVE", stop and read the README first.
"""

# ----------------------------------------------------------------------------
# Trading mode
# ----------------------------------------------------------------------------
# DO NOT change to LIVE until paper data has been reviewed.
MODE = "PAPER"          # "PAPER" or "LIVE"  — LIVE execution is intentionally disabled.

# ----------------------------------------------------------------------------
# The pot and the risk rule
# ----------------------------------------------------------------------------
# Your total trading capital ("the pot"), in GBP.
# Kept as a plain string here and turned into exact Decimal money inside the
# risk calculator — so we never touch error-prone floating point.
POT_SIZE = "14000"

# Hard risk cap per trade, as a fraction of the pot.
#   "0.01" = 1%.  This is the most you are willing to lose if the stop is hit.
# The risk calculator enforces this as an absolute ceiling.
RISK_PCT = "0.01"

# Currency symbol — used only for pretty printing.
CURRENCY = "£"

# ----------------------------------------------------------------------------
# Slippage model (honest paper fills)
# ----------------------------------------------------------------------------
# Real fills are NOT at the exact signal price — you get in slightly worse than
# you'd like. We model that as a per-SIDE price penalty that worsens the entry
# used for sizing, so the reward:risk and expectancy reflect realistic fills
# rather than perfect ones. (Without this, paper results flatter your edge.)
#
# Slippage is now configured PER ASSET CLASS, alongside that class's sizing and
# contract specs, in ASSET_CLASSES further down (the single source of truth for
# the multi-asset engine). The legacy SLIPPAGE table that older display code
# reads (status.py / review.py) is DERIVED from ASSET_CLASSES at the bottom of
# this section, so the two can never drift apart.
SLIPPAGE_DEFAULT = "0"   # used for any instrument not listed above

# ----------------------------------------------------------------------------
# Parser (Module B)
# ----------------------------------------------------------------------------
# The Claude model used to read a pasted signal and pull out the numbers.
PARSER_MODEL = "claude-sonnet-4-6"

# ----------------------------------------------------------------------------
# Paper logger (Module D)
# ----------------------------------------------------------------------------
# The CSV file every confirmed paper trade is written to.
PAPER_LOG_FILE = "paper_log.csv"

# ----------------------------------------------------------------------------
# Audit trail (audit.py) — the machine's black box
# ----------------------------------------------------------------------------
# Append-only, permanent record of every decision the pipeline makes (one JSON
# line per signal run). It is NEVER edited or deleted by hand — it's there so you
# can always ask "why did the machine do that?" months later. Read-only to your
# paper log; it only ever ADDS to its own file.
AUDIT_LOG_FILE = "audit_log.jsonl"

# ============================================================================
# RULE PROFILE — "CPS" (Columbus Closing Price System) or "DEFAULT"
# ============================================================================
# An OPTIONAL, selectable profile that makes the engine speak the CPS framework:
# phase-based risk, a fixed reward:risk exit ladder, real metal contract specs,
# and daily/weekly loss limits. It is ADDITIVE — every existing safety rail
# (1%-style hard cap mechanism, round-down sizing, zone validation, loud
# rejections, the amber human-confirm) still applies underneath it.
#
#   "CPS"     -> phase risk, 1:2/1:3/1:5 ladder scaled out in thirds, loss limits
#   "DEFAULT" -> the original behaviour: flat RISK_PCT, the signal's own targets
RULE_PROFILE = "DEFAULT"      # "CPS" or "DEFAULT"  (set to "CPS" to opt in)

# --- Phase-based risk (CPS) -------------------------------------------------
# Phase 1 = 1%, Phase 2 = 2%, Phase 3 = up to 3%. HARD CAP 3%, FLOOR 0.5%.
# Default to Phase 1 / 1%.
TRADING_PHASE = 1             # 1, 2, or 3
PHASE_RISK = {1: "0.01", 2: "0.02", 3: "0.03"}
RISK_PCT_MIN = "0.005"        # 0.5% floor
RISK_PCT_MAX = "0.03"         # 3% hard cap — risk % is clamped and never exceeds this

# --- Daily / weekly loss limits (CPS) ---------------------------------------
# The engine TRACKS cumulative realised P&L from the log and prints a clear STOP
# warning when a limit is hit. In PAPER mode it warns loudly; it does not block.
DAILY_LOSS_LIMIT = "0.02"     # 2% of balance lost in a day  -> stop for the day
WEEKLY_LOSS_LIMIT = "0.10"    # 10% of balance lost in a week -> stop for the week

# --- Stops ------------------------------------------------------------------
# "SIGNAL" -> use the stop-loss the signal gave (default, safest with our zone check).
# "FIXED"  -> place the stop a fixed dollar distance from entry (METALS only):
#             Gold $10-$20, Silver $1-$2.
# CPS RULE: the stop is set at entry and NEVER widened. It may only move toward
# profit (to breakeven after TP2). The engine enforces "never wider than set" and
# prints the management rule on the ticket; live trailing is a later, manual step.
STOP_MODE = "SIGNAL"          # "SIGNAL" or "FIXED"
FIXED_STOP = {                # dollars from entry; used only when STOP_MODE = "FIXED"
    "XAU": "15",              # allowed band 10-20
    "XAG": "1.5",             # allowed band 1-2
}
FIXED_STOP_RANGE = {          # allowed bands, validated on use
    "XAU": ("10", "20"),
    "XAG": ("1", "2"),
}

# --- Exit ladder (CPS) ------------------------------------------------------
# Fixed reward:risk targets, position scaled out in thirds.
CPS_LADDER_RR = ["2", "3", "5"]                       # TP1 = 1:2, TP2 = 1:3, TP3 = 1:5
CPS_SCALE_OUT = [
    "take 1/3 off",
    "take 1/3 off, then move stop to breakeven on the runner",
    "1/3 runner",
]

# --- Minimum tradable lot (CPS / metals) ------------------------------------
# If sizing rounds below this, SKIP the trade (the existing "protection" message).
MIN_LOT = "0.01"

# --- Contract specs reminder (printed on every metal ticket) ----------------
BROKER_SPEC_NOTE = (
    "Confirm these specs with YOUR broker before live — Columbus uses VT Markets; "
    "your broker (Bitget/other) may differ."
)

# ============================================================================
# PER-ASSET-CLASS CONFIGURATION — the multi-asset engine
# ============================================================================
# This is the ONE place that says, for each asset class, how a trade is sized,
# what its contract/pip specs are, and how much slippage to model. The core
# code (module_router for classification, module_c_risk for sizing) is GENERIC:
# it reads this registry and dispatches. Asset logic is NOT hardcoded to gold.
#
# HOW TO ADD A NEW ASSET CLASS LATER (see the README for the full walkthrough):
#   1. Add an entry to ASSET_CLASSES below with its recognition rules + specs.
#   2. If it can reuse an existing sizing strategy ("dollar_per_point",
#      "pip_value", "percent_risk"), set "sizing" to that name and you are DONE
#      — no core code changes. If it needs brand-new sizing maths, add one
#      function to SIZING_STRATEGIES in module_c_risk.py and name it here.
#   3. Until you are confident in its sizing, leave "calibrated": False — the
#      router will RECOGNISE the class but send it to human REVIEW instead of
#      sizing it with guessed maths.
#
# Each entry's fields:
#   ledger_class   the value written to the log's `asset_class` column. Kept in
#                  the existing METAL/CRYPTO/FOREX vocabulary for back-compat.
#   calibrated     True  -> sizing logic exists and is trusted enough for PAPER.
#                  False -> recognised only; routed to REVIEW, never auto-sized.
#   sizing         name of the sizing strategy (key in module_c_risk.SIZING_STRATEGIES).
#   params         strategy-specific spec (contract multiplier, pip/contract size, lots).
#   slippage       per-SIDE price penalty modelled into the entry (price units).
#   verified       False -> contract spec is a PLACEHOLDER; CONFIRM with your broker.
#   broker_note    spec-confirmation reminder printed on the ticket (metals/forex).
#   flags          extra honesty flags printed on the ticket (e.g. crypto fees).
#   match          how the router RECOGNISES this class (see notes per entry).
#   display_name   friendly name for summaries.
#
# Account currency the pot (POT_SIZE) is denominated in. NOTE: like the original
# gold maths, the engine treats USD≈account 1:1 (a deliberate simplification).
# Non-USD FX quote currencies are flagged CONFIRM-WITH-BROKER where that bites.
ACCOUNT_CURRENCY = "GBP"

# --- Recognition tables (shared by the router's structural detectors) --------
# ISO fiat currency codes used to recognise a FOREX pair (e.g. USDCAD, GBPJPY).
# XAU/XAG are handled as metals BEFORE this check, so they never count here.
FX_CODES = {
    "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD",
    "CNH", "SEK", "NOK", "DKK", "SGD", "HKD", "MXN", "ZAR", "TRY", "PLN",
}

# Stablecoin QUOTE tokens that mark a CRYPTO pair. Matched as the pair's quote
# token (the part after "/", or the trailing token) — NOT as a loose substring.
# (Matching "USDC" as a substring is exactly the bug that tagged USDCAD CRYPTO.)
CRYPTO_QUOTE_CODES = {"USDT", "USDC", "BUSD", "FDUSD", "TUSD", "DAI", "USDP"}

# Known crypto bases, for signals that omit the quote (e.g. a bare "BTC" / "BTCUSD").
CRYPTO_BASES = {
    "BTC", "ETH", "SOL", "FET", "PEPE", "BNB", "XRP", "ADA", "DOGE", "AVAX",
    "LINK", "MATIC", "DOT", "ARB", "OP", "SUI", "TIA", "SEI", "INJ", "NEAR",
    "LTC", "RNDR", "WIF", "BONK", "SHIB", "TON", "APT", "ATOM",
}

# --- FOREX pip value: quote-currency -> account-currency conversion ----------
# A FOREX pip's cash value depends on the pair's QUOTE currency. For USD-quoted
# pairs (EURUSD, GBPUSD…) the engine's USD≈account 1:1 proxy makes pip value
# directly usable. For NON-USD quotes (USDCAD->CAD, GBPJPY->JPY, EURGBP->GBP…)
# the true pip value depends on a live FX rate the terminal does NOT know — so
# we size with the rate below (default 1.0) and LOUDLY flag CONFIRM-WITH-BROKER.
# These are ROUGH and go stale: refresh/confirm before trusting non-USD sizes.
FX_QUOTE_TO_ACCOUNT = {
    "USD": "1.0",   # engine proxy: pot/gold already treated as USD≈account 1:1
}
FX_QUOTE_TO_ACCOUNT_DEFAULT = "1.0"   # unknown quote ccy -> 1.0, flagged CONFIRM

# --- Honesty notes printed on tickets ---------------------------------------
FX_SPEC_NOTE = (
    "FOREX pip value & contract size vary by broker (standard lot assumed = "
    "100,000 units). For non-USD-quote pairs the pip value also depends on the "
    "live quote->account FX rate — CONFIRM WITH BROKER before trusting the size."
)
CRYPTO_FEE_NOTE = (
    "CRYPTO sizing models NO fees/spread yet (slippage = 0). Taker fees and "
    "spread are real costs — add fee/spread modelling before trusting the edge."
)
OIL_SPEC_NOTE = "Oil contract/tick specs vary widely (CFD vs futures) — needs calibration."
COMMODITY_SPEC_NOTE = "Commodity contract/tick specs vary by instrument — needs calibration."
STOCK_SPEC_NOTE = "Equity sizing (shares, lot, margin) differs from FX/metals — needs calibration."

ASSET_CLASSES = {
    # ---- Calibrated: the engine sizes these in PAPER --------------------------
    "GOLD": {
        "ledger_class": "METAL",
        "calibrated": True,
        "sizing": "dollar_per_point",
        # CPS / VT Markets gold spec: 100 oz per 1.0 lot => $100 per $1 move per lot.
        "params": {
            "contract_multiplier": "100",   # $ per 1.0 price move per 1.0 lot
            "lot_size": "0.01",             # minimum size increment (round DOWN to it)
            "min_lot": "0.01",              # below this -> SKIP (protection)
        },
        "slippage": "0.30",                 # $/side (estimate; TUNE to your broker)
        "verified": False,                  # CONFIRM contract spec with YOUR broker
        "broker_note": BROKER_SPEC_NOTE,
        "flags": [],
        "match": {"prefixes": ["XAU"]},     # XAUUSD, XAUEUR…
        "display_name": "gold",
    },
    "SILVER": {
        "ledger_class": "METAL",
        "calibrated": True,
        "sizing": "dollar_per_point",
        # CPS / VT Markets silver spec: 5,000 oz per 1.0 lot => $5,000 per $1 move per lot.
        "params": {
            "contract_multiplier": "5000",
            "lot_size": "0.01",
            "min_lot": "0.01",
        },
        "slippage": "0.03",                 # smaller price -> smaller $/side estimate
        "verified": False,
        "broker_note": BROKER_SPEC_NOTE,
        "flags": [],
        "match": {"prefixes": ["XAG"]},
        "display_name": "silver",
    },
    "FOREX": {
        "ledger_class": "FOREX",
        "calibrated": True,
        "sizing": "pip_value",
        "params": {
            "contract_units": "100000",     # 1.0 standard lot = 100,000 units of base ccy
            "pip_size": "0.0001",           # standard pip (display only; JPY uses jpy_pip_size)
            "jpy_pip_size": "0.01",         # JPY-quote pairs quote to 2 dp
            "lot_size": "0.01",             # size in lots, round DOWN to 0.01
            "min_lot": "0.01",
        },
        "slippage": "0",                    # price units; 0 until tuned per pair
        "verified": False,                  # pip value/contract size vary by broker
        "broker_note": FX_SPEC_NOTE,
        "flags": [],
        "match": {"forex_codes": True},     # structural: two ISO fiat codes back-to-back
        "display_name": "forex",
    },
    "CRYPTO": {
        "ledger_class": "CRYPTO",
        "calibrated": True,
        "sizing": "percent_risk",
        "params": {
            "lot_size": "0.000001",         # fractional units allowed
            "min_lot": "0.000001",
        },
        "slippage": "0",                    # fees/spread NOT modelled yet (see flags)
        "verified": True,                   # size maths sound; fee/spread modelling pending
        "broker_note": "",
        "flags": [CRYPTO_FEE_NOTE],
        # quote stablecoin token, an explicit PERP, the parser's CRYPTO hint, or a known base
        "match": {"quote_codes": True, "perp": True, "parser_hint": "CRYPTO", "bases": True},
        "display_name": "crypto",
    },

    # ---- Recognised but NOT YET calibrated: router -> REVIEW, never sized -----
    # Adding proper sizing later = flip "calibrated" to True and fill in "sizing"
    # + "params" (and a SIZING_STRATEGIES function if the maths is new).
    "OIL": {
        "ledger_class": "OIL",
        "calibrated": False,
        "sizing": None,
        "params": {},
        "slippage": "0",
        "verified": False,
        "broker_note": OIL_SPEC_NOTE,
        "flags": [],
        "match": {"tickers": [
            "WTI", "USOIL", "UKOIL", "BRENT", "WTIUSD", "BRENTUSD",
            "XTIUSD", "XBRUSD", "CL", "BCO", "BCOUSD", "OIL",
        ]},
        "display_name": "oil",
    },
    "COMMODITIES": {
        "ledger_class": "COMMODITIES",
        "calibrated": False,
        "sizing": None,
        "params": {},
        "slippage": "0",
        "verified": False,
        "broker_note": COMMODITY_SPEC_NOTE,
        "flags": [],
        "match": {"tickers": [
            "NATGAS", "NGAS", "XNGUSD", "COPPER", "XCUUSD", "WHEAT", "CORN",
            "SOYBEAN", "COCOA", "COFFEE", "SUGAR", "PLATINUM", "XPTUSD",
            "PALLADIUM", "XPDUSD",
        ]},
        "display_name": "commodities",
    },
    "STOCKS": {
        "ledger_class": "STOCKS",
        "calibrated": False,
        "sizing": None,
        "params": {},
        "slippage": "0",
        "verified": False,
        "broker_note": STOCK_SPEC_NOTE,
        "flags": [],
        # Equities have no structural tell, so they are an explicit ticker list.
        "match": {"tickers": [
            "AAPL", "TSLA", "MSFT", "NVDA", "AMZN", "GOOGL", "GOOG", "META",
            "NFLX", "AMD", "INTC", "BABA", "DIS", "BA", "JPM", "V", "KO",
            "PYPL", "UBER", "COIN", "SPY", "QQQ",
        ]},
        "display_name": "stocks",
    },
}

# Order the router tries classes in. List-based exact matches and metal prefixes
# go first (most specific); the structural FOREX check runs BEFORE CRYPTO so a
# fiat pair like USDCAD can never be mistaken for crypto.
ASSET_CLASS_ORDER = ["GOLD", "SILVER", "OIL", "COMMODITIES", "STOCKS", "FOREX", "CRYPTO"]

# --- Legacy slippage table (DERIVED — do not edit; edit ASSET_CLASSES above) -
# status.py / review.py read this for their slippage summaries. Deriving it here
# keeps a single source of truth so the display can never drift from sizing.
SLIPPAGE = {
    "XAU": ASSET_CLASSES["GOLD"]["slippage"],
    "XAG": ASSET_CLASSES["SILVER"]["slippage"],
    "CRYPTO": ASSET_CLASSES["CRYPTO"]["slippage"],
}

# ----------------------------------------------------------------------------
# Signal Listener (Module A)  —  PREVIEW ONLY, NOT CONNECTED
# ----------------------------------------------------------------------------
# The listener can watch a chat channel and catch messages. Right now it only
# ever PRINTS what it caught — it is NOT wired into the run.py pipeline, places
# no trades, and touches no money.
#
# DO NOT set to LIVE until a real signal has been run manually through run.py
# and the source platform is confirmed. Going live is a separate, deliberate
# step done with guidance — never just by flipping this flag.
LISTENER_MODE = "PREVIEW"      # "PREVIEW" or "LIVE"
# ^ LEAVE THIS ON "PREVIEW". Do NOT change it until you have watched the listener
#   catch real signals cleanly for a while, and only then turn the parser handoff
#   on deliberately, together with your guide. (Changing this flag on its own does
#   nothing — the handoff line in module_a_telegram.py stays disabled regardless —
#   but keep it on PREVIEW so the intent is unmistakable.)

# Which Telegram channel(s) to watch. Use a channel's @username (e.g.
# "@thewhaleroom") OR its numeric ID (e.g. "-1001234567890").
#   * One channel:   TELEGRAM_CHANNEL = "@thewhaleroom"
#   * Several:       TELEGRAM_CHANNEL = ["@thewhaleroom", "-1001234567890"]
# Left blank on purpose — the listener refuses to start until you set this.
# (How to find a channel's @username or numeric ID is explained in the README.)
TELEGRAM_CHANNEL = "-1001902136163"

# Telethon stores your logged-in session in a file with this name (creates
# "<name>.session"). It is private — it is git-ignored and must never be shared.
TELEGRAM_SESSION_NAME = "whale_room"

# ============================================================================
# SIGNAL ROUTER (module_router.py) — classification & routing METADATA only
# ============================================================================
# The router reads a parsed signal and TAGS it: which asset class it is, which
# trader called it, and which venue it WOULD one day be sent to. It then decides
# whether the signal is clean enough to route, or whether it needs human eyes
# (the REVIEW bucket).
#
# It NEVER connects to a venue, places an order, or moves money. Everything below
# is just labels — routing metadata. (PAPER mode; no execution anywhere.)

# Traders/analysts you recognise. A signal's `source` is matched against this
# list (case-insensitive, substring — so "FAROUK-GOLD" still tags as FAROUK).
# Anything that matches nothing here is tagged UNKNOWN. Add names as you like.
KNOWN_TRADERS = ["FAROUK", "COLUMBUS", "CHRIS"]

# Where each asset class WOULD be routed later. These are PLACEHOLDER names on
# purpose — fill in the real venue/account labels when (and ONLY when) live
# execution is actually built. Nothing here connects to anything.
VENUE_MAP = {
    "GOLD":   "venue_A",   # <-- PLACEHOLDER: your metals venue (e.g. VT Markets / Bitget — confirm)
    "SILVER": "venue_A",   # <-- PLACEHOLDER: same metals venue
    "FOREX":  "venue_A",   # <-- PLACEHOLDER: your FX venue
    "CRYPTO": "venue_B",   # <-- PLACEHOLDER: your crypto exchange
}

# Label used for anything sent to the human-review bucket (UNKNOWN asset or a
# malformed signal). It is deliberately NOT a real venue.
VENUE_REVIEW = "REVIEW"

# ============================================================================
# SIGNAL-QUALITY FILTER (signal_quality.py) — confidence tagging METADATA only
# ============================================================================
# Traders often flag their OWN risk in the message: "high-risk", "low lot",
# "against the trend" (be cautious) vs "A+ setup", "100% confident" (lean in).
# This reads those cues from the raw signal text and tags each signal with a
# confidence level — HIGH / NORMAL / LOW — so review.py can later tell you whether
# the trader's HIGH-confidence calls actually outperform their LOW-confidence ones.
#
# By default this is INFORMATION ONLY: it tags, it does NOT block. The level is
# recorded on the logged trade; nothing is skipped or sized differently because
# of it. (PAPER mode; no execution anywhere.)
#
# Matching is case-insensitive and hyphen/space-insensitive, on whole words/
# phrases ("low lot" matches "low lot" and "low-lot", not "below lottery"). Tune
# both lists freely — add the exact phrases YOUR traders use.

# Cues that LOWER confidence (caution flags the trader posted about their call).
CONFIDENCE_LOW_CUES = [
    "high-risk", "high risk", "risky", "risk entry",
    "low lot", "small size", "small lot", "reduce size", "reduced size",
    "against the trend", "counter-trend", "counter trend",
    "be careful", "careful", "caution", "cautious",
    "news coming", "news event", "high impact", "volatile",
    "scalp only", "quick scalp", "not sure", "might", "maybe",
    "gamble", "lotto", "experimental",
]

# Cues that RAISE confidence (the trader signalling a strong, clean call).
CONFIDENCE_HIGH_CUES = [
    "high confidence", "high conviction", "100% confident", "100 percent",
    "very confident", "confident", "clean setup", "clean entry",
    "a+ setup", "a+ ", "textbook", "perfect setup",
    "strong", "strong setup", "high probability", "high prob",
    "best setup", "load up", "with the trend", "trend continuation",
    "easy", "sure thing", "banker",
]

# OPTIONAL — OFF BY DEFAULT. Leave this False to just TAG confidence and gather
# data. If you ever set it True, the pipeline will route LOW-confidence signals to
# the human REVIEW bucket instead of auto-processing them. Turn it on ONLY once
# review.py has actually shown that LOW-confidence trades underperform enough to
# be worth skipping — not before. (Even when True, nothing is executed; a routed
# trade is still only sized and logged on paper.)
SKIP_LOW_CONFIDENCE = False

# ============================================================================
# EXECUTION BRIDGE (module_execution.py) — SCAFFOLD, DELIBERATELY DISABLED
# ============================================================================
# This is the skeleton of the piece that would ONE DAY hand a fully sized,
# routed, safety-checked ticket to a broker. It is DELIBERATELY DISCONNECTED:
# there is no broker client anywhere, and three independent locks keep it from
# ever placing an order. Do NOT enable any of this until live trading is built
# on purpose, with guidance. (PAPER mode; nothing here moves money.)
#
#   Lock 1: this flag (EXECUTION_ENABLED).
#   Lock 2: MODE must be "LIVE" (it is "PAPER").
#   Lock 3: the submit function raises NotImplementedError where a broker call
#           would go — there is no order-placing code to run.
# Flipping any ONE of these still places nothing.
EXECUTION_ENABLED = False     # MUST stay False — on its own this changes nothing

# Placeholder broker handle per venue label (the labels come from VENUE_MAP).
# These are NOT credentials and connect to nothing — names to fill in much later.
EXECUTION_VENUES = {
    "venue_A": "PLACEHOLDER-metals-broker",    # e.g. your gold/silver/FX broker (confirm)
    "venue_B": "PLACEHOLDER-crypto-exchange",   # e.g. your crypto exchange
}
