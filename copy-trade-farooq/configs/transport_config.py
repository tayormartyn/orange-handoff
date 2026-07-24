"""Connected-transport configuration (OFFLINE build, Chuck-authorised TRANSPORT_BUILD_AUTHORISED).

FIXED destination: Pepperstone cTrader DEMO only. There is NO live path selectable here and NO
caller/CLI/env host+port override anywhere in this package. Gate AUTHORITY is NOT redefined here —
it is the single source in demo_lane.config / demo_lane.gate; this module only re-reads it.
Nothing in this package can flip a gate, request OAuth, or connect to place orders.
"""
from .. import config as demo_config          # SINGLE SOURCE of gate + account allowlist
from .. import gate as demo_gate              # SINGLE SOURCE of arming authority

# --- FIXED demo destination (immutable; no override path exists) ------------------------------
DEMO_HOST = "demo.ctraderapi.com"             # == demo_config.DEMO_ENDPOINT (asserted below)
DEMO_PORT = 5035                              # cTrader Open API TLS port (demo)
assert DEMO_HOST == demo_config.DEMO_ENDPOINT, "transport host must equal the single-source demo endpoint"

# There is deliberately NO LIVE_HOST constant and no selector. A live endpoint cannot be named.

# --- protocol / timing constants (transport mechanics only; NOT gates, NOT strategy) ----------
MAX_FRAME_BYTES = 1 << 20                     # 1 MiB hard cap; an oversized length prefix fails closed
HEARTBEAT_INTERVAL_S = 10                     # sender thread emits a heartbeat if idle this long
HEARTBEAT_TIMEOUT_S = 30                      # no inbound traffic for this long -> stale -> disconnect
RESPONSE_TIMEOUT_S = 15                       # per-request response wait; exceeding -> OUTCOME_UNKNOWN
RECONNECT_BACKOFF_S = (1, 2, 5, 15, 30)      # bounded backoff schedule; caps at the last value
RECONNECT_MAX_ATTEMPTS = len(RECONNECT_BACKOFF_S)
READER_POLL_S = 0.2                           # single reader thread's recv poll interval
SENDER_POLL_S = 0.05                          # sender thread's queue poll (drives auto-heartbeat)

TRANSPORT_VERSION = "connected_transport_v0_1"

# --- BROKER-IDENTITY CLAIM REGISTER (Chuck gap correction 3) ----------------------------------
# What the OFFLINE build actually proves vs what only the real read-only preflight can prove.
# broker_environment in the account guard is a LOCAL CONFIG EXPECTATION compared with itself —
# it is NOT broker attestation. Never upgrade PEPPERSTONE_ACCOUNT_BINDING here; only the preflight
# lane may produce the immutable binding, and the connected composition must validate it.
BROKER_IDENTITY_CLAIMS = {
    "DEMO_ENDPOINT": "OFFLINE_PROVEN",                       # fixed, no override, egress-guarded
    "ALLOWLISTED_ACCOUNT_ID": "OFFLINE_GUARD_PROVEN",        # exact-ID conjunction, offline
    "IS_LIVE_FALSE": "OFFLINE_GUARD_PROVEN",                 # isLive==False conjunction, offline
    "SCOPE_TRADE": "OFFLINE_GUARD_PROVEN",                   # scope conjunction, offline (fake creds)
    "PEPPERSTONE_ACCOUNT_BINDING": "PENDING_READ_ONLY_PREFLIGHT",
}

# the immutable sanitised binding the read-only preflight must create (and this transport's future
# connected composition must validate) before Pepperstone identity may be treated as proven:
PREFLIGHT_BINDING_REQUIRED_FIELDS = (
    "account_id_sha256",         # hash of the broker-reported ctidTraderAccountId
    "account_id_last4",          # last four digits only (sanitised)
    "is_live",                   # must be exactly False, broker-reported
    "broker_identity",           # confirmed Pepperstone demo identity, broker-reported
    "endpoint",                  # must equal the fixed demo endpoint
    "preflight_source",          # which preflight produced it
    "preflight_timestamp_utc",   # when
    "binding_sha256",            # hash sealing the record (immutability check)
)


def validate_preflight_binding(binding):
    """Fail-closed validator for the preflight identity binding. The future connected composition
    MUST pass a real, immutable, sanitised preflight record through this before treating
    PEPPERSTONE_ACCOUNT_BINDING as anything but PENDING. A missing/partial/self-referential
    binding -> ValueError (and the composition must remain NOT_ARMED)."""
    if not isinstance(binding, dict):
        raise ValueError("preflight binding absent — PEPPERSTONE_ACCOUNT_BINDING stays "
                         "PENDING_READ_ONLY_PREFLIGHT")
    missing = [f for f in PREFLIGHT_BINDING_REQUIRED_FIELDS
               if f not in binding or binding[f] in (None, "")]
    if missing:
        raise ValueError(f"preflight binding incomplete: missing {missing}")
    if binding["is_live"] is not False:
        raise ValueError("preflight binding must prove isLive == False")
    if binding["endpoint"] != DEMO_HOST:
        raise ValueError("preflight binding endpoint must be the fixed demo endpoint")
    ident = str(binding["broker_identity"]).upper()
    if "PEPPERSTONE" not in ident or "DEMO" not in ident:
        raise ValueError("preflight binding must carry a confirmed Pepperstone DEMO identity")
    if len(str(binding["account_id_last4"])) != 4:
        raise ValueError("preflight binding account_id_last4 must be exactly four characters")
    return True


def gates_all_false():
    """True iff all three authoritative execution gates are False (the normal, safe state)."""
    return (not demo_config.EXECUTION_ENABLED
            and not demo_config.CTRADER_EXECUTION_ENABLED
            and not demo_config.DEMO_EXECUTION_ENABLED)


def production_armed():
    """Authoritative arming for the PRODUCTION composition — a pure function of the single-source
    gates, exactly as demo_lane.order_adapter.production_policy derives dispatch. Enabled iff the
    demo gate is True AND both live gates are False. All three are hard False -> always False."""
    return (bool(demo_config.DEMO_EXECUTION_ENABLED)
            and not demo_config.EXECUTION_ENABLED
            and not demo_config.CTRADER_EXECUTION_ENABLED)


def backoff_for(attempt):
    """Bounded backoff seconds for a 0-indexed attempt; never unbounded (caps at the last step)."""
    if attempt < 0:
        attempt = 0
    return RECONNECT_BACKOFF_S[min(attempt, len(RECONNECT_BACKOFF_S) - 1)]
