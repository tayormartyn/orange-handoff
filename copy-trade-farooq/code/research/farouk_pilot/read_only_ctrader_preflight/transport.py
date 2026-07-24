"""View-only cTrader transport. Connects ONLY to demo.ctraderapi.com:5035 and exposes ONLY
typed read methods (each backed by read_ops' whitelist). There is deliberately NO public
send()/write()/dispatch() that accepts an arbitrary message, and NO raw-payload entrypoint.

Phase 1 (this deliverable): the package is importable and statically provable WITHOUT the
protobuf library or any network. connect() is GATED: it refuses unless the operator has done
the accounts-scope OAuth grant AND opted in (config.PHASE2_CONNECT_OPT_IN) - so Phase 1 never
opens a socket. ctrader_open_api and ssl/socket are imported LAZILY inside connect(), so no
network module is imported at package import time.
"""
from . import config, read_ops


class NotConnected(Exception):
    pass


class ArbitrarySendRefused(Exception):
    pass


class ViewOnlyTransport:
    """Typed view-only read surface. No generic send; every method builds exactly one
    whitelisted request via read_ops and dispatches it through the private, name-checked path."""

    def __init__(self):
        self._client = None
        self.endpoint = (config.DEMO_HOST, config.DEMO_PORT)   # fixed; not overridable

    # ---- Phase-2 connection (GATED; never runs in Phase 1) ----
    def connect(self):
        if not config.PHASE2_CONNECT_OPT_IN:
            raise NotConnected(
                "Phase 2 not authorised: set the accounts-scope OAuth token + "
                "ORANGE_PREFLIGHT_CONNECT=1 only after the operator's view-only grant. "
                "Phase 1 is static proof only; this tool does not connect.")
        # LAZY imports so no network/protobuf module loads at package import time.
        import ssl                                             # noqa: F401  (Phase-2 only)
        from ctrader_open_api import Client, TcpProtocol       # noqa: F401
        host, port = config.DEMO_HOST, config.DEMO_PORT        # DEMO ONLY, fixed host:port
        self._client = Client(host, port, TcpProtocol)
        return self

    # ---- the ONLY dispatch path: private + name-checked against the whitelist ----
    def _send_whitelisted(self, request):
        name = type(request).__name__
        if name not in read_ops.ALLOWED_READ_MESSAGES:
            raise ArbitrarySendRefused(f"message type {name} is not in the read whitelist")
        if self._client is None:
            raise NotConnected("not connected (Phase 2 gate)")
        return self._client.send(request)

    # ---- typed read methods (the entire public surface) ----
    def authenticate_app(self, client_id, client_secret):
        return self._send_whitelisted(read_ops.build_application_auth(client_id, client_secret))

    def list_accounts(self, access_token):
        return self._send_whitelisted(read_ops.build_account_list(access_token))

    def account_auth(self, ctid, access_token):
        return self._send_whitelisted(read_ops.build_account_auth(ctid, access_token))

    def get_trader(self, ctid):
        return self._send_whitelisted(read_ops.build_trader(ctid))

    def list_symbols(self, ctid):
        return self._send_whitelisted(read_ops.build_symbols_list(ctid))

    def get_symbol(self, ctid, symbol_id):
        return self._send_whitelisted(read_ops.build_symbol_by_id(ctid, symbol_id))

    def heartbeat(self):
        return self._send_whitelisted(read_ops.build_heartbeat())
