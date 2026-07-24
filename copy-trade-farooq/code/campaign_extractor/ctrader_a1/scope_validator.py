"""
Scope safety — reuses the single existing authority broker_readonly/oauth_scope.py.

Accepts ONLY a positively verified view-only returned scope (SCOPE_VIEW). Rejects SCOPE_TRADE,
combined/ambiguous, missing, unknown, or malformed scopes. Never silently downgrades a
trade-capable scope. No trading scope is ever emitted.
"""
from __future__ import annotations
import os

import sys as _sys
_CE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _CE not in _sys.path:
    _sys.path.insert(0, _CE)
from broker_readonly.oauth_scope import (oauth_scope_for, assert_returned_scope_admissible,
                                         RETURNED_VIEW, OAUTH_ACCOUNTS, ScopeError)


def requested_oauth_scope():
    """internal 'view' -> OAuth 'accounts' (view-only). 'trading' is never emitted."""
    return oauth_scope_for("view")          # == 'accounts'


def returned_scope_is_view_only(returned):
    """True ONLY for an exact SCOPE_VIEW. Everything else (SCOPE_TRADE, combined, missing,
    unknown, malformed) is rejected."""
    if returned is None or not isinstance(returned, str):
        return False
    if returned.strip() != RETURNED_VIEW:   # exact match: no combined / whitespace-padded / case
        return False
    try:
        return bool(assert_returned_scope_admissible(returned))
    except ScopeError:
        return False
