"""
shadow_ledgers.py — SHADOW MODE Phase 1b, the three ledgers (kept strictly separate).

  A  PROVIDER-REPORTED R   — read from the signed-off archive projection. Never recomputed.
  B  INDEPENDENT THEORETICAL R — advertised entry + original stop/targets replayed on the
       Phase 1a independent price path, NO follower delay, NO spread, NO slippage. "Did
       the market support the claim?"
  C  SHADOW-EXECUTABLE R   — realistic fill at posted+delay on executable bid/ask, with
       adverse slippage. One result per (delay, slippage) scenario, all labelled
       RECONSTRUCTED_DELAY_SCENARIO (T-C historical — never "exact executable").

Category-honest exit routing:
  * managed_profit_confirmed / manual_loss / breakeven, OR any signal with NO parsed
    targets -> exit at the MANAGEMENT message time (stop-protected), NOT a fixed target,
    and NOT by copying the provider's stated pips.
  * target_hit / profit_confirmed_r_unknown / original_stop_loss WITH targets ->
    chronological target/stop replay (verify the level was actually reachable).
  * profit_confirmed_r_unknown stays UNQUANTIFIABLE unless the independent data resolves
    it; an unknown is never silently converted into a target hit.

PAPER mode, read-only.
"""

from datetime import timedelta
from decimal import Decimal

import shadow_config as cfg
import shadow_replay as replay

# exit routing
TARGET_REPLAY = "target_replay"
MANAGED = "managed"

# Categories whose realistic exit is a stop-protected MANAGEMENT close, not a fixed
# target: the provider managed/closed these by hand (managed profit, a manual loss, a
# breakeven move) or claimed profit with no quantity (r_unknown — never a clean TP).
# A clean target_hit or an original stop loss instead gets a chronological replay.
_MANAGED_CATS = {"managed_profit_confirmed", "manual_loss", "breakeven",
                 "profit_confirmed_r_unknown"}


def exit_plan(sig):
    """Return (method, managed_time). MANAGED uses the management-time exit (stop
    protected); TARGET_REPLAY walks the path to targets/stop. No targets -> MANAGED
    (the only way to quantify), since there is no target level to replay to."""
    cat = sig.get("category") or ""
    has_targets = bool(sig.get("targets"))
    if cat in _MANAGED_CATS or not has_targets:
        return MANAGED, sig.get("mgmt_time")
    return TARGET_REPLAY, None


def _grade_from_gap(gap_ms):
    if gap_ms is None:
        return "P-U"
    if gap_ms <= 1000:
        return "P-A"
    if gap_ms <= 5000:
        return "P-B"
    return "P-C"


# ----------------------------------------------------------------------------
# Ledger A — provider reported (read only)
# ----------------------------------------------------------------------------
def ledger_A(sig):
    return {
        "ledger": "A_provider",
        "provenance": "PROVIDER",
        "r_value": sig.get("provider_r"),
        "r_is_known": bool(sig.get("provider_r_is_known")),
        "path_status": "PROVIDER_REPORTED",
        "outcome_category": sig.get("category"),
        "timestamp_grade": "T-C",
    }


# ----------------------------------------------------------------------------
# Ledger B — independent theoretical (no delay, mid, no slippage)
# ----------------------------------------------------------------------------
def ledger_B(sig):
    if sig.get("instrument") is None:
        return _no_feed("B_theoretical", "THEORETICAL_NO_DELAY", sig)
    method, mgmt = exit_plan(sig)
    common = dict(direction=sig["direction"], ref_entry=sig["ref_entry"], stop=sig["stop"],
                  entry_time=sig["posted_at"], boundary=sig["boundary"],
                  instrument=sig["instrument"], entry_mode="reference_when_reached",
                  use_bidask=False, slippage="0")
    if method == MANAGED:
        if mgmt is None:
            return _unquantifiable("B_theoretical", "THEORETICAL_NO_DELAY", sig,
                                   "managed/no-target signal with no management time")
        res = replay.simulate(targets=[], managed_exit_time=mgmt, **common)
    else:
        res = replay.simulate(targets=sig["targets"], **common)
    return _wrap(res, "B_theoretical", "THEORETICAL_NO_DELAY", sig, method)


# ----------------------------------------------------------------------------
# Ledger C — shadow executable (per delay + slippage scenario)
# ----------------------------------------------------------------------------
def ledger_C(sig, delay_sec, slippage):
    if sig.get("instrument") is None:
        d = _no_feed("C_shadow", cfg.RECONSTRUCTED_DELAY_SCENARIO, sig)
        d["delay_sec"], d["slippage_usd"] = delay_sec, str(slippage)
        return d
    method, mgmt = exit_plan(sig)
    entry_time = sig["posted_at"] + timedelta(seconds=delay_sec)
    common = dict(direction=sig["direction"], ref_entry=sig["ref_entry"], stop=sig["stop"],
                  entry_time=entry_time, boundary=sig["boundary"], instrument=sig["instrument"],
                  entry_mode="market_on_acting", use_bidask=True, slippage=str(slippage))
    if method == MANAGED:
        if mgmt is None:
            d = _unquantifiable("C_shadow", cfg.RECONSTRUCTED_DELAY_SCENARIO, sig,
                                "managed/no-target signal with no management time")
            d["delay_sec"], d["slippage_usd"] = delay_sec, str(slippage)
            return d
        mgmt_delayed = mgmt + timedelta(seconds=delay_sec)   # follower also delayed on the close
        res = replay.simulate(targets=[], managed_exit_time=mgmt_delayed, **common)
    else:
        res = replay.simulate(targets=sig["targets"], **common)
    d = _wrap(res, "C_shadow", cfg.RECONSTRUCTED_DELAY_SCENARIO, sig, method)
    d["delay_sec"], d["slippage_usd"] = delay_sec, str(slippage)
    return d


# ----------------------------------------------------------------------------
# Leakage decomposition for one (delay, slippage) — fixed documented order
# ----------------------------------------------------------------------------
def decomposition(sig, delay_sec, slippage):
    """R at each friction step (same risk unit). Returns {step_name: r_or_None}.

    Steps with no historical stamp (parser/approval) intentionally equal the prior
    step -> their attributed leakage is 0, honestly (we have no such timing for T-C).
    """
    if sig.get("instrument") is None:
        return {s: None for s in cfg.LEAKAGE_DECOMPOSITION_ORDER}
    method, mgmt = exit_plan(sig)
    posted = sig["posted_at"]

    def run(entry_mode, use_bidask, slip, entry_time, mgmt_time):
        base = dict(direction=sig["direction"], ref_entry=sig["ref_entry"], stop=sig["stop"],
                    entry_time=entry_time, boundary=sig["boundary"], instrument=sig["instrument"],
                    entry_mode=entry_mode, use_bidask=use_bidask, slippage=str(slip))
        if method == MANAGED:
            if mgmt is None:
                return None
            return replay.simulate(targets=[], managed_exit_time=mgmt_time, **base)
        return replay.simulate(targets=sig["targets"], **base)

    def r(res):
        return None if res is None or res.get("r") is None else Decimal(res["r"])

    entry_d = posted + timedelta(seconds=delay_sec)
    steps = {}
    steps["reference_entry_no_friction"] = r(run("reference_when_reached", False, "0", posted, mgmt))
    steps["independent_bid_ask_no_delay"] = r(run("reference_when_reached", True, "0", posted, mgmt))
    steps["receipt_delay"] = r(run("market_on_acting", True, "0", entry_d,
                                   (mgmt + timedelta(seconds=delay_sec)) if mgmt else None))
    steps["parser_delay"] = steps["receipt_delay"]      # +0 historical
    steps["approval_delay"] = steps["parser_delay"]     # +0 historical
    steps["slippage"] = r(run("market_on_acting", True, str(slippage), entry_d,
                              (mgmt + timedelta(seconds=delay_sec)) if mgmt else None))
    steps["management_delay"] = steps["slippage"]       # management timing already in managed exit
    return steps


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def _wrap(res, ledger, provenance, sig, method):
    return {
        "ledger": ledger,
        "provenance": provenance,
        "r_value": res.get("r"),
        "r_is_known": bool(res.get("r_is_known")),
        "r_low": res.get("r_low"),
        "r_high": res.get("r_high"),
        "path_status": res.get("path_status"),
        "exit_kind": res.get("exit_kind"),
        "quote_grade": _grade_from_gap(res.get("quote_gap_ms")),
        "timestamp_grade": "T-C",
        "outcome_category": sig.get("category"),
        "exit_method": method,
        "detail": res,
    }


def _no_feed(ledger, provenance, sig):
    return {"ledger": ledger, "provenance": provenance, "r_value": None,
            "r_is_known": False, "path_status": "NO_VALIDATED_FEED",
            "outcome_category": sig.get("category"), "timestamp_grade": "T-C",
            "detail": {"note": f"no validated price feed for {sig.get('asset')}"}}


def _unquantifiable(ledger, provenance, sig, why):
    return {"ledger": ledger, "provenance": provenance, "r_value": None,
            "r_is_known": False, "path_status": "UNQUANTIFIABLE",
            "outcome_category": sig.get("category"), "timestamp_grade": "T-C",
            "detail": {"note": why}}
