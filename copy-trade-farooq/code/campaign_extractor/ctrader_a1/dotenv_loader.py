"""
Deterministic dotenv loader for the ONE authoritative project .env.

* project-root path resolved EXPLICITLY (no walking parent directories);
* parses KEY=VALUE; ignores comments/blank lines;
* NEVER logs/prints a value (returns a dict the caller must keep private);
* fail-closed: a missing file / missing var is reported, never guessed;
* process-environment PRECEDENCE: an already-set os.environ value is NOT overwritten;
* cTrader configuration is ISOLATED from Telegram configuration (only CTRADER_* is returned).
"""
from __future__ import annotations
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
# explicit: ctrader_a1 -> campaign_extractor -> signal-terminal
PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")

CTRADER_KEYS = (
    "CTRADER_CLIENT_ID", "CTRADER_CLIENT_SECRET", "CTRADER_ACCESS_TOKEN",
    "CTRADER_REFRESH_TOKEN", "CTRADER_ACCOUNT_ID", "CTRADER_ENV", "CTRADER_SCOPE",
    "CTRADER_REDIRECT_URI", "CTRADER_GOLD_SYMBOL",
)


def _parse(path):
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def load_ctrader_env(path=None):
    """Return ONLY CTRADER_* entries from the authoritative .env (values kept private).
    Fail-closed: returns {} if the file is absent (caller treats missing as MISSING)."""
    path = path or ENV_PATH
    if not os.path.exists(path):
        return {}
    raw = _parse(path)
    return {k: v for k, v in raw.items() if k.startswith("CTRADER_")}   # isolated from TELEGRAM_*


def apply_to_environ(ctrader_env):
    """Set CTRADER_* into os.environ ONLY where not already present (process precedence).
    Returns the list of NAMES applied (never values)."""
    applied = []
    for k, v in ctrader_env.items():
        if k not in os.environ:
            os.environ[k] = v
            applied.append(k)
    return applied
