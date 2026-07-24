"""
Parse a CONFIRMED TRADE_UPDATE (human-reviewed text) into one or more PROPOSED management intents.
Proposals only — no OCR output, keyword match or message may modify an order/position. A provider's
absolute lot instruction ("take 1 lot out") is captured LITERALLY and left UNMAPPED to our position.
"""
from __future__ import annotations
import re

# order matters: breakeven is checked before generic AMEND_STOP_LOSS
INTENT_RULES = [
    ("MOVE_SL_TO_BREAKEVEN", ("sl to be", "sl to breakeven", "sl to entry", "stop to entry",
                              "move sl to breakeven", "move stop to entry", "move sl to entry",
                              "breakeven", "break even", "risk free", "risk-free")),
    ("PARTIAL_CLOSE", ("take partial", "partial close", "close partial", "take some", "take some off",
                       "take 1 lot", "take one lot", "take profit on", "close half", "secure some",
                       "reduce", "take tp", "tp1", "tp 1", "take 1 lot out", "book partial", "scale out")),
    ("AMEND_TAKE_PROFIT", ("new tp", "move tp", "add tp", "tp to", "amend tp", "next target")),
    ("AMEND_STOP_LOSS", ("new sl", "sl to", "stop to", "move sl", "move stop", "trail sl", "trail stop")),
    ("CANCEL_PENDING_ORDER", ("cancel", "delete pending", "remove order", "cancel limit", "cancel order")),
    ("CLOSE_WORST_LEG", ("close the worst", "close worst", "cut the worst", "close worst entry",
                         "close bad entry")),
    ("HOLD_BEST_LEG", ("hold the best", "hold best", "keep the best", "hold best entry")),
]
_LITERAL_LOT = re.compile(r"take\s+(\d+(?:\.\d+)?)\s+lot", re.I)


def parse_update(text):
    t = (text or "").lower()
    hits = []
    for intent, kws in INTENT_RULES:
        snip = next((k for k in kws if k in t), None)
        if snip:
            hits.append({"intent": intent, "snippet": snip})
    # de-dup: if breakeven matched, drop a generic AMEND_STOP_LOSS
    if any(h["intent"] == "MOVE_SL_TO_BREAKEVEN" for h in hits):
        hits = [h for h in hits if h["intent"] != "AMEND_STOP_LOSS"]

    literal = _LITERAL_LOT.search(text or "")
    provider_literal_lots = float(literal.group(1)) if literal else None

    if not hits:
        return {"primary": "AMBIGUOUS_UPDATE", "intents": [], "reason": "NO_RECOGNISED_INTENT",
                "provider_literal_lots": provider_literal_lots, "is_composite": False}
    is_composite = len(hits) > 1
    return {"primary": "COMPOSITE_MANAGEMENT_PLAN" if is_composite else hits[0]["intent"],
            "intents": hits, "provider_literal_lots": provider_literal_lots,
            "is_composite": is_composite, "reason": "OK"}


# ---- exact OCR "take more profit" candidate extraction (proposals only; raw preserved) ----
_PARTIAL_MORE_KWS = ("take more profit", "secure more", "bank more", "take more", "take tp1",
                     "take tp2", "take tp 1", "take tp 2")
_SPACED_PRICE = r"(\d[\d ]*\.\d+)"
_LEG_WORD = {"one": 1, "two": 2, "three": 3, "four": 4}


def _strip_price(s):
    try:
        return float(str(s).replace(" ", ""))
    except ValueError:
        return None


def parse_ocr_update(raw_text):
    """Parse a raw OCR TRADE_UPDATE line into a PROPOSED partial-close candidate. The raw text is
    returned unchanged; a separate normalized candidate is produced. Nothing here closes anything."""
    raw = raw_text if raw_text is not None else ""
    t = raw.lower()
    flags = []

    pm = re.search(r"(\d+)\s*pips", t)
    pips = int(pm.group(1)) if pm else None

    action = next((k for k in _PARTIAL_MORE_KWS if k in t), None)

    lm = re.search(r"(sell|buy)\s+(one|two|three|four|\d+)\s+" + _SPACED_PRICE + r"\s+to\s+" + _SPACED_PRICE,
                   t, re.I)
    leg = entry = exit_p = leg_num = None
    if lm:
        leg_num = _LEG_WORD.get(lm.group(2).lower(), lm.group(2))
        leg = f"{lm.group(1).upper()}_{leg_num}"
        entry, exit_p = _strip_price(lm.group(3)), _strip_price(lm.group(4))
        if " " in lm.group(3).strip() or " " in lm.group(4).strip():
            flags.append("OCR_DIGIT_SPACING")

    price_pair = entry is not None and exit_p is not None
    # Rule 3: a price pair alone (no action language) must NEVER propose a close
    intent = "PARTIAL_CLOSE_CANDIDATE" if action else "AMBIGUOUS_UPDATE"
    movement = round(abs(entry - exit_p), 2) if price_pair else None

    flags.append("CLOSE_VOLUME_NOT_SPECIFIED")            # Rule 6
    if leg:
        flags.append("PROVIDER_LEG_NOT_YET_MAPPED")       # Rules 4/5
    if pips is not None:
        flags.append("PROVIDER_PIPS_NOT_BROKER_VERIFIED") # Rule 9

    normalized = None
    if lm and pips is not None:
        verb = lm.group(1).capitalize()
        normalized = f"{pips} pips — {action}. {verb} {leg_num}: {entry:.2f} to {exit_p:.2f}."
    elif action:
        normalized = f"{action}."

    return {
        "raw_text": raw,                                  # IMMUTABLE — never overwritten
        "normalized_candidate": normalized,
        "classification": "TRADE_UPDATE",
        "intent": intent,
        "provider_claimed_pips": pips,
        "provider_entry_candidate": entry,
        "provider_exit_candidate": exit_p,
        "provider_price_movement": movement,
        "provider_leg_candidate": leg,
        "provider_close_volume": "UNKNOWN",
        "price_pair_only": (price_pair and not action),
        "ambiguity_flags": flags,
        "instruction_vs_recap": "INSTRUCTION_VS_RECAP_REQUIRES_CONFIRMATION",   # Rule 7
    }
