"""
Console adapter over the demo_executor services (NO trading logic here). Maps: cached read-only
preflight -> AccountSnapshot/SymbolMeta; latest recorded quote -> Quote; a CONFIRMED SIGNAL review
-> SignalInput; then calls demo_executor.proposals to build a DRY-RUN preview. Sends nothing.
"""
from __future__ import annotations
import json
import os
import sqlite3
import time
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_PL = os.path.dirname(_HERE)
_CE = os.path.dirname(_PL)
_ROOT = os.path.dirname(_CE)
_DE = os.path.join(_CE, "demo_executor")
import sys
for p in (_DE, _CE):
    if p not in sys.path:
        sys.path.insert(0, p)

import proposals as PROP
import update_plans as UPL
import config as DECFG
from audit_db import AuditDB
from models import BrokerPosition
from models import AccountSnapshot, SymbolMeta, Quote, SignalInput

PREFLIGHT_CACHE = os.path.join(_ROOT, "data", "demo_preflight_cache.json")
QUOTES_DB = os.path.join(_ROOT, "data", "ctrader_quotes_v1.db")
FX_USD_TO_GBP_APPROX = 0.79            # flagged approximate; real FX must be reconciled before any real order
_PROPOSALS = {}                        # in-memory proposal store for arm/approve (this phase)


def _ms(iso):
    if not iso:
        return None
    try:
        d = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return int((d if d.tzinfo else d.replace(tzinfo=timezone.utc)).timestamp() * 1000)
    except Exception:
        return None


def _now_ms():
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def load_account_and_symbol():
    """From the cached LIVE read-only preflight (balance READ, not assumed). Marks source + token scope."""
    if not os.path.exists(PREFLIGHT_CACHE):
        return None, None, "NO_PREFLIGHT_CACHE"
    c = json.load(open(PREFLIGHT_CACHE, encoding="utf-8"))
    a, s = c["account"], c["symbol_raw_ctrader"]
    account = AccountSnapshot(account_id=a["account_id"], is_live=a["is_live"], balance=a["balance"],
                              currency=a["currency"], trade_scope=a["token_scope"], environment="DEMO")
    # map cTrader raw volume units -> lots (1 lot = lot_size units); contract oz/lot = 100 (standard XAUUSD)
    lot_units = float(s["lot_size"])
    symbol = SymbolMeta(symbol_id=41, name="XAUUSD", digits=s["digits"], point=10 ** (-s["digits"]),
                        lot_size=100.0, min_volume=round(s["min_volume"] / lot_units, 4),
                        max_volume=round(s["max_volume"] / lot_units, 4),
                        volume_step=round(s["step_volume"] / lot_units, 4),
                        min_stop_distance_points=(s.get("min_stop_distance") or 50.0),
                        quote_currency="USD")
    return account, symbol, c.get("source", "CACHE")


def latest_quote():
    if not os.path.exists(QUOTES_DB):
        return None
    c = sqlite3.connect(f"file:{QUOTES_DB}?mode=ro", uri=True)
    row = c.execute("SELECT norm_bid, norm_ask, persisted_utc FROM normalised_quotes "
                    "WHERE norm_bid IS NOT NULL AND norm_ask IS NOT NULL ORDER BY rowseq DESC LIMIT 1").fetchone()
    c.close()
    if not row:
        return None
    return Quote(float(row[0]), float(row[1]), _ms(row[2]) or 0)


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def signal_from_review(review, signal_id=None):
    f = review.get("fields") or {}

    def v(k):
        return (f.get(k) or {}).get("value")
    tps = v("target_prices")
    targets = [t.strip() for t in str(tps).split(",") if t.strip()] if tps else None
    return SignalInput(
        signal_id=signal_id or review.get("intake_id"), intake_class=review.get("intake_class"),
        confirmed=review.get("explicit_confirmation_state") == "CONFIRMED",
        instrument=v("instrument"), direction=v("direction"),
        entry_low=_f(v("entry_low")), entry_high=_f(v("entry_high")), stop=_f(v("stop_price")),
        targets=targets, provider_verified=(review.get("provider") or {}).get("verification_state") == "PROVIDER_VERIFIED",
        confirmed_at_ms=_ms(review.get("review_created_at_utc")), duplicate=False, synthetic=False)


def build_preview(review, *, risk_pct=None, manual_entry=None, audit_path=None):
    account, symbol, source = load_account_and_symbol()
    if account is None:
        return {"error": "PREFLIGHT_UNAVAILABLE", "detail": source}
    q = latest_quote()
    if q is None:
        return {"error": "NO_QUOTE"}
    sig = signal_from_review(review)
    now = _now_ms()
    adb = AuditDB(audit_path) if audit_path else AuditDB()
    p = PROP.build_proposal(sig, account, symbol, q, risk_pct=risk_pct, manual_entry=_f(manual_entry),
                            token_scope=account.trade_scope, now_ms=now,
                            fx_quote_to_account=FX_USD_TO_GBP_APPROX, audit=adb)
    _PROPOSALS[p.proposal_id] = p
    pv = dict(p.preview)
    pv.update({"proposal_id": p.proposal_id, "status": p.status, "preflight_source": source,
               "fx_note": f"USD->GBP approx {FX_USD_TO_GBP_APPROX} (reconcile before any real order)",
               "token_scope": account.trade_scope,
               "NOTE": "DRY-RUN PREVIEW — NO ORDER SENT. Firewall blocks a real send (view-only token)."})
    return pv


def arm(proposal_id, audit_path=None):
    p = _PROPOSALS.get(proposal_id)
    if not p:
        return {"armed": False, "reason": "UNKNOWN_PROPOSAL"}
    return PROP.arm(p, AuditDB(audit_path) if audit_path else AuditDB())


def approve(proposal_id, audit_path=None):
    p = _PROPOSALS.get(proposal_id)
    if not p:
        return {"result": "UNKNOWN_PROPOSAL", "order_sent": False, "reason": "NO_ORDER_SENT"}
    return PROP.dry_run_approve(p, now_ms=_now_ms(), audit=AuditDB(audit_path) if audit_path else AuditDB())


# ---------------------------------------------------------------- TRADE_UPDATE management (dry-run)
def _cache_raw():
    c = json.load(open(PREFLIGHT_CACHE, encoding="utf-8"))
    s = c["symbol_raw_ctrader"]
    return c, s


def _positions_from_payload(payload):
    """Operator-supplied / reconciled broker positions (list of dicts) -> BrokerPosition objects.
    A LIVE reconcile (read-only ProtoOAReconcileReq) will populate this once a demo position exists;
    until then the match gate correctly reports NO_MATCH."""
    out = []
    for p in (payload.get("positions") or []):
        out.append(BrokerPosition(p.get("position_id"), p.get("label", ""), "XAUUSD",
                                  p.get("direction"), p.get("volume_units"), p.get("price"),
                                  p.get("stop_loss"), p.get("take_profit"), p.get("open_time_ms")))
    return out


def _mock_positions(payload):
    """A clearly-labelled mock position for UI demonstration only (no real position exists yet)."""
    if not payload.get("mock_ui"):
        return _positions_from_payload(payload), False
    p = payload.get("mock_position") or {"position_id": 88449001, "label": "MOCK_POSITION_FOR_DRY_RUN_UI_ONLY",
                                         "direction": "SELL", "volume_units": 300, "price": 4124.95,
                                         "stop_loss": 4140.0}
    return [BrokerPosition(p["position_id"], p["label"], "XAUUSD", p["direction"], p["volume_units"],
                           p["price"], p.get("stop_loss"), p.get("take_profit"), None)], True


def build_update_preview(review, payload=None, *, audit_path=None):
    payload = payload or {}
    account, symbol, source = load_account_and_symbol()
    if account is None:
        return {"error": "PREFLIGHT_UNAVAILABLE"}
    q = latest_quote()
    if q is None:
        return {"error": "NO_QUOTE"}
    c, s = _cache_raw()
    positions, mock_ui = _mock_positions(payload)
    text = payload.get("update_text") or (review.get("visible_result_fields") or {}).get("update", "") or "move SL to breakeven"
    ocr_probe = __import__("update_parser").parse_ocr_update(text)
    if ocr_probe["provider_leg_candidate"] or ("more profit" in text.lower()):
        # exact OCR 'take more profit' route
        r = UPL.build_ocr_update_plan(
            signal_id=review.get("intake_id"), source_class=review.get("intake_class"),
            confirmed=review.get("explicit_confirmation_state") == "CONFIRMED",
            provider_verified=(review.get("provider") or {}).get("verification_state") == "PROVIDER_VERIFIED",
            ocr_text=text, update_ts_ms=_ms(review.get("review_created_at_utc")), account=account,
            account_type=c["account"].get("account_type", "HEDGED"), symbol_digits=s["digits"], pip_position=s.get("pip_position", 1),
            positions=positions, quote=q, now_ms=_now_ms(), units_per_lot=float(s["lot_size"]),
            lot_size_raw=float(s["lot_size"]), min_volume_units=float(s["min_volume"]),
            step_volume_units=float(s["step_volume"]), fx=FX_USD_TO_GBP_APPROX, mock_ui=mock_ui,
            audit=AuditDB(audit_path) if audit_path else AuditDB())
        card = dict(r["card"]); card.update({"plan_id": r["plan_id"], "status": r["status"], "preflight_source": source})
        return card
    r = UPL.build_update_plan(
        signal_id=review.get("intake_id"), source_class=review.get("intake_class"),
        confirmed=review.get("explicit_confirmation_state") == "CONFIRMED",
        provider_verified=(review.get("provider") or {}).get("verification_state") == "PROVIDER_VERIFIED",
        update_text=payload.get("update_text") or (review.get("visible_result_fields") or {}).get("update", "") or "move SL to breakeven",
        update_ts_ms=_ms(review.get("review_created_at_utc")), account=account,
        account_type=c["account"].get("account_type", "HEDGED"), symbol_digits=s["digits"], point=10 ** (-s["digits"]),
        min_stop_distance_points=(s.get("min_stop_distance") or 50.0),
        positions=positions, quote=q, now_ms=_now_ms(),
        units_per_lot=float(s["lot_size"]), min_volume_units=float(s["min_volume"]),
        step_volume_units=float(s["step_volume"]), fx=FX_USD_TO_GBP_APPROX,
        requested_fraction=payload.get("requested_fraction"),
        audit=AuditDB(audit_path) if audit_path else AuditDB())
    card = dict(r["card"]); card.update({"plan_id": r["plan_id"], "status": r["status"], "preflight_source": source})
    return card


def submission_readiness():
    """Read-only submission-readiness (no secrets). Order sending stays disabled this phase."""
    c, s = _cache_raw()
    scope = c["account"].get("token_scope")
    blocking = []
    if not DECFG.ORDER_SENDING_ENABLED:
        blocking.append("ORDER_SENDING_ENABLED_FALSE")
    if scope != DECFG.REQUIRED_PERMISSION_SCOPE:
        blocking.append("TOKEN_NOT_SCOPE_TRADE(view-only)")
    scope_trade = scope == DECFG.REQUIRED_PERMISSION_SCOPE
    return {"ORDER_SENDING_ENABLED": DECFG.ORDER_SENDING_ENABLED,
            "demo_endpoint": DECFG.DEMO_ENDPOINT_HOST + ":" + str(DECFG.DEMO_ENDPOINT_PORT),
            "no_live_fallback": True,
            "account_id": c["account"].get("account_id"), "is_live": c["account"].get("is_live"),
            "currency": c["account"].get("currency"), "balance": c["account"].get("balance"),
            "demo_token_scope": ("SCOPE_TRADE" if scope_trade else "SCOPE_VIEW(view-only)"),
            "token_scope": scope, "permission_scope_trade": scope_trade,
            "send_gate": "DISABLED", "one_shot_permit": "NOT_ISSUED", "activation_lease": "NOT_ISSUED",
            "ready_for_fresh_signal": ("YES" if scope_trade and not blocking else "NO"),
            "ready_state": DECFG.READY_STATE, "ready_active": False, "blocking": blocking,
            "note": "READY_FOR_FIRST_CONTROLLED_DEMO_ORDER does NOT activate automatically; approval "
                    "still ends DRY_RUN_APPROVED / ORDER_SENDING_DISABLED / NO_ORDER_SENT"}


def management_readiness():
    """Read-only DEMO MANAGEMENT readiness (no secrets). The management gate is a SEPARATE lock and
    stays disabled this phase; no position is matched, no permit/lease is issued."""
    c, s = _cache_raw()
    scope = c["account"].get("token_scope")
    scope_trade = scope == DECFG.REQUIRED_PERMISSION_SCOPE
    blocking = []
    if not DECFG.ORDER_MANAGEMENT_ENABLED:
        blocking.append("ORDER_MANAGEMENT_ENABLED_FALSE")
    if not scope_trade:
        blocking.append("TOKEN_NOT_SCOPE_TRADE(view-only)")
    return {"demo_management_token": ("SCOPE_TRADE" if scope_trade else "SCOPE_VIEW(view-only)"),
            "account_id": c["account"].get("account_id"), "is_live": c["account"].get("is_live"),
            "management_gate": "DISABLED", "matched_position": "NONE",
            "management_permit": "NOT_ISSUED", "management_lease": "NOT_ISSUED",
            "ORDER_MANAGEMENT_ENABLED": DECFG.ORDER_MANAGEMENT_ENABLED,
            "ORDER_SENDING_ENABLED": DECFG.ORDER_SENDING_ENABLED,
            "demo_endpoint": DECFG.DEMO_ENDPOINT_HOST + ":" + str(DECFG.DEMO_ENDPOINT_PORT),
            "blocking": blocking,
            "note": "Entry-order and management gates are INDEPENDENT. Approval terminates as "
                    "UPDATE_PLAN_DRY_RUN_APPROVED / ORDER_MANAGEMENT_DISABLED / NO_BROKER_ACTION_SENT."}


def arm_update(plan_id, audit_path=None):
    return UPL.arm_plan(plan_id, AuditDB(audit_path) if audit_path else AuditDB())


def approve_update(plan_id, audit_path=None):
    return UPL.dry_run_approve(plan_id, now_ms=_now_ms(), audit=AuditDB(audit_path) if audit_path else AuditDB())
