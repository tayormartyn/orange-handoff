"""
Cached-token loader. Loads an EXISTING token only; never mints, refreshes, or requests a new
authorisation code/token, and never opens an authorisation URL.
"""
from __future__ import annotations
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))
TOKEN_PATH = os.path.join(PROJECT_ROOT, "data", "ctrader_token.json")


def load_cached_token(path=None):
    """Return the cached token dict, or None if absent/unreadable/empty. No OAuth, no network."""
    path = path or TOKEN_PATH
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None
    return d if d.get("access_token") else None
