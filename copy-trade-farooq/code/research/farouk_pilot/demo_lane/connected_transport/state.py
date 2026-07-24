"""Auth/connection state machine + deterministic correlation registry.

STATE ORDERING (enforced): an order-family request may be sent ONLY from READY, which is reached
strictly via CONNECTED -> APP_AUTHED -> ACCOUNT_AUTHED -> (RECONCILE) -> READY. After a reconnect
the machine returns to CONNECTED and MUST re-auth and RECONCILE before any action send is allowed
(RECONCILE_ONLY window). This is the single place 'are we allowed to act yet?' is decided.

CORRELATION (deterministic, no blind resend): every request key maps to a stable client_msg_id.
A key that is already in flight (or already resolved) is REFUSED — the transport never re-sends a
request blindly. A response matches by client_msg_id. A timed-out request is marked OUTCOME_UNKNOWN
and is NEVER auto-resent.
"""
import hashlib
import json

from . import framing


class AuthState:
    # the EXACT sequence (D-110 / Chuck completion item 3):
    #   CONNECTED -> APPLICATION_AUTHENTICATED -> ACCOUNT_LIST_RECEIVED -> ACCOUNT_VALIDATED
    #             -> ACCOUNT_AUTHENTICATED -> RECONCILE_ONLY -> READY
    DISCONNECTED = "DISCONNECTED"
    CONNECTED = "CONNECTED"                         # socket/TLS up, not app-authed
    APPLICATION_AUTHENTICATED = "APPLICATION_AUTHENTICATED"
    ACCOUNT_LIST_RECEIVED = "ACCOUNT_LIST_RECEIVED"   # account list back, NOT yet validated
    ACCOUNT_VALIDATED = "ACCOUNT_VALIDATED"           # allowlist guard passed -> account-auth permitted
    ACCOUNT_AUTHENTICATED = "ACCOUNT_AUTHENTICATED"   # account-authed; must still reconcile
    RECONCILE_ONLY = "RECONCILE_ONLY"                 # reconcile in flight; NO action send yet
    READY = "READY"                                   # authed + validated + reconciled -> actions
    CLOSED = "CLOSED"


class StateError(Exception):
    """An operation was attempted from a state that forbids it (fail-closed)."""


# the state from which each outbound family is permitted. NOTE: ACCOUNT_AUTH_REQ is permitted ONLY
# from ACCOUNT_VALIDATED — the account-list allowlist guard MUST pass before account-auth is sent.
_SENDABLE_ANYTIME = {AuthState.CONNECTED, AuthState.APPLICATION_AUTHENTICATED,
                     AuthState.ACCOUNT_LIST_RECEIVED, AuthState.ACCOUNT_VALIDATED,
                     AuthState.ACCOUNT_AUTHENTICATED, AuthState.RECONCILE_ONLY, AuthState.READY}
_ALLOWED_FROM = {
    framing.MsgType.APP_AUTH_REQ: {AuthState.CONNECTED},
    framing.MsgType.ACCOUNT_LIST_REQ: {AuthState.APPLICATION_AUTHENTICATED},
    framing.MsgType.ACCOUNT_AUTH_REQ: {AuthState.ACCOUNT_VALIDATED},      # ONLY after validation
    framing.MsgType.HEARTBEAT: set(_SENDABLE_ANYTIME),
    framing.MsgType.RECONCILE_REQ: {AuthState.ACCOUNT_AUTHENTICATED, AuthState.RECONCILE_ONLY,
                                    AuthState.READY},
    # every action family requires READY (authed AND validated AND reconciled)
    framing.MsgType.OPEN_LIMIT_REQ: {AuthState.READY},
    framing.MsgType.CANCEL_PENDING_REQ: {AuthState.READY},
    framing.MsgType.CLOSE_REDUCE_REQ: {AuthState.READY},
    framing.MsgType.AMEND_STOP_REQ: {AuthState.READY},
}


class ConnectionState:
    def __init__(self):
        self.state = AuthState.DISCONNECTED
        self.reconciled = False
        self.account_validated = False

    def can_send(self, msg_type):
        return self.state in _ALLOWED_FROM.get(msg_type, set())

    def assert_can_send(self, msg_type):
        if msg_type not in framing.PERMITTED_OUTBOUND:
            raise StateError(f"{msg_type} is not a permitted outbound family (no raw/generic send)")
        if not self.can_send(msg_type):
            raise StateError(f"send of {msg_type} refused in state {self.state} "
                             f"(validated={self.account_validated}, reconciled={self.reconciled})")
        return True

    # ---- transitions (ONLY these paths exist; each checks its predecessor) ----
    def on_connected(self):
        self.state = AuthState.CONNECTED
        self.reconciled = False
        self.account_validated = False              # a fresh socket is never pre-validated

    def on_app_authed(self):
        if self.state != AuthState.CONNECTED:
            raise StateError(f"APP_AUTH_RES out of order in {self.state}")
        self.state = AuthState.APPLICATION_AUTHENTICATED

    def on_account_list(self):
        if self.state != AuthState.APPLICATION_AUTHENTICATED:
            raise StateError(f"ACCOUNT_LIST_RES out of order in {self.state}")
        self.state = AuthState.ACCOUNT_LIST_RECEIVED

    def on_account_validated(self):
        if self.state != AuthState.ACCOUNT_LIST_RECEIVED:
            raise StateError(f"account validation invalid in {self.state}")
        self.account_validated = True
        self.state = AuthState.ACCOUNT_VALIDATED

    def on_account_authed(self):
        if self.state != AuthState.ACCOUNT_VALIDATED:
            raise StateError(f"ACCOUNT_AUTH_RES before ACCOUNT_VALIDATED (was {self.state})")
        self.state = AuthState.ACCOUNT_AUTHENTICATED
        self.reconciled = False                     # must reconcile before acting

    def on_reconcile_start(self):
        if self.state != AuthState.ACCOUNT_AUTHENTICATED:
            raise StateError(f"reconcile start invalid in {self.state}")
        self.state = AuthState.RECONCILE_ONLY

    def on_reconciled(self):
        if self.state not in (AuthState.RECONCILE_ONLY, AuthState.READY):
            raise StateError(f"reconcile completion invalid in {self.state}")
        self.reconciled = True
        self.state = AuthState.READY

    def on_disconnected(self):
        # a disconnect INVALIDATES account-validation; the full sequence is required again
        self.state = AuthState.DISCONNECTED
        self.reconciled = False
        self.account_validated = False

    def on_closed(self):
        self.state = AuthState.CLOSED
        self.reconciled = False
        self.account_validated = False


# --------------------------------------------------------------------------------------------------
class Correlation:
    PENDING = "PENDING"
    RESOLVED = "RESOLVED"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"


class CorrelationRegistry:
    """Deterministic client_msg_id per request key; in-flight/resolved keys are never re-sent."""
    def __init__(self):
        self._by_key = {}          # key_hash -> {cmid, status, result}
        self._by_cmid = {}         # cmid -> key_hash

    @staticmethod
    def _key_hash(key):
        return hashlib.sha256(json.dumps(key, sort_keys=True, default=str).encode()).hexdigest()

    @staticmethod
    def client_msg_id(key):
        return "ORG-" + CorrelationRegistry._key_hash(key)[:20]

    def register(self, key):
        """Reserve a correlation for a NEW request. Refuses if the key is already in flight or
        already resolved (no blind resend / duplicate-send prevention)."""
        kh = self._key_hash(key)
        existing = self._by_key.get(kh)
        if existing is not None:
            raise StateError(f"duplicate send refused: correlation already {existing['status']} "
                             f"(cmid={existing['cmid']})")
        cmid = "ORG-" + kh[:20]
        self._by_key[kh] = {"cmid": cmid, "status": Correlation.PENDING, "result": None}
        self._by_cmid[cmid] = kh
        return cmid

    def resolve(self, cmid, result):
        kh = self._by_cmid.get(cmid)
        if kh is None:
            return None                              # unknown correlation (caller decides handling)
        rec = self._by_key[kh]
        rec["status"] = Correlation.RESOLVED
        rec["result"] = result
        return rec

    def mark_unknown(self, cmid):
        kh = self._by_cmid.get(cmid)
        if kh is None:
            return None
        rec = self._by_key[kh]
        rec["status"] = Correlation.OUTCOME_UNKNOWN
        return rec

    def forget(self, cmid):
        """Release a correlation whose request DEFINITIVELY never left the machine (loss-BEFORE-send).
        Only valid while PENDING — a resolved/unknown correlation is never forgotten. This is NOT a
        resend; it lets a caller deliberately re-issue a request the broker provably never saw."""
        kh = self._by_cmid.get(cmid)
        if kh is None:
            return None
        if self._by_key[kh]["status"] != Correlation.PENDING:
            raise StateError("refusing to forget a non-pending correlation")
        del self._by_key[kh]
        del self._by_cmid[cmid]
        return cmid

    def status(self, cmid):
        kh = self._by_cmid.get(cmid)
        return self._by_key[kh]["status"] if kh else None

    def pending_cmids(self):
        return [r["cmid"] for r in self._by_key.values() if r["status"] == Correlation.PENDING]
