"""
Brick 3 — broker-neutral READ-ONLY adapter interface + offline implementations.

Read-only BY CONSTRUCTION: this module defines NO order/execution methods and imports
NO order-request types. It connects to nothing on its own; the real adapter stays inactive
while credentials are missing. Demo/live separation is enforced via hard-fails.
"""
from __future__ import annotations
import abc

from . import config
from .secrets import safe_record
from .states import ConnectionStateMachine
from .quotes import QuoteContext, classify
from .oauth_scope import oauth_scope_for, OAUTH_TRADING


class BrokerSafetyError(Exception):
    pass


class SymbolError(Exception):
    pass


def assert_demo_safety(*, env, endpoint, scope, execution_enabled, account_meta=None):
    """Hard-fail the moment anything indicates LIVE, unproven-demo, trade scope, or
    enabled execution. Raises BrokerSafetyError; never returns a 'maybe'."""
    if execution_enabled is not False:
        raise BrokerSafetyError("execution is not exactly False")
    if env != "demo":
        raise BrokerSafetyError(f"environment is not demo: {env!r}")
    if endpoint is not None and endpoint not in config.APPROVED_DEMO_ENDPOINTS:
        raise BrokerSafetyError(f"endpoint not on demo allowlist: {endpoint!r}")
    s = (scope or "").lower()
    if "trade" in s or "trading" in s or "execut" in s:
        raise BrokerSafetyError(f"scope contains trade/execution permission: {scope!r}")
    if account_meta is not None:
        a_env = str(account_meta.get("environment") or "").lower()
        if a_env == "":
            raise BrokerSafetyError("account environment unknown")
        if a_env == "live":
            raise BrokerSafetyError("live account rejected")
        if a_env != "demo":
            raise BrokerSafetyError(f"account environment not demo: {a_env!r}")


class BrokerReadOnlyAdapter(abc.ABC):
    """Read-only interface. NOTE: there is deliberately NO order/execution method here."""

    def __init__(self, clock=None):
        self.sm = ConnectionStateMachine(clock=clock)
        self._symbol_verified = False
        self._selected_account = None
        self._subscriptions = set()

    def get_connection_state(self) -> str:
        return self.sm.get_connection_state()

    @abc.abstractmethod
    def connect(self): ...
    @abc.abstractmethod
    def authenticate_application(self): ...
    @abc.abstractmethod
    def list_accounts(self): ...
    @abc.abstractmethod
    def authenticate_account(self): ...
    @abc.abstractmethod
    def get_account(self): ...
    @abc.abstractmethod
    def list_symbols(self): ...
    @abc.abstractmethod
    def resolve_symbol(self, name): ...
    @abc.abstractmethod
    def subscribe_quotes(self, symbol_id): ...
    @abc.abstractmethod
    def unsubscribe_quotes(self, symbol_id): ...
    @abc.abstractmethod
    def get_positions(self): ...
    @abc.abstractmethod
    def disconnect(self): ...


# --------------------------------------------------------------------------- Mock
class MockCTraderReadOnlyAdapter(BrokerReadOnlyAdapter):
    """Drives the full state machine + safety checks against an injected scenario.
    Connects to nothing; all data comes from the scenario dict."""

    def __init__(self, scenario, clock=None):
        super().__init__(clock=clock)
        self.s = scenario

    # ---- connection / auth ----
    def connect(self):
        if not self.s.get("app_approved"):
            return self.get_connection_state()                  # stays APP_NOT_APPROVED
        assert_demo_safety(env=self.s.get("env", "demo"), endpoint=self.s.get("endpoint"),
                           scope=self.s.get("scope", "view"),
                           execution_enabled=config.CTRADER_EXECUTION_ENABLED)
        self.sm.transition("CREDENTIALS_MISSING", "app approved")
        if not self.s.get("credentials"):
            return self.get_connection_state()                  # controlled wait
        for nxt, why in [("AUTHORISATION_REQUIRED", "creds present"),
                         ("AUTHORISATION_CODE_RECEIVED", "browser auth"),
                         ("TOKEN_EXCHANGE_REQUIRED", "code received"),
                         ("TOKEN_AVAILABLE", "token exchanged")]:
            self.sm.transition(nxt, why)
        return self.get_connection_state()

    def authenticate_application(self):
        if self.sm.state != "TOKEN_AVAILABLE":
            raise BrokerSafetyError("application authentication preconditions not met")
        self.sm.transition("APPLICATION_AUTHENTICATED", "app authenticated")
        return self.get_connection_state()

    def list_accounts(self):
        if self.sm.state != "APPLICATION_AUTHENTICATED":
            raise BrokerSafetyError("must authenticate application before listing accounts")
        self.sm.transition("ACCOUNTS_DISCOVERED", "accounts listed")
        return [safe_record(a) for a in self.s.get("accounts", [])]

    def authenticate_account(self):
        if self.sm.state != "ACCOUNTS_DISCOVERED":
            raise BrokerSafetyError("must discover accounts before authenticating one")
        demo = [a for a in self.s.get("accounts", []) if str(a.get("environment", "")).lower() == "demo"]
        # enforce demo/live on the account we intend to select; live/unknown -> hard-fail
        if not demo:
            # surface the rejection reason for whatever was offered
            for a in self.s.get("accounts", []):
                assert_demo_safety(env=self.s.get("env", "demo"), endpoint=self.s.get("endpoint"),
                                   scope=self.s.get("scope", "view"),
                                   execution_enabled=config.CTRADER_EXECUTION_ENABLED,
                                   account_meta=a)
            raise BrokerSafetyError("no demo account available")
        account = demo[0]
        assert_demo_safety(env=self.s.get("env", "demo"), endpoint=self.s.get("endpoint"),
                           scope=self.s.get("scope", "view"),
                           execution_enabled=config.CTRADER_EXECUTION_ENABLED, account_meta=account)
        self._selected_account = account
        self.sm.transition("DEMO_ACCOUNT_SELECTED", "demo account selected")
        self.sm.transition("ACCOUNT_AUTHENTICATED", "account authenticated")
        self.sm.transition("READ_ONLY_READY", "read-only ready")
        return self.get_connection_state()

    # ---- reads (require READ_ONLY_READY) ----
    def _require_ready(self):
        if self.sm.state != "READ_ONLY_READY":
            raise BrokerSafetyError(f"read requested before READ_ONLY_READY (state={self.sm.state})")

    def get_account(self):
        self._require_ready()
        return safe_record(self._selected_account)

    def list_symbols(self):
        self._require_ready()
        return [safe_record(s) for s in self.s.get("symbols", [])]

    def resolve_symbol(self, name):
        self._require_ready()
        matches = [s for s in self.s.get("symbols", []) if s.get("name") == name]
        if len(matches) == 0:
            raise SymbolError(f"no symbol matches {name!r}")
        if len(matches) > 1:
            raise SymbolError(f"ambiguous symbol {name!r}: {len(matches)} matches — not assumed")
        self._symbol_verified = True
        return safe_record(matches[0])

    def subscribe_quotes(self, symbol_id):
        self._require_ready()
        if not self._symbol_verified:
            raise BrokerSafetyError("symbol not verified before subscribe")
        self._subscriptions.add(symbol_id)
        return {"subscribed": symbol_id}

    def unsubscribe_quotes(self, symbol_id):
        self._subscriptions.discard(symbol_id)
        return {"unsubscribed": symbol_id}

    def quote_context(self):
        return QuoteContext(connected=True, auth_ready=(self.sm.state == "READ_ONLY_READY"),
                            env_verified_demo=(self._selected_account is not None),
                            symbol_verified=self._symbol_verified,
                            max_age_ms=config.DEFAULT_MAX_QUOTE_AGE_MS)

    def get_positions(self):
        self._require_ready()
        return [safe_record(p) for p in self.s.get("positions", [])]

    def disconnect(self):
        self.sm.transition("DISCONNECTED", "controlled disconnect")
        return self.get_connection_state()


# ----------------------------------------------------------------- Replay (quotes)
class ReplayCTraderQuoteAdapter:
    """Deterministically replays a recorded quote sequence through the classifier.
    Identical input -> identical outputs and identical logical hash."""

    def __init__(self, quotes, ctx: QuoteContext):
        self._quotes = list(quotes)
        self._ctx = ctx

    def replay(self):
        out = []
        prev = None
        for q in self._quotes:
            status, flags = classify(q, prev, self._ctx)
            out.append({"symbol": q.symbol, "status": status, "flags": dict(flags)})
            # advance 'prev' only on quotes that are structurally comparable
            if status not in ("BROKER_NOT_CONNECTED", "AUTH_NOT_AVAILABLE",
                              "ENVIRONMENT_UNVERIFIED", "SYMBOL_UNVERIFIED", "INVALID_VALUE"):
                prev = q
        return out

    def logical_hash(self):
        import hashlib
        import json
        return hashlib.sha256(json.dumps(self.replay(), sort_keys=True).encode("utf-8")).hexdigest()


# ----------------------------------------------------------- Real adapter (inactive)
class CTraderDemoReadOnlyAdapter(BrokerReadOnlyAdapter):
    """The real demo adapter. In this build it REMAINS INACTIVE: with placeholder/empty
    credentials, connect() returns a controlled CREDENTIALS_MISSING state and attempts NO
    network. It contains no socket/order code; live connection is the separate, separately
    approved activation phase."""

    def connect(self):
        # hard safety gate first (execution off, demo env, endpoint allowlist)
        assert_demo_safety(env=config.CTRADER_ENV, endpoint=None, scope=config.CTRADER_SCOPE,
                           execution_enabled=config.CTRADER_EXECUTION_ENABLED)
        # scope authority: internal 'view' -> OAuth 'accounts'; never 'trading'.
        oauth_scope = oauth_scope_for(config.CTRADER_SCOPE)
        if oauth_scope == OAUTH_TRADING:                      # unreachable by construction
            raise BrokerSafetyError("refused: OAuth trading scope must never be emitted")
        self.sm.transition("CREDENTIALS_MISSING", "real adapter: app-approval/creds gate")
        # no credentials -> controlled wait, NO network attempted
        return self.get_connection_state()

    def _inactive(self, what):
        raise BrokerSafetyError(
            f"{what} requires an approved, connected demo session (activation phase) — "
            f"inactive in this build; state={self.sm.state}")

    def authenticate_application(self): self._inactive("authenticate_application")
    def list_accounts(self): self._inactive("list_accounts")
    def authenticate_account(self): self._inactive("authenticate_account")
    def get_account(self): self._inactive("get_account")
    def list_symbols(self): self._inactive("list_symbols")
    def resolve_symbol(self, name): self._inactive("resolve_symbol")
    def subscribe_quotes(self, symbol_id): self._inactive("subscribe_quotes")
    def unsubscribe_quotes(self, symbol_id): self._inactive("unsubscribe_quotes")
    def get_positions(self): self._inactive("get_positions")

    def disconnect(self):
        self.sm.transition("DISCONNECTED", "controlled disconnect")
        return self.get_connection_state()
