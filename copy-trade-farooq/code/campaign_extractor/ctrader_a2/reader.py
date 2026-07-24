"""
A2 VIEW-ONLY reader — deterministic, no retry, no OAuth, 429-stops-immediately.

Flow: load cached token -> app auth -> account list -> require SCOPE_VIEW -> reject isLive=true
-> present demo accounts for HUMAN selection (never auto-select) -> [human picks] -> account
auth -> read basic info + XAUUSD spec -> clean disconnect. No order path exists.
"""
from __future__ import annotations
import os

import sys as _sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_CE = os.path.dirname(_HERE)
for p in (_HERE, _CE):
    if p not in _sys.path:
        _sys.path.insert(0, p)
from errors import (TokenMissing, RateLimited429, ScopeRejected, LiveAccountRejected,
                    NoDemoAccount)
import masking
import token_loader
from ctrader_a1 import scope_validator, account_validator

REQUESTED_SCOPE = scope_validator.requested_oauth_scope()   # 'accounts' (view-only); never 'trading'


class A2Reader:
    def __init__(self, transport, token_loader_fn=None):
        self.t = transport
        self._load = token_loader_fn or token_loader.load_cached_token
        self._token = None

    def load_token(self):
        tok = self._load()
        if not tok or not tok.get("access_token"):
            raise TokenMissing("no cached view-only token available; A2 does not mint/request one")
        self._token = tok
        return True

    def discover_accounts(self):
        """App-auth + account list; require SCOPE_VIEW; reject live; return demo candidates for
        HUMAN selection. Does NOT authenticate any account (that waits for the human choice)."""
        if self._token is None:
            self.load_token()
        try:
            self.t.app_auth()
        except RateLimited429 as e:
            e.stage = "APPLICATION_AUTH"
            raise
        try:
            res = self.t.get_account_list(self._token["access_token"])
        except RateLimited429 as e:
            e.stage = "GET_ACCOUNT_LIST"
            raise

        scope = (res or {}).get("permission_scope")
        if not scope_validator.returned_scope_is_view_only(scope):
            raise ScopeRejected("returned permission scope is not SCOPE_VIEW (view-only required)")

        accounts = (res or {}).get("accounts", [])
        verdict = account_validator.validate_demo_selection(accounts)
        if verdict["status"] == "REJECTED_LIVE_ONLY":
            raise LiveAccountRejected("only isLive=true account(s) present — rejected")
        if verdict["status"] == "NO_DEMO_ACCOUNT":
            raise NoDemoAccount("no isLive=false demo account available")

        self._demo_ids = set(verdict["candidates"])
        return {
            "status": verdict["status"],
            "requires_human_selection": True,          # ALWAYS: never auto-select
            "demo_candidates": [
                {"account_id_masked": masking.mask_account_id(c)} for c in verdict["candidates"]],
            "raw_candidate_ids": list(verdict["candidates"]),
        }

    def read_selected(self, account_id):
        """Read basic info for a HUMAN-selected demo account, then disconnect cleanly."""
        if account_id not in getattr(self, "_demo_ids", set()):
            raise LiveAccountRejected("selected account is not among verified demo candidates")
        try:
            self.t.account_auth(account_id, self._token["access_token"])
        except RateLimited429 as e:
            e.stage = "ACCOUNT_AUTH"
            raise
        try:
            info = self.t.get_account_info(account_id) or {}
        except RateLimited429 as e:
            e.stage = "ACCOUNT_INFO"
            raise
        if info.get("isLive") is True:                 # defence-in-depth
            self.t.disconnect()
            raise LiveAccountRejected("selected account reports isLive=true — rejected")
        try:
            sym = self.t.get_symbol(account_id, "XAUUSD")
        except RateLimited429 as e:
            e.stage = "SYMBOL"
            raise
        self.t.disconnect()

        xauusd = {"available": bool(sym)}
        if sym:
            xauusd.update({k: sym.get(k) for k in
                           ("digits", "pip_position", "lot_size", "min_volume", "symbol_id")})
        return {
            "account_id_masked": masking.mask_account_id(account_id),
            "broker": info.get("broker"), "server": info.get("server"),
            "currency": info.get("currency"), "balance": info.get("balance"),
            "isLive": info.get("isLive"),
            "xauusd": xauusd,
            "connection": "DISCONNECTED_CLEAN",
            "note": "provider-reported read-only snapshot; no order path; view-only scope",
        }
