"""Demo-lane REAL ORDER ADAPTER (mock-first).

Responsibilities: translate an executor intent dict -> a canonical BrokerOrderRequest (LIMIT-only,
protective stop required, GOOD_TILL_DATE), dispatch it through an INJECTED channel (mock in this
build), and map the raw ack -> a canonical ack (the reconciliation + protection facts the executor
needs). It provides the mechanical primitives (cancel_order, close_reduce, list_positions).

NON-goals (single source of truth stays elsewhere):
  * The SEVEN-FIELD exact-equality reconciliation lives ONLY in the executor. A security-critical
    check must have exactly ONE implementation - two copies drift apart and the divergence is
    silent - so the adapter NEVER compares ack vs request; it only supplies the canonical ack.
  * No ctrader_open_api import, no socket, no network, no real credentials.

PRODUCTION GATE AUTHORITY (Chuck bounded-fix 2): the production construction path
(RealOrderAdapter.for_production) derives dispatch enablement SOLELY from the AUTHORITATIVE gates
(config.EXECUTION_ENABLED / CTRADER_EXECUTION_ENABLED / DEMO_EXECUTION_ENABLED). It accepts NO
caller-controlled 'enabled' override, no CLI/env override. The only way to enable dispatch is a
test_only_policy, which is BOUND to a MockOrderChannel (it refuses any non-mock channel).
"""
from . import config
from .broker_request import BrokerOrderRequest


class AdapterHalt(Exception):
    """Translation refused (non-LIMIT opening, or missing protective stop)."""


class AdapterGateRefused(Exception):
    """Dispatch refused: authoritative gates False (NOT_ARMED), or a test-only enabled policy was
    pointed at a non-mock channel."""


class DispatchPolicy:
    """Constructed ONLY via production_policy() or test_only_policy() below - never directly with a
    caller-supplied enabled flag on the production path."""
    def __init__(self, dispatch_enabled, requires_mock_channel):
        self.dispatch_enabled = bool(dispatch_enabled)
        self.requires_mock_channel = bool(requires_mock_channel)


def production_policy():
    """AUTHORITATIVE gates ONLY; NO caller override. Enabled iff the demo gate is True AND the live
    gates are False (the demo lane never rides a weakened live gate). All three are hard False, so
    this is always disabled -> NOT_ARMED."""
    enabled = (bool(config.DEMO_EXECUTION_ENABLED)
               and not config.EXECUTION_ENABLED and not config.CTRADER_EXECUTION_ENABLED)
    return DispatchPolicy(dispatch_enabled=enabled, requires_mock_channel=False)


def test_only_policy(dispatch_enabled=True):
    """A test seam: may enable dispatch, but is BOUND to a MockOrderChannel (place_limit refuses a
    non-mock channel). It cannot arm a production/real channel."""
    return DispatchPolicy(dispatch_enabled=dispatch_enabled, requires_mock_channel=True)


def _is_mock(channel):
    return bool(getattr(channel, "IS_MOCK", False))


class RealOrderAdapter:
    def __init__(self, channel, policy=None):
        self.channel = channel
        self.policy = policy or production_policy()      # default: authoritative (NOT_ARMED)

    @classmethod
    def for_production(cls, channel):
        """Production entry point. Takes NO 'enabled' argument - enablement is a pure function of
        the authoritative gates (all hard False -> NOT_ARMED)."""
        return cls(channel, production_policy())

    # ---- the interface the executor already calls ----
    def symbol_meta(self, symbol_id):
        return self.channel.symbol_meta(symbol_id)

    def list_orders(self):
        return self.channel.list_orders()

    def list_positions(self):
        return self.channel.list_positions()

    def orders_past_expiry(self, now_ts):
        return self.channel.orders_past_expiry(now_ts)

    def cancel_order(self, order_id):
        return self.channel.send_cancel(order_id)

    # ---- translation: intent dict -> canonical BrokerOrderRequest ----
    def translate(self, req):
        if req.get("type") != "LIMIT":
            raise AdapterHalt(f"opening order must be LIMIT-only, got {req.get('type')!r}")
        if req.get("stop_price") is None:
            raise AdapterHalt("request has no protective stop - refusing to build an unprotected order")
        return BrokerOrderRequest(
            ctid_trader_account_id=req["account_id"], symbol_id=req["symbol"],
            trade_side=req["side"], volume=req["volume"], limit_price=req["entry_price"],
            stop_loss=req["stop_price"], expiration_timestamp=req["expiry_ts"],
            order_type="LIMIT", time_in_force=req.get("time_in_force", "GOOD_TILL_DATE"))

    # ---- gated dispatch + canonical ack (NO reconciliation here) ----
    def place_limit(self, req):
        spec = self.translate(req)
        if not self.policy.dispatch_enabled:
            raise AdapterGateRefused("NOT_ARMED - authoritative gates False (dispatch disabled)")
        if self.policy.requires_mock_channel and not _is_mock(self.channel):
            raise AdapterGateRefused("test-only enabled policy cannot drive a non-mock channel")
        raw = self.channel.send_open(spec)
        if raw is None:
            return None                        # lost response -> executor OUTCOME_UNKNOWN
        return self._canonical(req, raw)

    def _canonical(self, req, raw):
        vol = req["volume"]
        filled = int(raw.get("filled_volume", 0) or 0)
        return {
            # --- fields the executor reconciles (mapped back into the request's vocabulary) ---
            "account_id": raw.get("account_id", req["account_id"]),
            "symbol": raw.get("symbol_id", req["symbol"]),
            "side": raw.get("trade_side", req["side"]),
            "type": "LIMIT",
            "volume": raw.get("volume", vol),
            "entry_price": raw.get("limit_price", req["entry_price"]),
            "stop_price": raw.get("stop_loss", None),
            "expiry_ts": raw.get("expiration_timestamp", req["expiry_ts"]),
            "order_id": raw.get("order_id"),
            # --- protection facts the executor's 6a step consumes ---
            "stop_attached": bool(raw.get("stop_accepted", False)),
            "filled_volume": filled,
            "pending_volume": max(vol - filled, 0),
            "position_id": raw.get("position_id"),
            "status": raw.get("status", "PENDING"),
        }

    # ---- close-ONLY risk reduction ----
    def close_reduce(self, position_id, volume, owner_check="ORANGE"):
        """Reduce an owned position only. The channel refuses non-owned / over-close / non-positive;
        there is no path here that increases or reverses a position."""
        return self.channel.send_close(position_id, volume, owner_check)
