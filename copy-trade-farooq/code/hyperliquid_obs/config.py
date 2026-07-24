"""
H1 — Hyperliquid TESTNET observation config (no secrets, ever).

Holds only non-secret flags + the TESTNET endpoint allowlist. No credential of any kind
is read or stored here. Every safety flag defaults to the SAFE value, and an out-of-policy
value is a hard-fail upstream (see safety.assert_testnet_safety), never a silent override.

Endpoint policy (primary source: docs.hyperliquid.xyz):
  * TESTNET REST `https://api.hyperliquid-testnet.xyz`  — POST /info only (public, no signing)
  * TESTNET WS   `wss://api.hyperliquid-testnet.xyz/ws` — public subscriptions only
  * MAINNET endpoints are FORBIDDEN in this build (HYPERLIQUID_MAINNET_ALLOWED=False).
  * The venue's signing/order route is NEVER constructed by this package.
"""
import os
from urllib.parse import urlparse

from . import OBSERVER_VERSION  # noqa: F401  (re-exported for callers/tests)

# ---- safety flags (defaults are the safe values) -------------------------------------
HYPERLIQUID_ENV = os.environ.get("HYPERLIQUID_ENV", "testnet")

# Execution is OFF and must stay EXACTLY False (identity, not truthiness) in this build.
HYPERLIQUID_EXECUTION_ENABLED = False

# Mainnet is NOT permitted in H1. An env override to "true" is itself a hard-fail signal,
# surfaced by safety.assert_testnet_safety — it does not silently flip policy.
HYPERLIQUID_MAINNET_ALLOWED = (os.environ.get("HYPERLIQUID_MAINNET_ALLOWED", "false").lower()
                               in ("1", "true", "yes"))

# ---- admissible environments + endpoints ---------------------------------------------
APPROVED_ENV = "testnet"

APPROVED_TESTNET_REST = "https://api.hyperliquid-testnet.xyz"
APPROVED_TESTNET_WS = "wss://api.hyperliquid-testnet.xyz/ws"
APPROVED_TESTNET_HOST = "api.hyperliquid-testnet.xyz"

# Only the public, NON-signing /info path may be POSTed. The signing route is never used.
APPROVED_REST_PATHS = ("/info",)

# Documented, configurable staleness threshold for observation admissibility (ms).
DEFAULT_MAX_AGE_MS = 5000

# The instrument we intend to observe. The MAPPING is never assumed — it must be resolved
# from the returned `meta` universe (see instruments.resolve_perp). This is only the name.
TARGET_PERP_NAME = "BTC"


def _host(url) -> str:
    try:
        netloc = urlparse(str(url)).netloc or urlparse("//" + str(url)).netloc
        return netloc.split("@")[-1].split(":")[0].lower()
    except (ValueError, AttributeError):
        return ""


def is_hyperliquid_host(url) -> bool:
    return "hyperliquid" in _host(url)


def is_testnet_endpoint(url) -> bool:
    """True only for a Hyperliquid TESTNET host (contains 'testnet')."""
    h = _host(url)
    return "hyperliquid" in h and "testnet" in h


def is_mainnet_endpoint(url) -> bool:
    """True for any Hyperliquid host that is NOT a testnet host. Rule-based so the literal
    mainnet hostname need never be written into our source."""
    h = _host(url)
    return "hyperliquid" in h and "testnet" not in h


def endpoint_is_approved_testnet(url) -> bool:
    return _host(url) == APPROVED_TESTNET_HOST and is_testnet_endpoint(url)


def execution_is_locked_off() -> bool:
    """Execution must be exactly False (identity, not truthiness)."""
    return HYPERLIQUID_EXECUTION_ENABLED is False
