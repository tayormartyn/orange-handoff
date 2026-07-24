"""Follower Assistant v0.1 — deterministic Stage-1 engine (REVIEW-ONLY).

NO BROKER ACTION. NO ORDER SUBMISSION. REVIEW-ONLY SHADOW PROPOSAL.

Applies the RATIFIED follower_constitution_v0_1.json to a frozen campaign capture and
1-minute OHLC, producing per-lane theoretical results and an append-only transition log.

Design laws:
  * decimal.Decimal for prices/money; fractions.Fraction for position sizes (exact thirds);
    pips = USD * 10 (1 pip = $0.10, XAUUSD project convention), quantized to 0.01.
  * No AI arithmetic; no randomness; no wall-clock in outcomes (deterministic timestamps come
    from evidence and bars; run stamps live only in provenance fields).
  * Fail-closed: contradictions/unknown instructions -> PAUSED_NEEDS_HUMAN_REVIEW.
  * Same-bar conflicts: adverse-first ("stop-first-on-touch"), tagged AMBIGUOUS_SEQUENCE.
  * Idempotent: logical_hash over (setup, constitution, lane, evidence, ohlc) — a re-run
    yields byte-identical results; ledger appends are skipped on identical hash.
  * Source campaign evidence is NEVER mutated; the engine only reads it.
  * Prohibited fields (lot/account/broker/order/credentials/execution) cannot appear in any
    emitted record — enforced by guards.assert_clean on every emission.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from decimal import Decimal, getcontext
from fractions import Fraction

getcontext().prec = 28

D = Decimal
PIPS_PER_USD = D("10")          # 1 pip = $0.10
HERE = os.path.dirname(os.path.abspath(__file__))

LANES = {
    "LANE_A": {"name": "STRICT_FOLLOWER", "fill_mode": "THROUGH", "be_basis": "PER_LEG",
               "graze_usd": D("0"), "unfilled_on_be": "CANCEL"},
    "LANE_B": {"name": "POLICY_SENSITIVITY", "fill_mode": "TOUCH", "be_basis": "AVERAGE",
               "graze_usd": D("3.00"), "unfilled_on_be": "KEEP"},
}

TAKE_SOME_DEFAULT = Fraction(1, 4)      # ratified Q4 (DESIGN_PCT)
SINGLE_LEG_CLOSE_WORST = Fraction(1, 2)  # P11 single-leg default
TP1_FRACTION = Fraction(1, 2)            # P12 instruction-driven TP1
REENTRY_MAX_ATTEMPT = 2                  # P15 (attempt >=3 skipped)


def sha256_file(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def sha256_obj(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                                     default=str).encode("utf-8")).hexdigest()


def pips(usd: Decimal) -> Decimal:
    return (usd * PIPS_PER_USD).quantize(D("0.01"))


@dataclass
class Leg:
    leg_id: str
    price: Decimal                    # limit / market-reference price
    size: Fraction                    # of campaign unit
    kind: str = "LIMIT"               # LIMIT | MARKET_AT_SIGNAL_CLOSE
    state: str = "PROPOSED"           # PROPOSED | FILLED | CANCELLED | EXPIRED
    fill_price: Decimal | None = None
    fill_bar_ts: int | None = None
    open_size: Fraction = Fraction(0)
    be_price: Decimal | None = None   # armed break-even stop
    tags: list = field(default_factory=list)


@dataclass
class Slice:
    """A banked (closed) piece of position."""
    leg_id: str
    size: Fraction
    entry: Decimal
    exit: Decimal
    reason: str
    bar_ts: int
    message_id: int | None = None
    tags: list = field(default_factory=list)


class FollowerEngine:
    """One campaign x one lane. Deterministic bar-walk."""

    def __init__(self, campaign: dict, bars: list, lane_key: str, constitution: dict):
        self.c = campaign
        self.bars = bars                        # [(ts, o, h, l, cl)] Decimals, sorted, 1m
        self.lane_key = lane_key
        self.lane = LANES[lane_key]
        self.constitution = constitution
        self.direction = campaign["direction"]  # LONG | SHORT
        self.sgn = D(1) if self.direction == "LONG" else D(-1)
        self.current_sl = D(campaign["sl"])     # REVISED_STOP moves this forward-only (never retroactive)
        self.transitions = []
        self.slices: list[Slice] = []
        self.legs: list[Leg] = []
        self.state = "PROPOSED"
        self.ambiguities = []
        self.paused_reason = None
        self._near_logged = set()               # (leg_id, level) -> near-miss logged once
        self._prev_bar = None                   # previous processed bar (gap-context)

    # ---- construction -------------------------------------------------------------
    def propose_legs(self):
        lo, hi = D(self.c["zone_low"]), D(self.c["zone_high"])
        mid = ((lo + hi) / 2).quantize(D("0.01"))
        order = [hi, mid, lo] if self.direction == "LONG" else [lo, mid, hi]  # near, mid, far
        names = ["near", "mid", "far"]
        n = Fraction(1, 3)
        self.legs = [Leg(f"{self.c['setup_id']}/{nm}", p, n) for nm, p in zip(names, order)]
        self._log("LEGS_PROPOSED", rule="P04", detail={
            "legs": [{"leg_id": l.leg_id, "price": str(l.price), "size": str(l.size)} for l in self.legs]})

    # ---- helpers -------------------------------------------------------------------
    def _log(self, event, rule, detail=None, bar_ts=None, message_id=None, tags=None):
        self.transitions.append({
            "event": event, "rule": rule, "bar_ts": bar_ts, "message_id": message_id,
            "detail": detail or {}, "tags": tags or []})

    def _open_size(self):
        return sum((l.open_size for l in self.legs), Fraction(0))

    def _filled_legs(self):
        return [l for l in self.legs if l.state == "FILLED" and l.open_size > 0]

    def _avg_entry(self):
        fl = [l for l in self.legs if l.state == "FILLED"]
        if not fl:
            return None
        tot = sum((l.size for l in fl), Fraction(0))
        acc = sum((l.fill_price * D(l.size.numerator) / D(l.size.denominator) for l in fl), D(0))
        return (acc / (D(tot.numerator) / D(tot.denominator))).quantize(D("0.0001"))

    def _bank(self, leg: Leg, frac_of_leg_open: Fraction, price: Decimal, reason, bar_ts, message_id=None, tags=None):
        size = leg.open_size * frac_of_leg_open
        if size <= 0:
            return
        leg.open_size -= size
        self.slices.append(Slice(leg.leg_id, size, leg.fill_price, price, reason, bar_ts, message_id, tags or []))
        usd = (price - leg.fill_price) * self.sgn
        self._log("BANK", rule=reason, bar_ts=bar_ts, message_id=message_id, tags=tags, detail={
            "leg_id": leg.leg_id, "size": str(size), "entry": str(leg.fill_price),
            "exit": str(price), "usd_per_unit_of_slice": str(usd if usd != 0 else D("0"))})

    def _bank_across(self, frac_of_open: Fraction, price, reason, bar_ts, message_id=None, tags=None):
        for leg in self._filled_legs():
            self._bank(leg, frac_of_open, price, reason, bar_ts, message_id, tags)

    def _cancel_unfilled(self, why, bar_ts, message_id=None):
        for l in self.legs:
            if l.state == "PROPOSED":
                l.state = "CANCELLED"
                self._log("LEG_CANCELLED", rule=why, bar_ts=bar_ts, message_id=message_id,
                          detail={"leg_id": l.leg_id})

    # ---- fills / stops per bar -----------------------------------------------------
    def _try_fill(self, leg: Leg, bar):
        ts, o, h, l, cl = bar
        if leg.state != "PROPOSED":
            return False
        if leg.kind == "MARKET_AT_SIGNAL_CLOSE":
            leg.state, leg.fill_price, leg.fill_bar_ts, leg.open_size = "FILLED", cl, ts, leg.size
            leg.tags.append("AMBIGUOUS_SEQUENCE_INTRA_BAR_SIGNAL")
            self._log("LEG_FILLED", rule="P06", bar_ts=ts, detail={
                "leg_id": leg.leg_id, "fill": str(cl), "kind": leg.kind},
                tags=["AMBIGUOUS_SEQUENCE"])
            return True
        through = self.lane["fill_mode"] == "THROUGH"
        extreme = l if self.direction == "LONG" else h
        if self.direction == "LONG":
            hit = (l < leg.price) if through else (l <= leg.price)
        else:
            hit = (h > leg.price) if through else (h >= leg.price)
        if hit:
            leg.state, leg.fill_price, leg.fill_bar_ts, leg.open_size = "FILLED", leg.price, ts, leg.size
            # feed-divergence band: a fill whose bar extreme clears the limit by <= $3 could be a
            # no-fill on another feed — tag in BOTH lanes (P17 / red-team finding 4)
            tags = ["AMBIGUOUS_FILL_BAND"] if abs(extreme - leg.price) <= D("3.00") else []
            if tags:
                self.ambiguities.append({"bar_ts": ts, "leg": leg.leg_id,
                                         "note": f"fill margin ${abs(extreme - leg.price)} within $3 feed-divergence band"})
            self._log("LEG_FILLED", rule="P05", bar_ts=ts, tags=tags, detail={
                "leg_id": leg.leg_id, "fill": str(leg.price), "mode": self.lane["fill_mode"]})
            leg.tags.extend(tags)
            return True
        return False

    def _level_trigger(self, extreme, level, adverse_dir):
        """(triggered, graze_survived, band_tag). adverse_dir: -1 = adverse move is DOWN (LONG).
        Lane graze: breach <= graze survives (P17, boundary-inclusive); graze 0 = any touch triggers.
        band_tag flags any event/near-event within the $3 feed-divergence band (both lanes)."""
        graze = self.lane["graze_usd"]
        breach = (level - extreme) if adverse_dir < 0 else (extreme - level)
        touched = breach >= 0
        if graze > 0:
            trig = breach > graze
        else:
            trig = touched
        band = touched and breach <= D("3.00")
        return trig, (touched and not trig), band

    def _stop_checks(self, bar):
        """Adverse-first: BE scratch takes precedence over posted SL when both are struck in one
        bar (any continuous path reaches the BE level first — red-team finding 2); grazes within
        the $3 feed-divergence band are tagged in BOTH lanes (finding 4); Lane graze tolerance
        applies to the posted SL as well as BE (finding 8)."""
        ts, o, h, l, cl = bar
        sl = self.current_sl
        adverse = -1 if self.direction == "LONG" else 1
        extreme = l if self.direction == "LONG" else h
        acted = False
        def exit_price(level):
            """Gap-aware exit (red-team finding 3): the realistic exit is the (worse) OPEN only
            on a TRUE discontinuity — the bar opens beyond the level AND the previous bar never
            reached it. If price already traded at/through the level earlier (e.g. Lane-B graze
            survival), the stop model exits at the level itself."""
            gapped = (o < level) if self.direction == "LONG" else (o > level)
            if gapped and self._prev_bar is not None:
                po, ph, pl, pc = self._prev_bar[1:]
                prev_reached = (pl <= level) if self.direction == "LONG" else (ph >= level)
                gapped = not prev_reached
            return (o, True) if gapped else (level, False)

        for leg in self._filled_legs():
            be = leg.be_price
            if be is not None:
                trig, grazed, band = self._level_trigger(extreme, be, adverse)
                if grazed:
                    self.ambiguities.append({"bar_ts": ts, "leg": leg.leg_id,
                                             "note": f"BE graze within ${self.lane['graze_usd']} tolerance — survived (AMBIGUOUS_FILL_BAND)"})
                    self._log("BE_GRAZE_SURVIVED", rule="P17", bar_ts=ts,
                              detail={"leg_id": leg.leg_id, "be": str(be)},
                              tags=["AMBIGUOUS_FILL_BAND"])
                if trig:
                    tags = ["STOP_FIRST_ON_TOUCH", "AMBIGUOUS_SEQUENCE"] + (["AMBIGUOUS_FILL_BAND"] if band else [])
                    sl_also = (l <= sl) if self.direction == "LONG" else (h >= sl)
                    if sl_also:
                        tags.append("BE_PRECEDES_SL_SAME_BAR")
                    px, gapped = exit_price(be)
                    if gapped:
                        tags.append("GAP_FILL_UNCERTAIN")
                    self._bank(leg, Fraction(1), px, "P10_BE_SCRATCH", ts, tags=tags)
                    if band:
                        self.ambiguities.append({"bar_ts": ts, "leg": leg.leg_id,
                                                 "note": "BE scratch within $3 feed-divergence band (AMBIGUOUS_FILL_BAND)"})
                    acted = True
                    continue
                nk = (leg.leg_id, "BE", str(be))
                if not trig and not grazed and abs(extreme - be) <= D("3.00") and nk not in self._near_logged:
                    self._near_logged.add(nk)
                    self.ambiguities.append({"bar_ts": ts, "leg": leg.leg_id,
                                             "note": "price within $3 of the BE level without touch (FEED_SENSITIVE_NEAR_MISS)"})
            trig, grazed, band = self._level_trigger(extreme, sl, adverse)
            if grazed:
                self.ambiguities.append({"bar_ts": ts, "leg": leg.leg_id,
                                         "note": f"posted-SL graze within ${self.lane['graze_usd']} tolerance — survived (AMBIGUOUS_FILL_BAND)"})
                self._log("SL_GRAZE_SURVIVED", rule="P17", bar_ts=ts,
                          detail={"leg_id": leg.leg_id, "sl": str(sl)}, tags=["AMBIGUOUS_FILL_BAND"])
            if trig:
                tags = ["STOP_FIRST_ON_TOUCH"] + (["AMBIGUOUS_FILL_BAND"] if band else [])
                px, gapped = exit_price(sl)
                if gapped:
                    tags.append("GAP_FILL_UNCERTAIN")
                self._bank(leg, Fraction(1), px, "P21_POSTED_SL", ts, tags=tags)
                acted = True
            elif not grazed and abs(extreme - sl) <= D("3.00"):
                nk = (leg.leg_id, "SL", str(sl))
                if nk not in self._near_logged:
                    self._near_logged.add(nk)
                    self.ambiguities.append({"bar_ts": ts, "leg": leg.leg_id,
                                             "note": "price within $3 of the posted SL without touch (FEED_SENSITIVE_NEAR_MISS)"})
        return acted

    # ---- instructions ----------------------------------------------------------------
    def _apply_message(self, events, bar):
        """All instruction events of ONE message = one transition (coalesced, P11/P12).
        P20 fail-closed runs FIRST and is never overwritten (red-team finding 3)."""
        ts, o, h, l, cl = bar
        types = [e["instruction_type"] for e in events]
        mid = events[0].get("message_id")
        filled = self._filled_legs()

        if self.state == "PAUSED_NEEDS_HUMAN_REVIEW":
            self._log("MESSAGE_SKIPPED_WHILE_PAUSED", rule="P20", bar_ts=ts, message_id=mid,
                      detail={"types": types})
            return

        unknown = [t for t in types if t not in
                   ("FINAL_CLOSE", "EXPLICIT_FULL_EXIT", "CANCEL", "CLOSE_WORST", "HOLD_BEST",
                    "TP1_TAKE", "TP2_TAKE", "TAKE_PCT_OFF", "CLOSE_PERCENTAGE_PARTIAL",
                    "EXPLICIT_PERCENTAGE_PARTIAL_CLOSE", "SL_TO_ENTRY", "HOLD_RUNNER",
                    "CANCEL_LIMITS", "REVISED_STOP", "REVISED_ZONE", "INVALIDATION",
                    "RE_ENTER", "OTHER")]
        if unknown:
            self.state = "PAUSED_NEEDS_HUMAN_REVIEW"
            self.paused_reason = f"unknown instruction types {unknown} (P20 fail-closed)"
            self._log("PAUSED", rule="P20", bar_ts=ts, message_id=mid,
                      detail={"unknown_types": unknown, "note": "entire message refused, incl. any co-delivered known types"})
            return

        # ---- tracker-addendum instructions (tracker_policy_addendum_v0_1; constitution v0.1
        # itself untouched). All are ORANGE_DESIGN_CHOICE unless noted. ----
        if "REVISED_ZONE" in types:
            self.state = "PAUSED_NEEDS_HUMAN_REVIEW"
            self.paused_reason = "zone revised mid-campaign — entry structure change (fail-closed)"
            self._log("PAUSED", rule="ADD_REVISED_ZONE", bar_ts=ts, message_id=mid)
            return
        if "INVALIDATION" in types:
            if filled:
                self.state = "PAUSED_NEEDS_HUMAN_REVIEW"
                self.paused_reason = "provider invalidated setup with position open — human review"
                self._log("PAUSED", rule="ADD_INVALIDATION", bar_ts=ts, message_id=mid)
            elif self.slices:
                # position already fully banked: this campaign TRADED (red-team finding 7)
                self._cancel_unfilled("ADD_INVALIDATION_CANCEL", ts, mid)
                self.state = "CLOSED"
                self._log("INVALIDATION_AFTER_FLAT", rule="ADD_INVALIDATION", bar_ts=ts,
                          message_id=mid, detail={"note": "campaign already flat; result stands"})
            else:
                self._cancel_unfilled("ADD_INVALIDATION_CANCEL", ts, mid)
                self.state = "NO_FILL"
            return
        if "REVISED_STOP" in types:
            new_sl = next((e.get("new_sl") for e in events
                           if e["instruction_type"] == "REVISED_STOP"), None)
            if new_sl is None:
                self.state = "PAUSED_NEEDS_HUMAN_REVIEW"
                self.paused_reason = "stop revision without a parseable level (fail-closed)"
                self._log("PAUSED", rule="ADD_REVISED_STOP", bar_ts=ts, message_id=mid)
                return
            self.current_sl = D(str(new_sl))     # forward-only; earlier bars already resolved
            self._log("STOP_REVISED", rule="ADD_REVISED_STOP(FAROUK_PUBLISHED_RULE:posted revision)",
                      bar_ts=ts, message_id=mid, detail={"new_sl": str(self.current_sl)})
            # instruction-bar check, same as SL_TO_ENTRY arming (red-team finding 4):
            # intra-bar order unknowable -> adverse-first, tagged
            if self._stop_checks(bar):
                self._log("REVISED_STOP_BAR_ADVERSE_TOUCH", rule="P18", bar_ts=ts, message_id=mid,
                          tags=["AMBIGUOUS_SEQUENCE"],
                          detail={"note": "revised stop level touched within the instruction bar itself"})
        if "CANCEL_LIMITS" in types:
            self._cancel_unfilled("ADD_CANCEL_LIMITS", ts, mid)
        if "HOLD_RUNNER" in types:
            self._log("HOLD_RUNNER_NOTED", rule="ADD_HOLD_RUNNER", bar_ts=ts, message_id=mid)
        if "RE_ENTER" in types:
            self._log("RE_ENTER_NOTED", rule="P15", bar_ts=ts, message_id=mid,
                      detail={"note": "re-entry = NEW campaign upstream; no effect on this one"})

        if "FINAL_CLOSE" in types or "EXPLICIT_FULL_EXIT" in types:
            # EXPLICIT_FULL_EXIT (full-exit v0.1: "full exit"/"close all" variants) is terminal
            # with identical ratified semantics: bank ALL remaining filled quantity at close,
            # cancel unfilled resting entries (P14 terminal cancellation).
            for leg in filled:
                self._bank(leg, Fraction(1), cl, "P13_FINAL_CLOSE", ts, mid)
            self._cancel_unfilled("P14_FINAL_CLOSE_CANCEL", ts, mid)
            self.state = "CLOSED" if (self.slices or filled) else "NO_FILL"
            return

        if "CANCEL" in types:
            self._cancel_unfilled("P22_CANCELLATION", ts, mid)

        banked_by_close_worst = False
        if "CLOSE_WORST" in types and filled:
            if len(filled) == 1:
                self._bank(filled[0], SINGLE_LEG_CLOSE_WORST, cl,
                           "P11_SINGLE_LEG_CLOSE_WORST(coalesced_tp1)", ts, mid,
                           tags=["DESIGN_SINGLE_LEG_50"])
                banked_by_close_worst = True
            else:
                worst = max(filled, key=lambda x: x.fill_price) if self.direction == "LONG" \
                    else min(filled, key=lambda x: x.fill_price)
                self._bank(worst, Fraction(1), cl, "P11_CLOSE_WORST", ts, mid)
                # 'hold best' semantics: a co-delivered TP1 is coalesced into the worst-leg close
                # (the held legs are HELD, not half-banked) — red-team finding 10
                banked_by_close_worst = "TP1_TAKE" in types
                if banked_by_close_worst:
                    self._log("TP1_COALESCED_INTO_CLOSE_WORST", rule="P11", bar_ts=ts, message_id=mid,
                              detail={"note": "hold-best honoured; TP1 satisfied by the worst-leg close"})

        if "TP1_TAKE" in types and not banked_by_close_worst:
            if self._filled_legs():
                self._bank_across(TP1_FRACTION, cl, "P12_TP1_INSTRUCTION", ts, mid)
            else:
                self._log("INSTRUCTION_NOT_APPLICABLE", rule="P12", bar_ts=ts, message_id=mid,
                          detail={"why": "no open position"})

        if "TP2_TAKE" in types:
            if self._filled_legs():
                self._bank_across(TP1_FRACTION, cl, "ADD_TP2_INSTRUCTION", ts, mid)
            else:
                self._log("INSTRUCTION_NOT_APPLICABLE", rule="ADD_TP2", bar_ts=ts, message_id=mid,
                          detail={"why": "no open position"})

        for e in events:
            if e["instruction_type"] in ("TAKE_PCT_OFF", "CLOSE_PERCENTAGE_PARTIAL",
                                         "EXPLICIT_PERCENTAGE_PARTIAL_CLOSE"):
                # Explicit percentage reductions (CLOSE_PERCENTAGE_v0_1 / EPPC engine mapping
                # v0.1): close the stated fraction of the CURRENT REMAINING open filled
                # quantity — never the original campaign quantity. Runner remainder preserved;
                # unfilled entries are NOT cancelled here. Only TAKE_PCT_OFF may fall back to
                # the ratified 25% default; an EXPLICIT instruction with an undeterminable or
                # non-reconciling payload FAILS CLOSED (P20-style pause, no exposure change).
                pct = e.get("pct")
                if e["instruction_type"] == "EXPLICIT_PERCENTAGE_PARTIAL_CLOSE":
                    cp, rp = e.get("close_percentage"), e.get("retain_percentage")
                    qb = e.get("quantity_base")
                    valid = (isinstance(cp, int) and isinstance(rp, int)
                             and 0 < cp < 100 and 0 < rp < 100 and cp + rp == 100
                             and qb == "CURRENTLY_REMAINING_OPEN_FILLED_QUANTITY")
                    if valid and pct is None:
                        pct = cp / 100.0
                    if not valid or pct is None or abs(pct * 100 - cp) > 1e-9:
                        self.state = "PAUSED_NEEDS_HUMAN_REVIEW"
                        self.paused_reason = ("explicit percentage partial-close payload invalid/"
                                              f"undeterminable (close={cp!r} retain={rp!r} "
                                              f"base={qb!r} pct={e.get('pct')!r}) — fail closed")
                        self._log("PAUSED", rule="P20", bar_ts=ts, message_id=mid,
                                  detail={"why": self.paused_reason})
                        return
                frac = Fraction(pct).limit_denominator(1000) if pct else TAKE_SOME_DEFAULT
                tag = [] if pct else ["DESIGN_PCT_DEFAULT_25"]
                if self._filled_legs():
                    self._bank_across(frac, cl, "P12_TAKE_PCT", ts, mid, tags=tag)
                else:
                    self._log("INSTRUCTION_NOT_APPLICABLE", rule="P12", bar_ts=ts, message_id=mid,
                              detail={"why": "no open position",
                                      "instruction": e["instruction_type"]})

        if "SL_TO_ENTRY" in types:
            scope = next((e.get("scope") for e in events if e["instruction_type"] == "SL_TO_ENTRY"), None)
            targets = self._filled_legs()
            if scope and "lowest" in str(scope).lower() and targets:
                # literal wording: 'lowest entry' = lowest PRICE fill, direction-independent
                # (red-team finding 11; F001 LONG usage is the only observed instance)
                targets = [min(targets, key=lambda x: x.fill_price)]
            if self.lane["be_basis"] == "AVERAGE" and not scope:
                avg = self._avg_entry()
                for leg in targets:
                    leg.be_price = avg
            else:
                for leg in targets:
                    leg.be_price = leg.fill_price
            for leg in targets:
                self._log("BE_ARMED", rule="P10", bar_ts=ts, message_id=mid,
                          detail={"leg_id": leg.leg_id, "be": str(leg.be_price),
                                  "basis": "SCOPED_LEG" if scope else self.lane["be_basis"]})
            if self.lane["unfilled_on_be"] == "CANCEL":
                self._cancel_unfilled("P14_SL_TO_ENTRY_CANCEL", ts, mid)
            # arm-bar check: the arming bar's own range is tested immediately (adverse-first;
            # intra-bar order unknowable) — red-team finding 6
            if self._stop_checks(bar):
                self._log("ARM_BAR_ADVERSE_TOUCH", rule="P18", bar_ts=ts, message_id=mid,
                          detail={"note": "BE/SL level touched within the arming bar itself"},
                          tags=["AMBIGUOUS_SEQUENCE"])

    # ---- main walk ---------------------------------------------------------------------
    def run(self):
        if int(self.c.get("attempt_number", 1)) > REENTRY_MAX_ATTEMPT:
            self.state = "SKIPPED_BY_R2_CAP"
            self._log("SKIPPED", rule="P15", detail={"attempt": self.c.get("attempt_number")})
            return self.result()

        self.propose_legs()
        sig = int(self.c["signal_ts"])
        bars = [b for b in self.bars if b[0] >= sig - (sig % 60)]
        if not bars:
            self.state = "PAUSED_NEEDS_HUMAN_REVIEW"
            self.paused_reason = "no price data at/after signal (fail-closed)"
            return self.result()

        # P06 market-first-leg only when the signal bar CLOSES inside the zone (a wick-only
        # touch stays a limit and can fill by P05 in the same bar) — red-team finding 5
        sb = bars[0]
        near = self.legs[0]
        in_zone = (sb[4] <= near.price) if self.direction == "LONG" else (sb[4] >= near.price)
        if in_zone:
            near.kind = "MARKET_AT_SIGNAL_CLOSE"

        # exactly-once instruction application: exact duplicate deliveries collapse (idempotency)
        seen, events = set(), []
        for e in sorted(self.c["events"], key=lambda e: (int(e["ts"]), int(e.get("message_id") or 0))):
            key = (e.get("message_id"), e["instruction_type"], str(e.get("pct")), str(e.get("scope")))
            if key not in seen:
                seen.add(key)
                events.append(e)
            else:
                self._log("DUPLICATE_EVENT_SKIPPED", rule="idempotency", message_id=e.get("message_id"),
                          detail={"instruction_type": e["instruction_type"]})
        expiry_ts = sig + 24 * 3600                            # P14/P16 24h expiry
        ei = 0
        self.state = "PROPOSED"

        for bar in bars:
            ts = bar[0]
            if self.state in ("CLOSED", "PAUSED_NEEDS_HUMAN_REVIEW"):
                break
            # 1) adverse-first stop/BE checks on existing position
            self._stop_checks(bar)
            # 2) fills (market leg fills on the signal bar; limits by mode)
            for leg in self.legs:
                if leg.kind == "MARKET_AT_SIGNAL_CLOSE" and ts != bars[0][0]:
                    continue
                if self._try_fill(leg, bar):
                    if self.state == "PROPOSED":
                        self.state = "LIVE"
                    # same-bar adverse re-check on the fresh fill (huge-bar case)
                    self._stop_checks(bar)
            # 3) instructions whose timestamp falls in this bar (grouped per message)
            batch = {}
            while ei < len(events) and int(events[ei]["ts"]) < ts + 60:
                e = events[ei]
                batch.setdefault(e.get("message_id") or 0, []).append(e)
                ei += 1
            for mid in sorted(batch):
                self._apply_message(batch[mid], bar)
            # 4) expiry of unfilled legs
            if ts >= expiry_ts:
                self._cancel_unfilled("P16_24H_EXPIRY", ts)
            # 5) flat after having been live, with nothing pending -> closed
            if self.state == "LIVE" and self._open_size() == 0 and ei >= len(events) \
                    and all(l.state != "PROPOSED" for l in self.legs):
                self.state = "CLOSED"
            self._prev_bar = bar

        if self.state == "LIVE":
            self.state = "OPEN_PENDING_DATA"
        if self.state == "PROPOSED":
            self.state = "NO_FILL" if any(l.state == "CANCELLED" for l in self.legs) \
                else "AWAITING_FILL_PENDING_DATA"
        return self.result()

    # ---- results --------------------------------------------------------------------
    def result(self):
        realized_usd = sum(((s.exit - s.entry) * self.sgn *
                            D(s.size.numerator) / D(s.size.denominator) for s in self.slices), D(0))
        last_close = self.bars[-1][4] if self.bars else None
        unreal = D(0)
        open_detail = []
        for leg in self._filled_legs():
            u = (last_close - leg.fill_price) * self.sgn * D(leg.open_size.numerator) / D(leg.open_size.denominator)
            unreal += u
            open_detail.append({"leg_id": leg.leg_id, "open_size": str(leg.open_size),
                                "entry": str(leg.fill_price), "mark": str(last_close),
                                "unrealized_pips_contrib": str(pips(u))})
        return {
            "setup_id": self.c["setup_id"], "lane": self.lane_key, "lane_name": self.lane["name"],
            "campaign_state": self.state, "paused_reason": self.paused_reason,
            "legs": [{"leg_id": l.leg_id, "price": str(l.price), "kind": l.kind, "state": l.state,
                      "fill_price": str(l.fill_price) if l.fill_price is not None else None,
                      "open_size": str(l.open_size), "be_price": str(l.be_price) if l.be_price else None,
                      "tags": l.tags} for l in self.legs],
            "slices": [{"leg_id": s.leg_id, "size": str(s.size), "entry": str(s.entry),
                        "exit": str(s.exit), "reason": s.reason, "bar_ts": s.bar_ts,
                        "message_id": s.message_id, "tags": s.tags} for s in self.slices],
            "realized_pips_per_unit": str(pips(realized_usd)),
            "unrealized_pips_per_unit": str(pips(unreal)) if open_detail else None,
            "open_position": open_detail or None,
            "average_entry": str(self._avg_entry()) if self._avg_entry() else None,
            "ambiguities": self.ambiguities,
            "transitions": self.transitions,
            "follow_through": ("PENDING_FOLLOW_THROUGH" if self.state in
                               ("OPEN_PENDING_DATA", "AWAITING_FILL_PENDING_DATA") else "COMPLETE_IN_WINDOW"),
        }


def run_campaign(campaign: dict, bars: list, constitution: dict):
    """Both lanes, deterministic. Lane A is ALWAYS the headline (never the more profitable one)."""
    out = {}
    for lane in ("LANE_A", "LANE_B"):
        out[lane] = FollowerEngine(campaign, bars, lane, constitution).run()
    out["headline_lane"] = "LANE_A"
    out["lane_b_disclaimer"] = ("POLICY_SENSITIVITY lane; documented alternates only; "
                                "NOT Farouk's actual result")
    return out
