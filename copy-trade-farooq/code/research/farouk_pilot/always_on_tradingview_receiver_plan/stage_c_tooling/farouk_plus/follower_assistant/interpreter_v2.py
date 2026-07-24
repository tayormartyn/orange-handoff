"""Deterministic Farouk-gold message interpreter — the ONE canonical live interpretation
path for the Stage-1 follower lane (no LLM, no second source of truth: output is the same
XAU_F_SETUP record shape the engine's campaign_from_setup already consumes).

REVIEW-ONLY. Fail-closed everywhere: ambiguous direction/zone/stop -> NEEDS_HUMAN_REVIEW,
never a proposal. Only seascalperfarouk posts in the gold-trades channel enter this lane;
other providers, other channels, other assets, and indicator alerts are structurally
incapable of creating a campaign here.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal as D

FAROUK_GOLD_HEADER = re.compile(r"^seascalperfarouk Posted in .*gold-trades", re.IGNORECASE)
DIRECTION_RE = re.compile(r"\b(BUY|SELL)\b", re.IGNORECASE)
# hotfix v0.1: zone delimiter widened to hyphen / en-dash / em-dash / slash / 'to' (was hyphen+en-dash
# only). Handles 'Sell Zone: 4059–4069', '4059/4069', '4059 to 4069', '4059 — 4069'.
ZONE_RE = re.compile(r"(\d{4}(?:\.\d{1,2})?)\s*(?:[-–—/]|\bto\b)\s*(\d{4}(?:\.\d{1,2})?)", re.IGNORECASE)
# hotfix v0.1: stop-loss extraction widened to 'sl' / 'stop loss' / 'stop' labels (was 'sl' only).
# Handles 'Stop Loss: 4090', 'SL: 4090', 'Stop: 4090'. Still exactly-one-stop or fail closed.
SL_RE = re.compile(r"(?:\bsl\b|\bstop[\s-]*loss\b|\bstop\b)\s*:?\s*(?:at\s+|@\s*)?(\d{4}(?:\.\d{1,2})?)", re.IGNORECASE)
XAU_RE = re.compile(r"\bXAUUSD\b|\bGOLD\b", re.IGNORECASE)
PCT_RE = re.compile(r"take\s+(\d{1,2})\s*%\s*off", re.IGNORECASE)
# qualitative risk wording — preserved as TEXT only; never converted to lot/money/exposure
RISK_WORDING_RE = re.compile(r"high\s+risk|low\s+lot|small\s+lot|careful|risky", re.IGNORECASE)
# explicit "close X% leave/hold/keep/run Y%" scale-out morphology (hotfix scale-out v0.1). Captures
# the close-side pct (after close/take/bank) and the retain-side pct (after leave/hold/keep/run).
CLOSE_LEAVE_RE = re.compile(
    r"(?:close|take|bank)\s+(-?\d{1,3})\s*(?:%|percent)?[\s,]*(?:and\s+)?(?:leave|hold|keep|run\w*)\s+(-?\d{1,3})\s*(?:%|percent)?",
    re.IGNORECASE)
# explicit full-exit morphology (full-exit v0.1, observed live msg 45805 "full exit"). BOUNDED
# phrase list only — result cards, profit commentary and bare "X pips" claims NEVER match; a full
# exit is recognised only from these literal wordings, never inferred from screenshots or profit
# numbers. ("full close" already maps to FINAL_CLOSE below and keeps that existing terminal path.)
FULL_EXIT_RE = re.compile(
    r"\bfull(?:y)?\s+exit\b|\bexit(?:ed)?\s+fully\b|\bclose\s+all\b|\bclose\s+everything\b",
    re.IGNORECASE)
# CLOSE_PERCENTAGE_v0_1 (2026-07-17, observed live msg 45885 "close 100%"): narrowly bounded
# `close N%` management morphology. INTEGER N only (no decimals in v0.1), optional whitespace
# before '%', optional terminal punctuation (regex simply stops at '%'). The literal word
# 'close' followed by the integer and a percent sign is REQUIRED — a bare "100%", "we made
# 100%", "100 pips", "close 100 pips" and result-card/profit wording can never match. Only the
# authoritative Telegram management text is parsed; images/captions are never OCR'd.
CLOSE_PCT_VERSION = "CLOSE_PERCENTAGE_v0_1"
CLOSE_PCT_RE = re.compile(r"\bclose\s+(\d{1,3})\s*%", re.IGNORECASE)
# fail-closed net: close + malformed/decimal/signed number + '%' that the narrow rule refused
CLOSE_PCT_MALFORMED_RE = re.compile(r"\bclose\s+[-+]?[\d.,]+\s*%", re.IGNORECASE)

# ---- MORPHOLOGY_EXTENSION_v2 (D-020): pre-June single-price entry family + SL variants -------
MORPH_V2 = "MORPHOLOGY_EXTENSION_v2"
# entry-context direction words (LONG/SHORT admitted ONLY inside the single-price entry gate below;
# the zone-entry path keeps the original BUY/SELL-only DIRECTION_RE untouched)
DIR_WORD_RE = re.compile(r"\b(BUY|SELL|LONG|SHORT)\b", re.IGNORECASE)
ENTRY_PRICE_RE = re.compile(r"\bentry(?:\s+price)?\s*[:@]?\s*\(?\s*(\d{4}(?:\.\d{1,2})?)", re.IGNORECASE)
DIR_PRICE_RE = re.compile(r"\b(BUY|SELL)\s+(\d{4}(?:\.\d{1,2})?)\b", re.IGNORECASE)
# explicit entry SIGNAL required (never a bare direction word): instrument-adjacent direction,
# direction-on-gold phrasing, or opened-a-position phrasing
GOLD_DIR_ADJ_RE = re.compile(
    r"(?:\b(?:XAUUSD|GOLD)\b[^\S\n]{0,4}(?:BUY|SELL|LONG|SHORT)\b)"
    r"|(?:\b(?:BUY|SELL|LONG|SHORT)\b[^\S\n]{0,4}(?:XAUUSD|GOLD)\b)"
    r"|(?:\b(?:BUY|SELL|LONG|SHORT)\b(?:[^\S\n]+position)?[^\S\n]+on[^\S\n]+gold\b)"
    r"|(?:\bopened?\s+a\b[^\n]{0,30}\b(?:LONG|SHORT)\b[^\n]{0,25}\bgold\b)",
    re.IGNORECASE)
# A2 SL variants (timeless phrasings found in the 274-quarantine sample)
SL_TO_ENTRY_V2_RE = re.compile(
    # imperative context REQUIRED for the bare 'sl entry' form — retrospective references
    # ("if your SL entry got hit") must NOT mint a phantom instruction (45719 lesson).
    # v2.1 (D-028): tp-N-prefixed compound 'tp 1 sl entry' added — the tp clause supplies
    # the instruction context (live miss on msg 45937).
    r"stop[\s-]*loss\s+to\s+entry|stoploss\s+to\s+entry"
    r"|\b(?:move|put|set|place)\s+(?:your\s+)?sl\s+entry\b|%\s*,?\s*sl\s+entry\b"
    r"|\btp\s*\d\s*,?\s+sl\s+entry\b"
    r"|\b(?:sl|stop[\s-]*loss|stoploss)\s+to\s+enty\w*\b",
    re.IGNORECASE)
# v2.1 (D-028): leg-selective hold family + informational TP notes (per-clause completeness)
HOLD_LEG_RE = re.compile(r"\bhold\s+the\s+(lowest|highest)\s+entry\b", re.IGNORECASE)
TP_HIT_RE = re.compile(r"\btp\s*(\d)\s*(?:hit|✅|done)\b", re.IGNORECASE)
TP_NOTE_RE = re.compile(r"\b(?:next\s+)?tp\s+(?:is\s+)?(\d{4}(?:\.\d{1,2})?)\b", re.IGNORECASE)
REVISED_STOP_V2_RE = re.compile(
    r"(?:set|put|move)\s+(?:your\s+)?(?:sl|stop[\s-]*loss|stoploss)\s*(?:now\s+)?(?:at|to|@|:)\s*(\d{4}(?:\.\d{1,2})?)"
    r"|(?:\bsl\b|stop[\s-]*loss|stoploss)\s+now\s+(?:at|to|@)\s*(\d{4}(?:\.\d{1,2})?)",
    re.IGNORECASE)
TAKE_PCT_V2_RE = re.compile(r"take\s+(\d{1,2})\s*%(?!\s*off)", re.IGNORECASE)

# frozen pre-marks (mirrors guards.FROZEN_PRE_MARKS; comparison is annotation-only)
PRE_MARKS = {
    "PM-F001-SELL-4150-4184": ("SHORT", D("4150"), D("4184"), "2026-07-17T21:00:00Z"),
    "PM-F002-SUPPLY-4430-4480": ("SHORT", D("4430"), D("4480"), "2026-07-31T21:00:00Z"),
    "PM-F003-SELL-4250-4260": ("SHORT", D("4250"), D("4260"), "2026-07-19T21:00:00Z"),
    "PM-F004-DEMAND-3850-3863": ("LONG", D("3850"), D("3863"), "2026-07-31T21:00:00Z"),
}


def is_farouk_gold(raw_text: str | None) -> bool:
    """Channel+sender gate: literal first-line header only (never inferred from wording)."""
    if not raw_text:
        return False
    return bool(FAROUK_GOLD_HEADER.match(raw_text.strip().splitlines()[0]))


def classify(raw_text: str | None) -> dict:
    """-> {'kind': NOT_FAROUK_GOLD | ENTRY | MANAGEMENT | NEEDS_HUMAN_REVIEW | OTHER, ...}"""
    if not is_farouk_gold(raw_text):
        return {"kind": "NOT_FAROUK_GOLD"}
    # MORPHOLOGY_EXTENSION_v2 comma-price normalisation: '4,915' -> '4915' for DETECTION only
    # (digit,3-digits thousands pattern; raw evidence text is never modified anywhere else)
    text = re.sub(r"(\d),(\d{3})\b", r"\1\2", raw_text)
    directions = {m.upper() for m in DIRECTION_RE.findall(text)}
    zones = ZONE_RE.findall(text)
    sls = SL_RE.findall(text)
    looks_entry = bool(directions and (zones or sls))
    if looks_entry and len(zones) == 0 and XAU_RE.search(text) and len(sls) == 1:
        # MORPHOLOGY_EXTENSION_v2: zero zone ranges + one stop -> fall through to the
        # single-price entry gate below instead of dead-ending in review. Multi-zone and
        # all other ambiguity still fail closed in the original block.
        pass
    elif looks_entry:
        if not XAU_RE.search(text):
            # BUY/SELL numbers in gold-trades without an instrument word: refuse to guess
            return {"kind": "NEEDS_HUMAN_REVIEW", "why": "entry-shaped post without explicit XAUUSD/GOLD"}
        if len(directions) != 1:
            return {"kind": "NEEDS_HUMAN_REVIEW", "why": f"ambiguous direction {sorted(directions)}"}
        if len(zones) != 1:
            return {"kind": "NEEDS_HUMAN_REVIEW", "why": f"{len(zones)} zone ranges found (need exactly 1)"}
        if len(sls) != 1:
            return {"kind": "NEEDS_HUMAN_REVIEW",
                    "why": "missing stop" if not sls else "multiple stops"}
        a, b = D(zones[0][0]), D(zones[0][1])
        sl = D(sls[0])
        direction = "LONG" if directions == {"BUY"} else "SHORT"
        # stop must sit on the correct side of the zone, else fail closed
        if direction == "LONG" and not sl < min(a, b):
            return {"kind": "NEEDS_HUMAN_REVIEW", "why": "LONG stop not below zone"}
        if direction == "SHORT" and not sl > max(a, b):
            return {"kind": "NEEDS_HUMAN_REVIEW", "why": "SHORT stop not above zone"}
        rm = RISK_WORDING_RE.search(text)
        return {"kind": "ENTRY", "direction": direction,
                "zone_low": str(min(a, b)), "zone_high": str(max(a, b)), "sl": str(sl),
                "reentry_language": bool(re.search(r"re-?enter|another trade|again", text, re.I)),
                "risk_commentary_raw": (rm.group(0) if rm else None),
                "qualitative_risk_flag": ("HIGH_RISK_SOURCE_WORDING" if rm else None),
                "no_sizing_note": "qualitative risk wording preserved as text only; NO lot/money/exposure/authorization derived"}
    # ---- MORPHOLOGY_EXTENSION_v2: single-price / at-market entry family (runs BEFORE any
    # management typing — hard assertion D-020: an entry must NEVER be read as a stop-move).
    # Requires an explicit entry SIGNAL + gold instrument + exactly one stop price; the entry
    # price, if any, comes ONLY from a direction-adjacent price or an 'entry <price>' token.
    # NO ZONE IS EVER SYNTHESISED: unpriced entries return zone_low=zone_high=None flagged
    # AT_MARKET_UNPRICED (downstream contract: NO campaign; durable review record at the wire).
    if (XAU_RE.search(text) and len(sls) == 1 and not SL_TO_ENTRY_V2_RE.search(text)
            and not re.search(r"\bzone\b\s*[:@]", text, re.I)):
        # zone-LABELLED posts ("Sell Zone: 4059" with a missing second bound) stay in the
        # original fail-closed path — a labelled zone must parse as a full range, never be
        # reinterpreted as a single-price/at-market entry (hotfix negative fixture).
        mdp = DIR_PRICE_RE.search(text)
        mep = ENTRY_PRICE_RE.search(text)
        mga = GOLD_DIR_ADJ_RE.search(text)
        if mdp or mep or mga:
            dirs2 = {("LONG" if d.upper() in ("BUY", "LONG") else "SHORT")
                     for d in DIR_WORD_RE.findall(text)}
            if len(dirs2) != 1:
                return {"kind": "NEEDS_HUMAN_REVIEW",
                        "why": f"single-price entry family: ambiguous direction {sorted(dirs2)}",
                        "morphology": MORPH_V2}
            direction2 = dirs2.pop()
            sl2 = D(sls[0])
            price = D(mdp.group(2)) if mdp else (D(mep.group(1)) if mep else None)
            rm2 = RISK_WORDING_RE.search(text)
            base = {"kind": "ENTRY", "direction": direction2, "sl": str(sl2),
                    "reentry_language": bool(re.search(r"re-?enter|another trade|again", text, re.I)),
                    "risk_commentary_raw": (rm2.group(0) if rm2 else None),
                    "qualitative_risk_flag": ("HIGH_RISK_SOURCE_WORDING" if rm2 else None),
                    "no_sizing_note": "qualitative risk wording preserved as text only; NO lot/money/exposure/authorization derived",
                    "morphology": MORPH_V2}
            if price is not None and price != sl2:
                if direction2 == "LONG" and not sl2 < price:
                    return {"kind": "NEEDS_HUMAN_REVIEW", "why": "LONG stop not below single-price entry", "morphology": MORPH_V2}
                if direction2 == "SHORT" and not sl2 > price:
                    return {"kind": "NEEDS_HUMAN_REVIEW", "why": "SHORT stop not above single-price entry", "morphology": MORPH_V2}
                base.update({"zone_low": str(price), "zone_high": str(price),
                             "entry_pricing": "SINGLE_PRICE", "zone_degenerate": True,
                             "degenerate_zone_note": "single-price entry: all theoretical legs sit at "
                             "one price; EXCLUDE from leg-fill statistics (fill rate, near/mid/far, "
                             "entry-policy sensitivity) or stratify separately"})
                return base
            base.update({"zone_low": None, "zone_high": None,
                         "entry_pricing": "AT_MARKET_UNPRICED",
                         "unpriced_contract": "NO campaign may be created; wire emits a durable interpretation-review record; no zone is ever synthesised"})
            return base

    instructions = type_instructions(text)
    inv = [i for i in instructions if i["instruction_type"] == "INVALID_PERCENTAGE_PARTIAL"]
    if inv:
        # invalid/non-reconciling scale-out percentages -> fail closed to quarantine, never normalise
        return {"kind": "NEEDS_HUMAN_REVIEW",
                "why": f"invalid percentage partial (close {inv[0]['close_percentage']} + leave "
                       f"{inv[0]['retain_percentage']} = {inv[0]['percentage_sum']}, must be 100)"}
    if instructions:
        # v2.1 per-clause completeness (D-028): a message with typed instructions AND an
        # un-typed instruction-indicative clause fails ENTIRELY closed — never silent-partial.
        gaps = coverage_gaps(text, instructions)
        if gaps:
            return {"kind": "NEEDS_HUMAN_REVIEW",
                    "why": f"per-clause completeness: un-typed {'/'.join(gaps)} clause(s) "
                           f"alongside typed instructions (v2.1 hard fail-closed)",
                    "partial_instructions_withheld": [i["instruction_type"] for i in instructions]}
        return {"kind": "MANAGEMENT", "instructions": instructions}
    # safety net (red-team finding 9): stop/SL wording that produced NO typed instruction is
    # NOT commentary — a stale stop is the worst silent failure. Fail closed to review.
    if re.search(r"\bsl\b|\bstop\s?loss\b|\bstop\b", text, re.I):
        return {"kind": "NEEDS_HUMAN_REVIEW",
                "why": "stop-related wording with no recognized instruction pattern"}
    return {"kind": "OTHER"}


def type_instructions(text: str) -> list[dict]:
    """Deterministic 8C instruction typing (same taxonomy as the ratified fixtures)."""
    text = re.sub(r"(\d),(\d{3})\b", r"\1\2", text)  # v2 comma-price normalisation (detection only)
    t = text.lower()
    out = []
    if "close worst" in t:
        out.append({"instruction_type": "CLOSE_WORST"})
    if "hold best" in t or "hold the rest" in t:
        out.append({"instruction_type": "HOLD_BEST"})
    if re.search(r"\btp\s*1\b", t):
        out.append({"instruction_type": "TP1_TAKE"})
    if re.search(r"\btp\s*2\b", t):
        out.append({"instruction_type": "TP2_TAKE"})
    if "hold runner" in t or "let it run" in t:
        out.append({"instruction_type": "HOLD_RUNNER"})
    if re.search(r"cancel\s+(the\s+)?(limits?|orders?)", t):
        out.append({"instruction_type": "CANCEL_LIMITS"})
    if re.search(r"invalid|no longer valid|setup is off", t):
        out.append({"instruction_type": "INVALIDATION"})
    if (re.search(r"sl (to|at) entry|sl to break\s?even|\bsl to be\b|stop to entry|stop to break\s?even", t)
            or SL_TO_ENTRY_V2_RE.search(t)):
        out.append({"instruction_type": "SL_TO_ENTRY",
                    "scope": "lowest entry leg" if "lowest" in t else None})
    else:
        mrs = re.search(r"(?:move\s+)?\b(?:sl|stop)\b\s*(?:to|at|now|:)?\s*(\d{4}(?:\.\d{1,2})?)", t)
        mrs2 = REVISED_STOP_V2_RE.search(t)
        if mrs:
            out.append({"instruction_type": "REVISED_STOP", "new_sl": mrs.group(1)})
        elif mrs2:
            out.append({"instruction_type": "REVISED_STOP",
                        "new_sl": mrs2.group(1) or mrs2.group(2), "morphology": MORPH_V2})
    mz = re.search(r"(?:new zone|zone now|zone is now)\s*:?\s*(\d{4}(?:\.\d{1,2})?)\s*[-–]\s*(\d{4}(?:\.\d{1,2})?)", t)
    if mz:
        out.append({"instruction_type": "REVISED_ZONE"})
    # ---- COMPOUND_PRECEDENCE_v0_1 (2026-07-17) -------------------------------------------------
    # EXACTLY ONE size-reduction instruction may be emitted per message, chosen by specificity:
    #   close-X%-leave-Y%  >  close-N%  >  malformed-percentage net  >  take-X%-off  >  take-some.
    # Terminal (FINAL_CLOSE / EXPLICIT_FULL_EXIT) and CANCEL checks below ALWAYS still run, so a
    # compound "close 50% ... full exit" co-delivers both and the engine's terminal branch keeps
    # established precedence (terminal applies first and returns — never two reductions).
    reduction_emitted = False
    mcl = CLOSE_LEAVE_RE.search(text)
    if mcl:
        c_pct, r_pct = int(mcl.group(1)), int(mcl.group(2))
        if 0 < c_pct < 100 and 0 < r_pct < 100 and (c_pct + r_pct) == 100:
            out.append({"instruction_type": "EXPLICIT_PERCENTAGE_PARTIAL_CLOSE",
                        "close_percentage": c_pct, "retain_percentage": r_pct, "percentage_sum": c_pct + r_pct,
                        "pct": c_pct / 100.0,
                        "runner_requested": r_pct > 0, "quantity_base": "CURRENTLY_REMAINING_OPEN_FILLED_QUANTITY",
                        "raw_instruction": mcl.group(0)})
        else:
            out.append({"instruction_type": "INVALID_PERCENTAGE_PARTIAL",
                        "close_percentage": c_pct, "retain_percentage": r_pct, "percentage_sum": c_pct + r_pct,
                        "resolution": "QUARANTINE_FAIL_CLOSED", "raw_instruction": mcl.group(0)})
        reduction_emitted = True
    # CLOSE_PERCENTAGE_v0_1: `close N%`. N=100 -> EXPLICIT_FULL_EXIT (terminal; unfilled entries
    # cancel per ratified P14). 1<=N<100 -> CLOSE_PERCENTAGE_PARTIAL of the CURRENT REMAINING
    # open filled quantity (never the original campaign quantity). 0/>100/malformed -> quarantine.
    if not reduction_emitted:
        mcp = CLOSE_PCT_RE.search(text)
        if mcp:
            n = int(mcp.group(1))
            if n == 100:
                out.append({"instruction_type": "EXPLICIT_FULL_EXIT",
                            "size_basis": "ALL_CURRENTLY_REMAINING_OPEN_FILLED_SIZE",
                            "raw_instruction": mcp.group(0), "morphology": CLOSE_PCT_VERSION})
            elif 1 <= n < 100:
                out.append({"instruction_type": "CLOSE_PERCENTAGE_PARTIAL",
                            "close_percentage": n, "retain_percentage": 100 - n,
                            "percentage_sum": 100, "pct": n / 100.0,
                            "quantity_base": "CURRENTLY_REMAINING_OPEN_FILLED_QUANTITY",
                            "runner_requested": True,
                            "raw_instruction": mcp.group(0), "morphology": CLOSE_PCT_VERSION})
            else:
                out.append({"instruction_type": "INVALID_PERCENTAGE_PARTIAL",
                            "close_percentage": n, "retain_percentage": 100 - n,
                            "percentage_sum": n, "resolution": "QUARANTINE_FAIL_CLOSED",
                            "raw_instruction": mcp.group(0), "morphology": CLOSE_PCT_VERSION})
            reduction_emitted = True
    if not reduction_emitted:
        mm = CLOSE_PCT_MALFORMED_RE.search(text)
        if mm:
            out.append({"instruction_type": "INVALID_PERCENTAGE_PARTIAL",
                        "close_percentage": -1, "retain_percentage": -1, "percentage_sum": -1,
                        "resolution": "QUARANTINE_FAIL_CLOSED",
                        "raw_instruction": mm.group(0), "morphology": CLOSE_PCT_VERSION})
            reduction_emitted = True
    if not reduction_emitted:
        m = PCT_RE.search(t)
        m2 = TAKE_PCT_V2_RE.search(t)
        if m:
            out.append({"instruction_type": "TAKE_PCT_OFF", "pct": int(m.group(1)) / 100.0})
        elif m2 and SL_TO_ENTRY_V2_RE.search(t):
            # v2: 'take 90% sl entry' compound — pct co-delivered with the SL instruction only
            # when the SL variant proves instruction context (never bare 'take 90%' commentary)
            out.append({"instruction_type": "TAKE_PCT_OFF", "pct": int(m2.group(1)) / 100.0,
                        "morphology": MORPH_V2})
        elif re.search(r"take\s+some\s+off|take\s+profit", t):
            out.append({"instruction_type": "TAKE_PCT_OFF", "pct": None,
                        "note": "no percentage stated -> ratified 25% default applies"})
    if re.search(r"trade\s+closed|closed\s+in|close\s+(the\s+)?trade|full\s+close", t):
        out.append({"instruction_type": "FINAL_CLOSE"})
    mfe = FULL_EXIT_RE.search(text)
    if mfe:
        # terminal: close ALL currently remaining filled quantity; unfilled resting entries are
        # cancelled per the ratified constitution's terminal-cancellation rule (P14). Campaign
        # transitions to CLOSED only after unique valid campaign correlation upstream (wire).
        out.append({"instruction_type": "EXPLICIT_FULL_EXIT",
                    "size_basis": "ALL_CURRENTLY_REMAINING_OPEN_FILLED_SIZE",
                    "raw_instruction": mfe.group(0)})
    if re.search(r"\bcancel", t):
        out.append({"instruction_type": "CANCEL"})
    # ---- v2.1 leg-selective hold + informational notes (D-028) ------------------------------
    mhl = HOLD_LEG_RE.search(text)
    if mhl and not any(i["instruction_type"] in ("HOLD_BEST",) for i in out):
        # direction-dependent: resolved AT THE WIRE against the correlated campaign's direction
        # (LONG+LOWEST -> HOLD_BEST, SHORT+HIGHEST -> HOLD_BEST); anything else fails closed there.
        out.append({"instruction_type": "HOLD_LEG_SELECTIVE", "selector": mhl.group(1).upper(),
                    "resolution": "WIRE_RESOLVES_AGAINST_CAMPAIGN_DIRECTION_OR_FAILS_CLOSED"})
    for mth in TP_HIT_RE.finditer(text):
        out.append({"instruction_type": "TP_HIT_NOTE", "tp_index": int(mth.group(1)),
                    "informational": True,
                    "note": "report of a TP being hit — informational; never an engine instruction"})
    mtn = TP_NOTE_RE.search(text)
    if mtn:
        out.append({"instruction_type": "TP_LEVEL_NOTE", "level": mtn.group(1),
                    "informational": True,
                    "note": "stated TP level — informational; never an engine instruction"})
    return out


# ---- v2.1 per-clause completeness (D-028 hard architectural requirement) ---------------------
_COVERAGE_CHECKS = [
    (re.compile(r"\bsl\b|\bstop[\s-]*loss\b|\bstoploss\b|\bstop\b", re.I),
     {"SL_TO_ENTRY", "REVISED_STOP", "INVALIDATION"}, "stop"),
    (re.compile(r"\btp\s*\d\b|\btp\s+(?:is\s+)?\d{4}", re.I),
     {"TP1_TAKE", "TP2_TAKE", "TP_LEVEL_NOTE", "TP_HIT_NOTE"}, "tp"),
    (re.compile(r"\bhold\b", re.I),
     {"HOLD_BEST", "HOLD_RUNNER", "HOLD_LEG_SELECTIVE"}, "hold"),
    (re.compile(r"\bclose[sd]?\b", re.I),
     {"CLOSE_WORST", "FINAL_CLOSE", "EXPLICIT_FULL_EXIT", "CLOSE_PERCENTAGE_PARTIAL",
      "EXPLICIT_PERCENTAGE_PARTIAL_CLOSE", "INVALID_PERCENTAGE_PARTIAL"}, "close"),
    (re.compile(r"\bcancel", re.I), {"CANCEL", "CANCEL_LIMITS"}, "cancel"),
    (re.compile(r"\d{1,3}\s*%", re.I),
     {"TAKE_PCT_OFF", "CLOSE_PERCENTAGE_PARTIAL", "EXPLICIT_PERCENTAGE_PARTIAL_CLOSE",
      "INVALID_PERCENTAGE_PARTIAL", "EXPLICIT_FULL_EXIT"}, "percent"),
    # EXPLICIT_FULL_EXIT included: 'close 100%' IS the percent morphology's N=100 outcome
    # (caught by the F005 byte-identity gate during v2.1 build — msg 45885)
]


def coverage_gaps(text, instructions):
    """Any instruction-indicative token category with NO matching typed instruction is a gap.
    A gap fails the ENTIRE message closed (never silent-partial — msg 45937 lesson).
    Temporal idioms are stripped first: 'market close' (and the live 'maket close' typo) is a
    TIME reference, not an instruction clause — the only whitelisted phrase family."""
    scrub = re.sub(r"\b(?:market|maket)\s+close[sd]?\b", " ", text, flags=re.I)
    types = {i["instruction_type"] for i in instructions}
    return [name for pat, cover, name in _COVERAGE_CHECKS
            if pat.search(scrub) and not (types & cover)]


def score_deterministic(entry: dict, posted_at_iso: str) -> dict:
    """Frozen v0.2/v0.3 base scoring on the deterministically observable feature subset.
    reason_stated is NOT reliably machine-detectable -> False with an explicit review note.
    F2 requires pre-signal OHLC -> weight 0, PENDING_OHLC_RECHECK (same as fixtures)."""
    dt = datetime.fromisoformat(posted_at_iso.replace("Z", "+00:00")).astimezone(timezone.utc)
    after_1530 = (dt.hour, dt.minute) >= (15, 30)
    caution = bool(re.search(r"low\s+lot|small\s+lot|careful|dont\s+risk|don't\s+risk",
                             entry.get("_raw", ""), re.I))
    score = 1 + (-1 if after_1530 else 1) + (1 if caution else 0)     # attempt=1 assumed (+1)
    def label(sc):
        if sc <= -2: return "REJECT"
        if sc <= 0: return "WATCH"
        return "SHADOW_CANDIDATE_LOW" if sc == 1 else "SHADOW_CANDIDATE_MEDIUM"
    return {"v02_score": score, "v03_score": score,
            "v02_label": label(score), "v03_label": label(score),
            "features": {"attempt_number": 1, "first_attempt_flag": True, "re_entry_flag": False,
                         "after_1530z_flag": after_1530, "caution_language": caution,
                         "reason_stated_on_arrival": False, "claim_quality": "OK"},
            "note": "auto-scored on deterministic feature subset; reason_stated=False pending "
                    "human review; F2 zone-touch PENDING_OHLC_RECHECK (weight 0)"}


def pre_mark_compare(direction: str, zone_low: str, zone_high: str, posted_at_iso: str) -> dict:
    lo, hi = D(zone_low), D(zone_high)
    out = {}
    for pid, (pdir, plo, phi, pexp) in PRE_MARKS.items():
        if posted_at_iso > pexp:
            out[pid] = "EXPIRED"
        elif direction == pdir and not (hi < plo or lo > phi):
            out[pid] = "PARTIAL_MATCH" if not (lo >= plo and hi <= phi) else "MATCHED"
        else:
            out[pid] = "NOT_MATCHED"
    return out


def build_setup_record(setup_id: str, msg: dict, entry: dict) -> dict:
    """Minimal XAU_F_SETUP-shaped record (same field names campaign_from_setup reads),
    provenance-marked as live-wire output. Capture blocks not derivable deterministically
    stay UNKNOWN — never invented."""
    scoring = score_deterministic(dict(entry, _raw=msg["raw_text"]), msg["posted_at"])
    return {
        "record_type": "XAU_F_SETUP",
        "setup_id": setup_id, "revision": 1,
        "interpretation_source": "live_wire_deterministic_v0_1",
        "message_ids": [int(msg["id"])],
        "timestamp_utc": msg["posted_at"],
        "instrument": "XAUUSD", "direction": entry["direction"],
        "entry_zone": f"{entry['zone_low']}-{entry['zone_high']}",
        "sl": f"{entry['sl']} (posted follower stop; personal stop UNKNOWN; structural invalidation NOT STATED)",
        "tp_levels": [],
        "campaign_status_at_commit": "OPEN (auto-created at arrival)",
        "capture_timing": "LIVE_AT_ARRIVAL (listener capture; proposal auto-emitted by live wire)",
        "frozen_evidence_sha256": msg["raw_text_sha256"],
        "detector_v0_2": {"review_label": scoring["v02_label"]},
        "detector_v0_3": {"review_label": scoring["v03_label"]},
        "detector_v0_2_label": scoring["v02_label"], "detector_score": scoring["v03_score"],
        "scoring_features_used": scoring["features"],
        "auto_scoring_note": scoring["note"],
        "reentry_language_flag": entry.get("reentry_language", False),
        "management_timing_8c": {"instruction_events": []},
        "pre_mark_comparison": pre_mark_compare(entry["direction"], entry["zone_low"],
                                                entry["zone_high"], msg["posted_at"]),
        "media": [],
        "notes": "live-wire auto interpretation; richer capture blocks (ORB/POC/panel/8F/batch-B) "
                 "remain UNKNOWN pending session review — never invented",
        "review_only": True, "executable": False, "trade_ready": False, "observation_only": True,
    }
