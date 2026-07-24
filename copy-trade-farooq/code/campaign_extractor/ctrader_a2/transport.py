"""
Transport interface for the A2 reader. The real implementation (live_transport.py) wraps the
ctrader_open_api Twisted client; offline tests inject a mock. VIEW-ONLY: the interface exposes
ONLY read operations — there is no order/amend/cancel/close method anywhere.
"""
from __future__ import annotations


class Transport:
    def app_auth(self):
        """ProtoOAApplicationAuthReq — authenticate the application. May raise RateLimited429."""
        raise NotImplementedError

    def get_account_list(self, access_token):
        """ProtoOAGetAccountListByAccessTokenReq -> {permission_scope, accounts:[{account_id,isLive}]}."""
        raise NotImplementedError

    def account_auth(self, account_id, access_token):
        """ProtoOAAccountAuthReq — authorise reads for one account."""
        raise NotImplementedError

    def get_account_info(self, account_id):
        """ProtoOATraderReq -> {broker, server, currency, balance, isLive}."""
        raise NotImplementedError

    def get_symbol(self, account_id, symbol_name):
        """ProtoOASymbolsListReq / ProtoOASymbolByIdReq -> spec dict or None."""
        raise NotImplementedError

    def disconnect(self):
        """Close the connection cleanly."""
        raise NotImplementedError
