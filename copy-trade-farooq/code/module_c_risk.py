"""
module_c_risk.py — the Risk Calculator (final form).

THE ONE RULE: capital at risk per trade NEVER exceeds 1% of the pot.
Everything in this file exists to enforce that rule and to refuse, loudly,
anything that would break it.

All money/size math uses Decimal — never float.

Run this file on its own to see the five real test signals sized and printed:

    python module_c_risk.py
"""

from decimal import Decimal, ROUND_DOWN, getcontext

import config
import asset_classes
from models import Signal, Ticket

# Plenty of precision for tiny prices like PEPE without surprises.
getcontext().prec = 50

_THIRD = Decimal(1) / Decimal(3)


class RiskError(Exception):
    """
    Raised when a signal cannot be sized safely.
    The message is written to be shown directly to the operator.
    """


# ----------------------------------------------------------------------------
# Asset routing — config-driven (see config.ASSET_CLASSES)
# ----------------------------------------------------------------------------
def _D(x) -> Decimal:
    return Decimal(str(x))


def _ticker_pair(obj):
    """(ticker, pair) from a Signal / dict / bare ticker string."""
    if isinstance(obj, str):
        return obj, obj
    if isinstance(obj, dict):
        return obj.get("ticker", ""), (obj.get("pair", "") or obj.get("ticker", ""))
    return getattr(obj, "ticker", ""), (getattr(obj, "pair", "") or getattr(obj, "ticker", ""))


def resolve_asset_config(ticker_or_signal) -> dict:
    """
    Resolve how to treat an instrument, from the per-asset-class registry in
    config.ASSET_CLASSES. Accepts a Signal, a dict, or a bare ticker string.

    Returns a dict:
        fine_class           GOLD / SILVER / FOREX / CRYPTO / OIL / ... / UNKNOWN
        asset_class          ledger label written to the log (METAL/CRYPTO/FOREX/…)
        calibrated           bool — is there trusted sizing logic for this class?
        sizing               name of the sizing strategy (None if not calibrated)
        params               strategy params (contract multiplier / pip specs / lots)
        slippage             Decimal — per-side price slippage estimate
        verified             bool — False means the spec is a PLACEHOLDER, confirm live
        broker_note          spec-confirmation reminder (metals/forex)
        flags                extra honesty flags (e.g. crypto fees)
        quote_currency       FOREX quote currency (drives pip value), else ""

    Back-compat: callers that only read ["asset_class"] (review.py) still get the
    METAL/CRYPTO/FOREX ledger vocabulary they expect.
    """
    fc = asset_classes.classify(ticker_or_signal)
    base = asset_classes.spec(fc)
    ticker, pair = _ticker_pair(ticker_or_signal)
    return {
        "fine_class": fc,
        "asset_class": asset_classes.ledger_class(fc),
        "calibrated": asset_classes.is_calibrated(fc),
        "sizing": base.get("sizing"),
        "params": dict(base.get("params", {})),
        "slippage": asset_classes.slippage(fc),
        "verified": bool(base.get("verified", False)),
        "broker_note": base.get("broker_note", ""),
        "flags": list(base.get("flags", [])),
        "quote_currency": asset_classes.quote_currency(ticker, pair),
    }


# ----------------------------------------------------------------------------
# Sizing strategies — one per "how is size calculated" in config.ASSET_CLASSES.
# Each takes the resolved spec plus the common sizing inputs and returns the
# size-specific outputs. Adding a class that reuses one of these is config-only;
# a genuinely new sizing maths is one new function registered below.
#
# Common inputs:
#   price_risk    |entry - stop| in price terms (already slippage-adjusted entry)
#   dollar_risk   budgeted cash at risk = pot * risk_pct (account currency)
#   sizing_entry  the entry the size is calculated from (after slippage)
#   quote_ccy     the pair's quote currency (FOREX pip value depends on it)
# Each returns: size, lot_size, min_lot, risk_per_unit (cash per 1 size unit per
#   stop), notional, contract_multiplier, size_unit (label), flags (extra notes).
# ----------------------------------------------------------------------------
def _round_down_to(raw: Decimal, lot: Decimal) -> Decimal:
    """Round a raw size DOWN to the nearest lot increment (never breaches the cap)."""
    return (raw / lot).to_integral_value(rounding=ROUND_DOWN) * lot


def _size_dollar_per_point(spec, *, price_risk, dollar_risk, sizing_entry, quote_ccy):
    """
    GOLD / SILVER (and any CFD priced as $ per point). A 1.0 price move is worth
    `contract_multiplier` per 1.0 lot. This is the original metals maths, intact.
    """
    p = spec["params"]
    mult = _D(p["contract_multiplier"])
    lot = _D(p["lot_size"])
    min_lot = _D(p.get("min_lot", p["lot_size"]))
    risk_per_unit = price_risk * mult
    size = _round_down_to(dollar_risk / risk_per_unit, lot)
    notional = size * sizing_entry * mult
    return {
        "size": size, "lot_size": lot, "min_lot": min_lot,
        "risk_per_unit": risk_per_unit, "notional": notional,
        "contract_multiplier": mult, "size_unit": "lot(s)", "flags": [],
    }


def _size_pip_value(spec, *, price_risk, dollar_risk, sizing_entry, quote_ccy):
    """
    FOREX. Size in standard lots, where 1.0 lot = `contract_units` of the base
    currency. The cash value of a price move is in the pair's QUOTE currency, so
    we convert quote -> account at the configured (approximate) rate. USD-quote
    pairs use the engine's USD≈account 1:1 proxy; non-USD quotes (USDCAD->CAD,
    crosses, JPY) are sized with the configured rate and flagged CONFIRM.
    """
    p = spec["params"]
    units = _D(p["contract_units"])
    lot = _D(p["lot_size"])
    min_lot = _D(p.get("min_lot", p["lot_size"]))
    rate = asset_classes.quote_to_account_rate(quote_ccy)
    # Value of a 1.0 price move on 1.0 standard lot, in account currency.
    multiplier = units * rate
    risk_per_unit = price_risk * multiplier
    size = _round_down_to(dollar_risk / risk_per_unit, lot)
    notional = size * sizing_entry * multiplier
    flags = []
    if not asset_classes.is_usd_proxy_quote(quote_ccy):
        q = quote_ccy or "non-USD"
        flags.append(
            f"CONFIRM WITH BROKER: {q}-quote pair — true pip value depends on the "
            f"live {q}->{config.ACCOUNT_CURRENCY} rate; sized using an approximate "
            f"rate of {rate} (refresh before trusting the lot size)."
        )
    return {
        "size": size, "lot_size": lot, "min_lot": min_lot,
        "risk_per_unit": risk_per_unit, "notional": notional,
        "contract_multiplier": multiplier, "size_unit": "lot(s)", "flags": flags,
    }


def _size_percent_risk(spec, *, price_risk, dollar_risk, sizing_entry, quote_ccy):
    """
    CRYPTO. Percentage-of-capital-at-risk sizing: position sized so that being
    stopped out costs exactly the risk-% budget. Size is in fractional COIN
    UNITS (no contract multiplier, multiplier = 1). Slippage/fees are NOT
    modelled yet — flagged on the ticket.
    """
    p = spec["params"]
    mult = Decimal("1")
    lot = _D(p["lot_size"])
    min_lot = _D(p.get("min_lot", p["lot_size"]))
    risk_per_unit = price_risk * mult
    size = _round_down_to(dollar_risk / risk_per_unit, lot)
    notional = size * sizing_entry * mult
    return {
        "size": size, "lot_size": lot, "min_lot": min_lot,
        "risk_per_unit": risk_per_unit, "notional": notional,
        "contract_multiplier": mult, "size_unit": "unit(s)", "flags": [],
    }


# Registry: strategy name (from config.ASSET_CLASSES["…"]["sizing"]) -> function.
# Add a new key here only when a class needs genuinely new sizing maths.
SIZING_STRATEGIES = {
    "dollar_per_point": _size_dollar_per_point,
    "pip_value": _size_pip_value,
    "percent_risk": _size_percent_risk,
}


# ----------------------------------------------------------------------------
# Rule-profile helpers (CPS)
# ----------------------------------------------------------------------------
def resolve_risk_profile():
    """
    Work out the risk % for the active rule profile.

    Returns (risk_pct: Decimal, phase: int, profile: str, cap: Decimal).
    CPS uses phase-based risk (1%/2%/3%), clamped to the [floor, hard-cap] band.
    DEFAULT uses the flat RISK_PCT with a 1% notion of cap.
    """
    profile = (config.RULE_PROFILE or "DEFAULT").upper()
    if profile == "CPS":
        phase = int(config.TRADING_PHASE)
        pct = Decimal(config.PHASE_RISK.get(phase, config.PHASE_RISK[1]))
        floor = Decimal(config.RISK_PCT_MIN)
        cap = Decimal(config.RISK_PCT_MAX)
        pct = max(floor, min(pct, cap))     # clamp — risk can NEVER exceed the cap
        return pct, phase, "CPS", cap
    return Decimal(config.RISK_PCT), 0, "DEFAULT", Decimal(config.RISK_PCT)


def _resolve_stop(signal, cfg, direction, sizing_entry):
    """
    Decide the effective stop price and how it was set.

    Returns (stop: Decimal, stop_mode: str).
    FIXED mode (CPS, metals only) places the stop a fixed dollar distance from
    the sizing entry. Otherwise the signal's own stop is used.
    """
    profile = (config.RULE_PROFILE or "DEFAULT").upper()
    mode = (config.STOP_MODE or "SIGNAL").upper() if profile == "CPS" else "SIGNAL"

    if mode == "FIXED" and cfg["asset_class"] == "METAL":
        t = (signal.ticker or "").upper()
        key = "XAU" if t.startswith("XAU") else ("XAG" if t.startswith("XAG") else None)
        if key and key in config.FIXED_STOP:
            dist = Decimal(config.FIXED_STOP[key])
            lo, hi = (Decimal(x) for x in config.FIXED_STOP_RANGE[key])
            if not (lo <= dist <= hi):
                raise RiskError(
                    f"{signal.ticker}: FIXED stop distance ${dist} is outside the "
                    f"allowed ${lo}-${hi} band. Fix FIXED_STOP in config.py."
                )
            stop = sizing_entry + dist if direction == "SHORT" else sizing_entry - dist
            return stop, "FIXED"
    return signal.stop_loss, "SIGNAL"


# ----------------------------------------------------------------------------
# Sizing
# ----------------------------------------------------------------------------
def size_signal(signal: Signal,
                pot_size: Decimal,
                risk_pct: Decimal = None,
                phase: int = None,
                require_targets: bool = True) -> Ticket:
    """
    Turn a validated Signal into a sized Ticket, enforcing the hard risk cap.

    Sizing rules (mandatory — unchanged, never weakened):
      * Entry zone is treated as true (low, high) no matter how it was typed.
      * SHORT  -> size from the LOWEST entry  (closest to stop = tightest = safest).
      * LONG   -> size from the HIGHEST entry (closest to stop = tightest = safest).
      * SHORT  -> stop must sit ABOVE the whole zone, else reject.
      * LONG   -> stop must sit BELOW the whole zone, else reject.
      * Size is always rounded DOWN, so rounding can never breach the cap.
      * If size rounds below the minimum lot, SKIP — protection, not a bug.

    Rule-profile additions (CPS): phase-based risk %, an optional fixed-distance
    stop (metals), and a fixed 1:2 / 1:3 / 1:5 exit ladder scaled out in thirds.
    """
    # Resolve the risk % / phase from the active profile unless told otherwise.
    profile_pct, profile_phase, profile, _cap = resolve_risk_profile()
    if risk_pct is None:
        risk_pct = profile_pct
    if phase is None:
        phase = profile_phase

    cfg = resolve_asset_config(signal)

    # Defence in depth: only size asset classes the engine is CALIBRATED for. The
    # router already sends recognised-but-uncalibrated classes (OIL/COMMODITIES/
    # STOCKS) and UNKNOWN ones to human REVIEW — but if a signal reaches sizing
    # anyway, refuse it loudly rather than size it with guessed maths.
    if not cfg["calibrated"] or cfg["sizing"] not in SIZING_STRATEGIES:
        fc = cfg["fine_class"]
        if fc == asset_classes.UNKNOWN:
            raise RiskError(
                f"{signal.ticker}: asset class not recognised — cannot size it. "
                "Send to human REVIEW."
            )
        raise RiskError(
            f"{signal.ticker}: asset class {fc} recognised but not yet calibrated "
            "for sizing — human review needed. (Add sizing to config.ASSET_CLASSES "
            "to enable it.)"
        )

    direction = (signal.direction or "").upper().strip()

    # Always work from a true (low, high) zone.
    entry_low = min(signal.entry_low, signal.entry_high)
    entry_high = max(signal.entry_low, signal.entry_high)

    # DEFAULT trades the signal's own targets, so it needs them. CPS computes its
    # own fixed-RR ladder, so a missing target list is fine there. A caller that
    # only needs the POSITION sized (entry + stop), not an R:R ladder — e.g. the
    # history back-logger sizing a stop-only signal — can pass require_targets=False;
    # the position still sizes honestly and the ladder is simply left empty.
    if profile != "CPS" and not signal.targets and require_targets:
        raise RiskError(
            f"{signal.ticker}: no targets given — cannot work out reward:risk. "
            "Signal rejected."
        )

    # --- Conservative sizing entry (direction decides which edge) -----------
    # SHORT sizes from the LOW end, LONG from the HIGH end — the WORSE fill of the
    # zone, so size/expectancy is never flattered. The parser records this same
    # value as signal.primary_entry; prefer it when present (one source of truth),
    # and fall back to deriving it for Signals built without it.
    if direction not in ("SHORT", "LONG"):
        raise RiskError(
            f"{signal.ticker}: direction must be LONG or SHORT, got '{signal.direction}'."
        )
    primary = getattr(signal, "primary_entry", None)
    if primary is not None and entry_low <= primary <= entry_high:
        sizing_entry = primary
    else:
        sizing_entry = entry_low if direction == "SHORT" else entry_high

    # --- Effective stop (signal stop, or CPS fixed-distance stop) -----------
    stop, stop_mode = _resolve_stop(signal, cfg, direction, sizing_entry)

    # --- Zone-aware validation (unchanged rail) -----------------------------
    if direction == "SHORT" and not (stop > entry_high):
        raise RiskError(
            f"{signal.ticker} SHORT rejected: the stop ({stop}) must sit ABOVE "
            f"the entire entry zone ({entry_low}–{entry_high}). "
            "This looks malformed — check the numbers."
        )
    if direction == "LONG" and not (stop < entry_low):
        raise RiskError(
            f"{signal.ticker} LONG rejected: the stop ({stop}) must sit BELOW "
            f"the entire entry zone ({entry_low}–{entry_high}). "
            "This looks malformed — check the numbers."
        )

    # --- Slippage: worsen the EFFECTIVE entry (honest fills) ----------------
    # Real fills aren't at the exact price — you get in slightly worse. Worsen
    # the entry by the per-side slippage estimate, in the direction that hurts,
    # BEFORE sizing, so the stop distance, size and reward:risk all reflect a
    # realistic fill rather than a perfect one. The stop itself is unchanged (it
    # was set above); slippage only moves where we actually got IN.
    slippage = cfg.get("slippage", Decimal("0"))
    raw_entry = sizing_entry
    if slippage > 0:
        sizing_entry = (sizing_entry + slippage) if direction == "LONG" \
            else (sizing_entry - slippage)

    # --- The hard cap (per-asset-class sizing strategy) ---------------------
    price_risk_per_unit = abs(sizing_entry - stop)        # stop distance in price ("sl_dollar")
    if price_risk_per_unit <= 0:
        raise RiskError(
            f"{signal.ticker}: entry and stop are the same price — no measurable risk. "
            "Signal rejected."
        )

    dollar_risk = pot_size * risk_pct                     # budgeted cash at risk

    # Dispatch to this asset class's sizing strategy. Each rounds DOWN to its lot
    # increment, so rounding can NEVER breach the cap — the one rule, preserved
    # identically across every asset class.
    strategy = SIZING_STRATEGIES[cfg["sizing"]]
    sized = strategy(
        cfg,
        price_risk=price_risk_per_unit,
        dollar_risk=dollar_risk,
        sizing_entry=sizing_entry,
        quote_ccy=cfg.get("quote_currency", ""),
    )
    size = sized["size"]
    lot = sized["lot_size"]
    min_lot = sized["min_lot"]
    multiplier = sized["contract_multiplier"]
    risk_per_unit = sized["risk_per_unit"]
    notional = sized["notional"]
    size_unit = sized["size_unit"]
    extra_flags = sized["flags"]

    if size < min_lot or size <= 0:
        raise RiskError(
            f"{signal.ticker}: this trade cannot be taken within the "
            f"{risk_pct * 100:.2f}% risk rule — the stop is too far from entry for a "
            f"{config.CURRENCY}{dollar_risk} risk budget "
            f"(needs at least {min_lot} {size_unit}). Nothing was sized. "
            "(This is the protection working, not a bug.)"
        )

    # --- Resulting numbers --------------------------------------------------
    cash_at_risk = size * risk_per_unit
    risk_pct_of_pot = cash_at_risk / pot_size

    # --- Exit ladder --------------------------------------------------------
    if profile == "CPS":
        ladder_rr = [Decimal(x) for x in config.CPS_LADDER_RR]
        scale_out = list(config.CPS_SCALE_OUT)
        # Fixed RR targets measured from the sizing entry, in the profit direction.
        if direction == "LONG":
            tps = [sizing_entry + rr * price_risk_per_unit for rr in ladder_rr]
        else:
            tps = [sizing_entry - rr * price_risk_per_unit for rr in ladder_rr]
        rr_targets = ladder_rr
    else:
        tps = list(signal.targets)
        rr_targets = [abs(t - sizing_entry) / price_risk_per_unit for t in tps]
        scale_out = []

    first_target = tps[0] if tps else None          # may be None for a stop-only trade
    tp1 = tps[0] if len(tps) > 0 else None
    tp2 = tps[1] if len(tps) > 1 else None
    tp3 = tps[2] if len(tps) > 2 else None
    rr_first_target = rr_targets[0] if rr_targets else None

    return Ticket(
        signal=signal,
        asset_class=cfg["asset_class"],
        contract_multiplier=multiplier,
        asset_verified=cfg["verified"],
        pot_size=pot_size,
        sizing_entry=sizing_entry,
        raw_entry=raw_entry,
        slippage=slippage,
        stop_loss=stop,
        first_target=first_target,
        size=size,
        notional=notional,
        cash_at_risk=cash_at_risk,
        risk_pct_of_pot=risk_pct_of_pot,
        rr_first_target=rr_first_target,
        rr_targets=rr_targets,
        profile=profile,
        phase=phase,
        risk_pct=risk_pct,
        dollar_risk=dollar_risk,
        lots=size,
        sl_dollar=price_risk_per_unit,
        stop_mode=stop_mode,
        tp1=tp1,
        tp2=tp2,
        tp3=tp3,
        scale_out=scale_out,
        broker_note=cfg.get("broker_note", ""),
        sizing_method=cfg["sizing"],
        size_unit=size_unit,
        quote_currency=cfg.get("quote_currency", "") if cfg["fine_class"] == "FOREX" else "",
        # Per-class honesty flags from config, plus any the strategy raised
        # (e.g. FOREX non-USD quote conversion warning).
        flags=list(cfg.get("flags", [])) + list(extra_flags),
    )


# ----------------------------------------------------------------------------
# Pretty printing for a ticket (shared by run.py and the self-test below)
# ----------------------------------------------------------------------------
def format_ticket(ticket: Ticket, currency: str = "£") -> str:
    s = ticket.signal
    lines = []
    lines.append("-" * 64)
    tag = f"  TICKET (PAPER)  {s.ticker}  {s.direction}   [{ticket.asset_class}]"
    if ticket.profile == "CPS":
        tag += f"   {{CPS · Phase {ticket.phase}}}"
    lines.append(tag)
    lines.append("-" * 64)
    lines.append(f"  Pair                : {s.pair}")
    if s.session or s.level_tf:
        ctx = "  /  ".join(p for p in (s.session, s.level_tf) if p)
        lines.append(f"  Context             : {ctx}")
    lines.append(f"  Entry zone          : {s.entry_low} – {s.entry_high}")
    if ticket.slippage and ticket.slippage > 0:
        lines.append(f"  Conservative entry  : {ticket.raw_entry}")
        lines.append(f"  Slippage modelled   : ${ticket.slippage} per side "
                     f"(worsens the fill)")
        lines.append(f"  Sizing entry (used) : {ticket.sizing_entry}   "
                     f"(after slippage — R:R below is honest)")
    else:
        lines.append(f"  Sizing entry (used) : {ticket.sizing_entry}   "
                     f"(no slippage modelled for this instrument)")
    lines.append(f"  Stop loss           : {ticket.stop_loss}   "
                 f"(distance {currency}{_money(ticket.sl_dollar)}, mode: {ticket.stop_mode})")
    lines.append("")
    lines.append(f"  Size                : {ticket.lots} {ticket.size_unit}")
    if ticket.quote_currency:
        lines.append(f"  Quote currency      : {ticket.quote_currency}   "
                     f"(pip value is in this currency)")
    lines.append(f"  Notional            : {currency}{_money(ticket.notional)}")
    lines.append(f"  Budgeted risk       : {currency}{_money(ticket.dollar_risk)}  "
                 f"({ticket.risk_pct * 100:.2f}% of pot)")
    lines.append(f"  Cash at risk (real) : {currency}{_money(ticket.cash_at_risk)}  "
                 f"({ticket.risk_pct_of_pot * 100:.3f}% of pot)")

    if ticket.profile == "CPS":
        lines.append("")
        lines.append("  CPS exit ladder (scale out in thirds):")
        labels = ["TP1", "TP2", "TP3"]
        tps = [ticket.tp1, ticket.tp2, ticket.tp3]
        for i, (lab, tp, rr) in enumerate(zip(labels, tps, ticket.rr_targets)):
            plan = ticket.scale_out[i] if i < len(ticket.scale_out) else ""
            line = f"      {lab}  {tp}".ljust(34) + f"1:{rr:g}".ljust(8) + plan
            lines.append(line)
        lines.append("  Stop rule           : set at entry, NEVER widened. "
                     "After TP2, move stop to breakeven on the runner.")
    else:
        lines.append(f"  R:R to first target : {ticket.rr_first_target:.2f} : 1")
        lines.append("  R:R ladder          :")
        for i, (tgt, rr) in enumerate(zip(s.targets, ticket.rr_targets), start=1):
            lines.append(f"      T{i}  {tgt}".ljust(30) + f"{rr:.2f} : 1")

    notes_block = []
    if ticket.broker_note:
        notes_block.append(f"** CONFIRM SPECS: {ticket.broker_note}")
    elif not ticket.asset_verified:
        notes_block.append("** WARNING: contract spec is unverified — confirm before live.")
    for flag in ticket.flags:
        notes_block.append(f"** {flag}")
    if notes_block:
        lines.append("")
        for note in notes_block:
            lines.append(f"  {note}")
    lines.append("-" * 64)
    return "\n".join(lines)


def _money(d: Decimal) -> str:
    """Format a Decimal as money with 2 dp for display."""
    return f"{d.quantize(Decimal('0.01'), rounding=ROUND_DOWN):,}"


# ----------------------------------------------------------------------------
# Self-test: the five REAL signals from the brief.
# ----------------------------------------------------------------------------
def _build(ticker, pair, direction, asset_class, e1, e2, sl, targets, raw):
    return Signal(
        ticker=ticker,
        pair=pair,
        direction=direction,
        asset_class=asset_class,
        entry_low=Decimal(min(e1, e2)),
        entry_high=Decimal(max(e1, e2)),
        stop_loss=Decimal(sl),
        targets=[Decimal(t) for t in targets],
        raw_text=raw,
    )


def _run_self_test():
    pot = Decimal("14000")
    risk = Decimal("0.01")

    tests = [
        _build("FET", "FET/USDT", "SHORT", "CRYPTO",
               "1.4334", "1.4721", "1.5284",
               ["1.3912", "1.3323", "1.2612", "1.1578"],
               "FET/USDT SHORT zone 1.4334-1.4721 SL 1.5284 ..."),
        _build("SOL", "SOL/USDT", "LONG", "CRYPTO",
               "131.20", "134.65", "127.15",
               ["138.80", "143.50", "149.00", "156.00"],
               "SOL/USDT LONG zone 131.20-134.65 SL 127.15 ..."),
        _build("PEPE", "PEPE/USDT", "SHORT", "CRYPTO",
               "0.00001221", "0.00001258", "0.00001306",
               ["0.0000118", "0.00001135", "0.0000106", "0.0000097"],
               "PEPE/USDT SHORT zone 0.00001221-0.00001258 SL 0.00001306 ..."),
        _build("XAUUSD", "XAUUSD", "LONG", "METAL",
               "2292.00", "2304.50", "2274.00",
               ["2325", "2350", "2385"],
               "XAUUSD LONG zone 2292.00-2304.50 SL 2274.00 ..."),
        _build("XAGUSD", "XAGUSD", "SHORT", "METAL",
               "29.850", "30.200", "30.650",
               ["29.20", "28.50", "27.30"],
               "XAGUSD SHORT zone 29.850-30.200 SL 30.650 ..."),
        # FOREX — the kind of pair that used to mis-size (USDCAD). Sizes in lots
        # via pip-value maths, with a CONFIRM-WITH-BROKER flag for the non-USD quote.
        _build("USDCAD", "USDCAD", "SHORT", "",
               "1.4600", "1.4600", "1.4650",
               ["1.4520", "1.4450"],
               "USDCAD SHORT 1.4600 SL 1.4650 (forex)"),
        # OIL — recognised but NOT yet calibrated: sizing must REFUSE it (the
        # router would already have sent it to human review upstream).
        _build("USOIL", "USOIL", "LONG", "",
               "78.50", "78.50", "77.40",
               ["80.00", "82.00"],
               "USOIL LONG 78.50 SL 77.40 (oil — not calibrated)"),
    ]

    print("\n" + "=" * 60)
    print("  RISK CALCULATOR SELF-TEST   pot = £14,000   cap = 1%")
    print("=" * 60)
    for sig in tests:
        try:
            ticket = size_signal(sig, pot, risk)
            print(format_ticket(ticket))
        except RiskError as e:
            print("-" * 60)
            print(f"  REJECTED: {e}")
            print("-" * 60)
    print()


if __name__ == "__main__":
    _run_self_test()
