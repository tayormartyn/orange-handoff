"""
Masked presence reporting. Returns ONLY one of: PRESENT / MISSING / EMPTY / MALFORMED_FORMAT.
Never returns, prints, or samples a value, prefix, or suffix.
"""
from __future__ import annotations
import re

STATES = ("PRESENT", "MISSING", "EMPTY", "MALFORMED_FORMAT")

# light shape checks — used ONLY to classify; never echo what matched.
_FORMAT = {
    "CTRADER_CLIENT_ID": re.compile(r"^\d+_[A-Za-z0-9]{16,}$"),
    "CTRADER_CLIENT_SECRET": re.compile(r"^[A-Za-z0-9]{16,}$"),
    "CTRADER_ACCESS_TOKEN": re.compile(r"^[A-Za-z0-9._\-]{16,}$"),
    "CTRADER_REFRESH_TOKEN": re.compile(r"^[A-Za-z0-9._\-]{16,}$"),
    "CTRADER_ACCOUNT_ID": re.compile(r"^\d+$"),
    "CTRADER_ENV": re.compile(r"^(demo|live)$"),
    "CTRADER_SCOPE": re.compile(r"^(view|accounts)$"),
    "CTRADER_REDIRECT_URI": re.compile(r"^https?://[^\s]+$"),
    "CTRADER_GOLD_SYMBOL": re.compile(r"^[A-Z]{3,10}$"),
}


def presence(name, env):
    """env: dict of name->value. Returns a masked state ONLY."""
    if name not in env:
        return "MISSING"
    v = env[name]
    if v == "":
        return "EMPTY"
    pat = _FORMAT.get(name)
    if pat is not None and not pat.match(v):
        return "MALFORMED_FORMAT"
    return "PRESENT"


def report(env, names):
    return {n: presence(n, env) for n in names}
