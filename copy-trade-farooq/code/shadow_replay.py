"""
shadow_replay.py — SHADOW MODE Phase 1b, the tick-path replay engine.

Given a signal's direction, reference entry, stop and targets, and an entry time, it
replays the INDEPENDENT Phase 1a tick path and returns where the trade would have
filled and exited — with strict executable-fill discipline and honest handling of
the cases where the data cannot answer.

Discipline (from the spec, sections 9/12):
  * LONG  enters on ASK, exits a target on BID, stop fills on BID (− adverse slippage).
  * SHORT enters on BID, exits a target on ASK, stop fills on ASK (+ adverse slippage).
  * Ticks already carry bid AND ask, so spread is taken FROM the tick, never added twice.
  * Slippage only ever WORSENS a fill.
  * Use the first valid tick AT or AFTER the effective time. If it is further than the
    quote-gap limit -> NO_EXECUTABLE_QUOTE (we do not guess a fill).
  * NO interpolation, NO stale forward-fill.
  * First chronological crossing decides the event. Genuine tick data is a single
    price per instant, so ordering is normally UNAMBIGUOUS; only when an unobserved
    gap spans BOTH stop and target do we return PATH_AMBIGUOUS with pessimistic and
    optimistic bounds.

Risk unit: R is always measured against the REFERENCE risk |ref_entry − stop|, held
constant across every ledger and decomposition step, so friction shows up honestly
in the numerator.

PAPER mode, read-only. No R interpretation here — just the mechanical replay.
"""

import bisect
from datetime import timedelta
from decimal import Decimal

import dukascopy_adapter as adapter
import price_cache
import shadow_config as cfg

# path_status values
RESOLVED = "RESOLVED"
PATH_AMBIGUOUS = "PATH_AMBIGUOUS"
NO_EXECUTABLE_QUOTE = "NO_EXECUTABLE_QUOTE"
MISSED_ENTRY = "MISSED_ENTRY"
OPEN_AT_BOUNDARY = "OPEN_AT_BOUNDARY"
CLOSED_MARKET = "CLOSED_MARKET"


def dir_sign(direction):
    d = (direction or "").upper()
    if d in ("LONG", "BUY"):
        return 1
    if d in ("SHORT", "SELL"):
        return -1
    raise ValueError(f"unknown direction {direction!r}")


# ----------------------------------------------------------------------------
# Tick path across hours (reuses the immutable Phase 1a cache)
# ----------------------------------------------------------------------------
def ticks_in_range(start_dt, end_dt, instrument=adapter.INSTRUMENT):
    """All cached ticks with start_dt <= dt <= end_dt, in order, spanning hours.

    Returns (ticks, hours_used) where hours_used lists (hour_iso, sha, status) so a
    result can name the exact immutable price files it was built from.
    """
    ticks = []
    hours_used = []
    cur = start_dt.replace(minute=0, second=0, microsecond=0)
    end_hour = end_dt.replace(minute=0, second=0, microsecond=0)
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)
    while cur <= end_hour:
        hr = price_cache.get_hour(cur, instrument=instrument)
        meta = price_cache._cached_meta(adapter._floor_hour(cur), instrument) or {}
        hours_used.append((cur.isoformat(), meta.get("sha256_raw"), hr.status))
        for t in hr.ticks:
            if start_ms <= t.epoch_ms <= end_ms:
                ticks.append(t)
        cur += timedelta(hours=1)
    return ticks, hours_used


def first_tick_at_or_after(ticks, when_ms):
    """Index of the first tick with epoch_ms >= when_ms, or None."""
    keys = [t.epoch_ms for t in ticks]
    i = bisect.bisect_left(keys, when_ms)
    return i if i < len(ticks) else None


# ----------------------------------------------------------------------------
# Executable price helpers
# ----------------------------------------------------------------------------
def _entry_price(tick, sign, use_bidask, slippage):
    """Market entry price at a tick. LONG pays ASK, SHORT pays BID; slippage worsens."""
    if not use_bidask:
        mid = (tick.bid + tick.ask) / 2
        return mid + sign * slippage          # worsen: long pays up, short sold lower
    if sign > 0:
        return tick.ask + slippage            # long buys at ask, slippage worse (higher)
    return tick.bid - slippage                # short sells at bid, slippage worse (lower)


def _target_hit(tick, sign, target, use_bidask):
    """Has price reached `target` on the EXIT side? LONG exits on bid, SHORT on ask."""
    if use_bidask:
        px = tick.bid if sign > 0 else tick.ask
    else:
        px = (tick.bid + tick.ask) / 2
    return px >= target if sign > 0 else px <= target


def _stop_hit(tick, sign, stop, use_bidask):
    """Has price reached the STOP on the exit side?"""
    if use_bidask:
        px = tick.bid if sign > 0 else tick.ask
    else:
        px = (tick.bid + tick.ask) / 2
    return px <= stop if sign > 0 else px >= stop


def _exit_fill_price(tick, sign, level, is_stop, use_bidask, slippage):
    """The price a target/stop exit actually fills at. Targets fill at the level
    (limit); stops are market -> add adverse slippage on the exit side."""
    if not is_stop:
        return level                          # target = limit exit at the level
    # stop: market exit, slippage worsens. LONG sells lower, SHORT buys higher.
    return level - slippage if sign > 0 else level + slippage


# ----------------------------------------------------------------------------
# The replay
# ----------------------------------------------------------------------------
# Process-level memo of replay results within a run. simulate() is called ~1000+
# times with heavy overlap (decomposition steps duplicate C scenarios; the no-delay
# steps repeat across delays), so identical parameter sets are computed once.
_SIM_MEMO = {}


def clear_memo():
    _SIM_MEMO.clear()


def simulate(direction, ref_entry, stop, targets, entry_time, boundary,
             *, entry_mode, use_bidask, slippage, instrument=adapter.INSTRUMENT,
             gap_limit_ms=cfg.QUOTE_GAP_LIMIT_MS, primary_bound=cfg.PRIMARY_PATH_BOUND,
             managed_exit_time=None):
    """Memoizing wrapper around the replay (see _simulate_impl)."""
    key = (direction, str(ref_entry), str(stop), tuple(str(t) for t in targets),
           entry_time.isoformat(), boundary.isoformat(), entry_mode, use_bidask,
           str(slippage), instrument, gap_limit_ms, primary_bound,
           managed_exit_time.isoformat() if managed_exit_time else None)
    if key not in _SIM_MEMO:
        _SIM_MEMO[key] = _simulate_impl(
            direction, ref_entry, stop, targets, entry_time, boundary,
            entry_mode=entry_mode, use_bidask=use_bidask, slippage=slippage,
            instrument=instrument, gap_limit_ms=gap_limit_ms, primary_bound=primary_bound,
            managed_exit_time=managed_exit_time)
    return _SIM_MEMO[key]


def _simulate_impl(direction, ref_entry, stop, targets, entry_time, boundary,
                   *, entry_mode, use_bidask, slippage, instrument=adapter.INSTRUMENT,
                   gap_limit_ms=cfg.QUOTE_GAP_LIMIT_MS, primary_bound=cfg.PRIMARY_PATH_BOUND,
                   managed_exit_time=None):
    """Replay one trade.

    managed_exit_time (optional): for managed_profit / no-target signals the exit is
    the provider's management close, not a fixed target. When set, the path is walked
    with STOP PROTECTION only — if the stop is hit before managed_exit_time the trade
    is stopped (a follower would have been stopped before the managed close); otherwise
    it exits at the executable price at managed_exit_time. Targets are NOT auto-taken
    in this mode (the provider was managing, not using fixed TPs).

    entry_mode:
      "reference_when_reached" — Ledger-B style: the limit fills at `ref_entry` the
            moment price first reaches the zone edge at/after entry_time (no entry
            slippage; that is the price you set). MISSED if never reached by boundary.
      "market_on_acting"       — Ledger-C style: a market fill at the first tick
            at/after entry_time, at executable bid/ask (+ slippage).

    Returns a dict with: path_status, entry_price, entry_dt, exit_price, exit_kind
    ('target'/'stop'/'open'/none), r, r_low, r_high, r_is_known, quote_gap_ms,
    furthest_target_idx, hours_used.
    """
    sign = dir_sign(direction)
    ref_entry = Decimal(str(ref_entry))
    stop = Decimal(str(stop))
    slippage = Decimal(str(slippage))
    risk = abs(ref_entry - stop)
    targets = [Decimal(str(t)) for t in targets if str(t).strip() not in ("", "None")]

    out = {"path_status": None, "entry_price": None, "entry_dt": None,
           "exit_price": None, "exit_kind": None, "r": None, "r_low": None,
           "r_high": None, "r_is_known": False, "quote_gap_ms": None,
           "furthest_target_idx": None, "hours_used": [], "risk": str(risk),
           "ref_entry": str(ref_entry), "stop": str(stop),
           "targets": [str(t) for t in targets], "ambiguous": False}

    if risk <= 0:
        out["path_status"] = "INVALID_STOP"
        return out

    ticks, hours_used = ticks_in_range(entry_time, boundary, instrument)
    out["hours_used"] = hours_used
    if not ticks:
        # No ticks anywhere in the window: closed market or missing data.
        out["path_status"] = CLOSED_MARKET
        return out

    entry_ms = int(entry_time.timestamp() * 1000)

    # ---- ENTRY ----
    if entry_mode == "market_on_acting":
        idx = first_tick_at_or_after(ticks, entry_ms)
        if idx is None:
            out["path_status"] = NO_EXECUTABLE_QUOTE
            return out
        gap = ticks[idx].epoch_ms - entry_ms
        out["quote_gap_ms"] = gap
        if gap > gap_limit_ms:
            out["path_status"] = NO_EXECUTABLE_QUOTE
            return out
        entry_price = _entry_price(ticks[idx], sign, use_bidask, slippage)
        entry_idx = idx
    elif entry_mode == "reference_when_reached":
        # limit fills when price first reaches the zone edge at/after entry_time
        entry_idx = None
        start = first_tick_at_or_after(ticks, entry_ms)
        if start is not None:
            for j in range(start, len(ticks)):
                # fill when the entry-side price reaches ref_entry:
                # LONG buys at ask <= ref_entry; SHORT sells at bid >= ref_entry.
                px = ticks[j].ask if (sign > 0 and use_bidask) else (
                     ticks[j].bid if (sign < 0 and use_bidask) else
                     (ticks[j].bid + ticks[j].ask) / 2)
                reached = px <= ref_entry if sign > 0 else px >= ref_entry
                if reached:
                    entry_idx = j
                    break
        if entry_idx is None:
            out["path_status"] = MISSED_ENTRY
            return out
        entry_price = ref_entry
        out["quote_gap_ms"] = ticks[entry_idx].epoch_ms - entry_ms
    else:
        raise ValueError(f"unknown entry_mode {entry_mode!r}")

    out["entry_price"] = str(entry_price)
    out["entry_dt"] = ticks[entry_idx].dt.isoformat()

    def r_of(exit_price):
        return (Decimal(sign) * (Decimal(str(exit_price)) - entry_price) / risk)

    # ---- MANAGED EXIT: stop-protected hold to the management close time ----
    if managed_exit_time is not None:
        exit_ms = int(managed_exit_time.timestamp() * 1000)
        for j in range(entry_idx + 1, len(ticks)):
            tk = ticks[j]
            if _stop_hit(tk, sign, stop, use_bidask):
                stop_fill = _exit_fill_price(tk, sign, stop, True, use_bidask, slippage)
                out["path_status"] = RESOLVED
                out["exit_kind"] = "stop_before_managed_close"
                out["exit_price"] = str(stop_fill)
                r = r_of(stop_fill)
                out["r"], out["r_low"], out["r_high"] = str(r), str(r), str(r)
                out["r_is_known"] = True
                return out
            if tk.epoch_ms >= exit_ms:
                # exit at the executable price at the management close (spread + slippage)
                exit_px = (tk.bid - slippage) if sign > 0 else (tk.ask + slippage)
                out["path_status"] = RESOLVED
                out["exit_kind"] = "managed_close"
                out["exit_price"] = str(exit_px)
                out["managed_exit_dt"] = tk.dt.isoformat()
                r = r_of(exit_px)
                out["r"], out["r_low"], out["r_high"] = str(r), str(r), str(r)
                out["r_is_known"] = True
                return out
        # management close is beyond the available ticks/boundary
        out["path_status"] = OPEN_AT_BOUNDARY
        last_mid = (ticks[-1].bid + ticks[-1].ask) / 2
        out["detail_mark_to_boundary_r"] = str(r_of(last_mid))
        return out

    # ---- PATH: first chronological crossing, furthest target before stop ----
    furthest_idx = -1
    prev_mid = (ticks[entry_idx].bid + ticks[entry_idx].ask) / 2
    for j in range(entry_idx + 1, len(ticks)):
        tk = ticks[j]
        this_mid = (tk.bid + tk.ask) / 2
        stop_now = _stop_hit(tk, sign, stop, use_bidask)
        # advance furthest target reached
        hit_any_target = False
        for ti in range(furthest_idx + 1, len(targets)):
            if _target_hit(tk, sign, targets[ti], use_bidask):
                furthest_idx = ti
                hit_any_target = True
            else:
                break

        if stop_now:
            # Ambiguity: did an as-yet-unreached target also fall inside the gap
            # [prev_mid, this_mid] that we could not observe between ticks?
            nxt_t = furthest_idx + 1
            target_in_gap = (nxt_t < len(targets) and
                             _between(prev_mid, this_mid, targets[nxt_t]))
            stop_fill = _exit_fill_price(tk, sign, stop, True, use_bidask, slippage)
            if furthest_idx >= 0:
                # already banked at least one target before this stop
                out["path_status"] = RESOLVED
                out["exit_kind"] = "target"
                out["exit_price"] = str(targets[furthest_idx])
                out["furthest_target_idx"] = furthest_idx
                r = r_of(targets[furthest_idx])
                out["r"], out["r_low"], out["r_high"] = str(r), str(r), str(r)
                out["r_is_known"] = True
                return out
            if target_in_gap:
                # stop and the next target both inside one unobserved gap -> ambiguous
                r_stop = r_of(stop_fill)
                r_tgt = r_of(targets[nxt_t])
                lo, hi = sorted([r_stop, r_tgt])
                out["path_status"] = PATH_AMBIGUOUS
                out["ambiguous"] = True
                out["exit_kind"] = "ambiguous"
                out["r_low"], out["r_high"] = str(lo), str(hi)
                out["r"] = str(lo if primary_bound == "pessimistic" else hi)
                out["r_is_known"] = True
                out["exit_price"] = str(stop_fill if primary_bound == "pessimistic"
                                        else targets[nxt_t])
                return out
            # clean stop loss
            out["path_status"] = RESOLVED
            out["exit_kind"] = "stop"
            out["exit_price"] = str(stop_fill)
            r = r_of(stop_fill)
            out["r"], out["r_low"], out["r_high"] = str(r), str(r), str(r)
            out["r_is_known"] = True
            return out

        if furthest_idx == len(targets) - 1 and targets:
            # furthest defined target reached, no stop yet -> exit at furthest target
            out["path_status"] = RESOLVED
            out["exit_kind"] = "target"
            out["exit_price"] = str(targets[furthest_idx])
            out["furthest_target_idx"] = furthest_idx
            r = r_of(targets[furthest_idx])
            out["r"], out["r_low"], out["r_high"] = str(r), str(r), str(r)
            out["r_is_known"] = True
            return out
        prev_mid = this_mid

    # ---- reached boundary without a clean stop/target resolution ----
    if furthest_idx >= 0:
        out["path_status"] = RESOLVED
        out["exit_kind"] = "target"
        out["exit_price"] = str(targets[furthest_idx])
        out["furthest_target_idx"] = furthest_idx
        r = r_of(targets[furthest_idx])
        out["r"], out["r_low"], out["r_high"] = str(r), str(r), str(r)
        out["r_is_known"] = True
        return out
    # open at boundary: do NOT fabricate an exit; report unquantifiable
    out["path_status"] = OPEN_AT_BOUNDARY
    last_mid = (ticks[-1].bid + ticks[-1].ask) / 2
    out["detail_mark_to_boundary_r"] = str(r_of(last_mid))   # context only, not credited
    return out


def _between(a, b, x):
    """Is x within the closed interval spanned by a and b (either order)?"""
    lo, hi = (a, b) if a <= b else (b, a)
    return lo <= x <= hi


def ambiguity_bounds(direction, entry_price, stop, target, slippage="0"):
    """Pessimistic and optimistic R bounds for a COARSE bar (e.g. a 5s candle, or a
    minute) that touched BOTH the stop and the target with unknown order.

    With genuine tick data this never arises (each tick is a single price, and the
    exit-side convention can't satisfy stop and target at one tick) — this is the
    primitive for the candle/coarse-data fallback the brief calls out. The PRIMARY
    aggregate takes the pessimistic bound; the report always shows both.

    Returns (r_low, r_high) with r_low <= r_high, both measured against the reference
    risk |entry − stop|.
    """
    sign = dir_sign(direction)
    entry_price = Decimal(str(entry_price))
    stop = Decimal(str(stop))
    target = Decimal(str(target))
    slip = Decimal(str(slippage))
    risk = abs(entry_price - stop)
    if risk == 0:
        return None, None
    stop_fill = (stop - slip) if sign > 0 else (stop + slip)   # stop is market: worse
    r_stop = Decimal(sign) * (stop_fill - entry_price) / risk
    r_target = Decimal(sign) * (target - entry_price) / risk
    return (min(r_stop, r_target), max(r_stop, r_target))
