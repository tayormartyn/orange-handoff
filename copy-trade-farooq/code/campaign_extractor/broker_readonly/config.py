"""
Brick 3 — broker read-only config PLACEHOLDERS (no real values, ever).

Isolated from the existing top-level ctrader_config.py. Holds only non-secret
placeholders. Credentials come from the environment and default to empty; an empty
credential is a CONTROLLED state, never a crash. This module connects to nothing.
"""
import os

ADAPTER_VERSION = "broker-ro-0.1.0"

# ---- placeholders (never commit real values; empty by default) ----
CTRADER_ENV = os.environ.get("CTRADER_ENV", "demo")
CTRADER_SCOPE = os.environ.get("CTRADER_SCOPE", "view")
CTRADER_CLIENT_ID = os.environ.get("CTRADER_CLIENT_ID", "")
CTRADER_CLIENT_SECRET = os.environ.get("CTRADER_CLIENT_SECRET", "")
CTRADER_ACCESS_TOKEN = os.environ.get("CTRADER_ACCESS_TOKEN", "")
CTRADER_REFRESH_TOKEN = os.environ.get("CTRADER_REFRESH_TOKEN", "")
CTRADER_ACCOUNT_ID = os.environ.get("CTRADER_ACCOUNT_ID", "")
CTRADER_EXECUTION_ENABLED = False          # MUST stay exactly False in this build

# Only demo endpoints are admissible in this phase.
APPROVED_DEMO_ENDPOINTS = ("demo.ctraderapi.com",)

# Documented, configurable staleness threshold for quote admissibility.
DEFAULT_MAX_QUOTE_AGE_MS = 5000


def credentials_present() -> bool:
    return bool(CTRADER_CLIENT_ID and CTRADER_CLIENT_SECRET and CTRADER_ACCESS_TOKEN)


def execution_is_locked_off() -> bool:
    """Hard rule 6: execution must be exactly False (identity, not truthiness)."""
    return CTRADER_EXECUTION_ENABLED is False
