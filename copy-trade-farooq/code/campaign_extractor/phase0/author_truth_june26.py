"""
Author the June 26 fixture expected_truth — HUMAN-AUTHORED GROUND TRUTH.

Martyn ruled on every event in a joint session; this script writes those rulings into
fixtures/fixture_2026-06-26.json (the per-message `expected_truth` slots) and records a
top-level `authored_campaigns` summary. This is the FIXED truth: the LLM candidate
extractor (built last) must reproduce it and must NEVER alter it.

Idempotent: reads the fixture, sets expected_truth by message_id, writes back. It does NOT
recompute or touch fixture_hash (that hash covers only the immutable archive-derived
evidence payload — message_key/content_hash/raw_text/sender/media_status — not the
human truth layer).

The four ruled judgment calls:
  352 size  -> NULL / QUALITATIVE_ONLY  (conflicting "LOW lot" + "half size", no convert)
  360 stop  -> STOP_HIT, realized_r NULL, likely breakeven (SL was at entry)
  357 tp1   -> PARTIAL_TP (NON-terminal, leg stays open)
  361/366   -> close-target association NEEDS_REVIEW (which leg is worst/best/first unknown)
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "fixtures", "fixture_2026-06-26.json")
TRACK = "PROVIDER"               # Farouk's own stated campaign = provider track
GOLD = "GOLD_SELL_2026-06-26"
BTC = "BTC_BUY_2026-06-26"

# provenance shorthands
LT, DC, UNS = "LITERAL_TEXT", "DETERMINISTIC_CONVERSION", "UNSUPPORTED"


def F(name, value, prov, **extra):
    d = {"value": value, "provenance": prov}
    d.update(extra)
    return {name: d}


def ev(event_type, quote, leg_ref=None, parent_ref=None, fields=None,
       association="CONFIRMED", note=None):
    e = {"event_type": event_type, "track": TRACK, "leg_ref": leg_ref,
         "parent_ref": parent_ref, "fields": fields or {}, "association_status": association,
         "evidence_quote": quote}
    if note:
        e["note"] = note
    return e


def merge(*field_dicts):
    out = {}
    for fd in field_dicts:
        out.update(fd)
    return out


# message_id -> (campaign, [events], notes)
TRUTH = {
    352: (GOLD, [ev("NEW_CAMPAIGN", "XAUUSD SELL 4078-4092"),
                 ev("OPEN_LEG", "XAUUSD SELL 4078-4092  SL4120", leg_ref="leg-1",
                    fields=merge(
                        F("asset", "XAUUSD", LT), F("direction", "SELL", LT),
                        F("entry_low", "4078", LT), F("entry_high", "4092", LT),
                        F("stop", "4120", LT),
                        F("size", None, UNS, size_quality="QUALITATIVE_ONLY")),
                    note="RULING #1: 'use a LOW lot size' + 'risk half size' conflict -> "
                         "size NULL; 'half size' NOT silently converted to 0.50.")],
          "Campaign open: gold SELL leg-1."),
    353: (GOLD, [ev("MOVE_STOP", "move sl to entry 100pips", leg_ref="leg-1",
                    fields=F("stop_to", "entry", LT),
                    note="SL moved to entry (breakeven protection).")], None),
    354: (GOLD, [], "COMMENTARY — sell rationale (H1/15m/5m OB, daily FVG). No event."),
    355: (GOLD, [ev("RE_ENTER", "Re-enter quarter size.", leg_ref="leg-2", parent_ref="leg-1",
                    fields=F("size", 0.25, DC),
                    note="'quarter size' -> 0.25 (allowlisted deterministic conversion).")],
          "Child re-entry leg-2 at quarter size."),
    356: (GOLD, [], "COMMENTARY — 'Small size' qualitative; NO number, NO new leg, does NOT "
                    "alter leg-2's 0.25."),
    357: (GOLD, [ev("PARTIAL_TP", "tp 1 again", leg_ref="leg-1",
                    note="RULING #3: 'tp 1' is a PARTIAL take-profit -> NON-terminal; leg "
                         "stays open. Banks part of the move on the open SELL position.")],
          "First partial TP."),
    358: (GOLD, [ev("MOVE_STOP", "sl to entry", leg_ref="leg-1",
                    fields=F("stop_to", "entry", LT))], None),
    359: (GOLD, [], "EMPTY body -> image-only post -> MEDIA_MISSING. No event."),
    360: (GOLD, [ev("STOP_HIT", "SL got hit again", leg_ref="leg-1",
                    fields=F("realized_r", None, UNS),
                    note="RULING #2: STOP_HIT, status STOPPED, realized_r NULL. Likely "
                         "BREAKEVEN — SL had been moved to entry (msgs 353 & 358) and msg "
                         "374 says stopped at entry. Do NOT assert a loss magnitude."),
                 ev("RE_ENTER", "XAUUSD SELL 4084-4094  SL4120", leg_ref="leg-3",
                    fields=merge(
                        F("asset", "XAUUSD", LT), F("direction", "SELL", LT),
                        F("entry_low", "4084", LT), F("entry_high", "4094", LT),
                        F("stop", "4120", LT),
                        F("size", None, UNS, size_quality="QUALITATIVE_ONLY")),
                    note="'low lot' -> size NULL. parent_ref null: specific parent leg not "
                         "stated. TWO events from one message; both cite message 360.")],
          "Stop (breakeven) + second re-entry leg-3 in the same message."),
    361: (GOLD, [ev("PARTIAL_CLOSE", "Closed the worst entry", leg_ref=None,
                    association="NEEDS_REVIEW",
                    note="RULING #4: which leg is 'the worst entry' is NOT determinable from "
                         "text -> association NEEDS_REVIEW. Do not guess."),
                 ev("HOLD_REMAINDER", "holding the best entry", leg_ref=None,
                    association="NEEDS_REVIEW",
                    note="RULING #4: which leg is 'the best entry' unknown -> NEEDS_REVIEW.")],
          "Closes one leg, holds another — leg identities unresolved."),
    362: (GOLD, [ev("MOVE_STOP", "move SL to entry", leg_ref=None, association="NEEDS_REVIEW",
                    fields=F("stop_to", "entry", LT)),
                 ev("CONDITIONAL", "If we get stopped out, I’ll look for another trade",
                    note="Conditional plan -> creates NO leg.")], None),
    363: (GOLD, [], "EMPTY body -> image-only -> MEDIA_MISSING. No event."),
    364: (GOLD, [], "COMMENTARY — 'Take profits... stick to the plan' (no distinct quantity)."),
    365: (GOLD, [ev("PARTIAL_TP", "90 pips take 2 tp's", leg_ref="leg-1",
                    fields=F("pips", "90", LT),
                    note="'90 pips' is profit MAGNITUDE (literal, informational) — NOT R, not "
                         "converted. 'take 2 tp's' = partial, NON-terminal.")],
          "Further partial TPs."),
    366: (GOLD, [ev("PARTIAL_CLOSE", "I closed My fist entry in profit", leg_ref=None,
                    association="NEEDS_REVIEW",
                    note="RULING #4: 'first entry' leg id not determinable -> NEEDS_REVIEW. "
                         "'in profit' = explicit close wording (realised), but leg unknown."),
                 ev("HOLD_REMAINDER", "Holding my best entry", leg_ref=None,
                    association="NEEDS_REVIEW")],
          "Closes 'first' entry in profit, holds 'best' — identities unresolved."),
    367: (GOLD, [], "COMMENTARY — '100+ pips' magnitude. No event."),
    368: (GOLD, [ev("CONDITIONAL", "if we get stopped, I’ll give another trade",
                    note="Conditional plan -> NO leg.")], None),
    369: (GOLD, [ev("PARTIAL_TP", "Take profit, guys, please.", leg_ref="leg-1",
                    note="Instruction to bank more profit; partial, non-terminal.")], None),
    370: (GOLD, [], "COMMENTARY — 'We did it again'. No event."),
    371: (GOLD, [], "EMPTY body -> image-only -> MEDIA_MISSING. No event."),
    372: (GOLD, [], "COMMENTARY — '150 pips' magnitude. No event."),
    373: (GOLD, [], "COMMENTARY — defers breakdown to YouTube. No event."),
    374: (GOLD, [ev("CLOSE", "I’ll exit and wait for the next one", leg_ref=None,
                    association="NEEDS_REVIEW",
                    note="Campaign CLOSE (closing event of the gold SELL campaign). Also "
                         "confirms stops were at ENTRY ('most of you got stopped out at "
                         "entry') -> supports RULING #2 breakeven. Closed leg is the held "
                         "'best' leg whose id is NEEDS_REVIEW.")],
          "Final close of the gold campaign."),
    375: (GOLD, [ev("MOVE_STOP", "place your SL at entry", leg_ref=None,
                    association="NEEDS_REVIEW", fields=F("stop_to", "entry", LT),
                    note="SL-to-entry advice for anyone still holding.")], None),
    376: (BTC, [ev("NEW_CAMPAIGN", "BTCUSD BUY"),
                ev("OPEN_LEG", "BTCUSD BUY  ENTRY 59800-59000  SL 57800", leg_ref="btc-leg-1",
                   fields=merge(
                       F("asset", "BTCUSD", LT), F("direction", "BUY", LT),
                       F("entry_low", "59000", LT), F("entry_high", "59800", LT),
                       F("stop", "57800", LT),
                       F("size", None, UNS, size_quality="QUALITATIVE_ONLY")))],
          "SEPARATE BTC campaign — EXCLUDED from the gold campaign (different asset)."),
    377: (None, [], "EMPTY body -> image-only -> MEDIA_MISSING. No event."),
    378: (None, [], "COMMENTARY — weekly wrap / risk-management note. No event, no campaign."),
    379: (BTC, [ev("TP_LEVELS", "Take Profit levels BTC  60.7k 61.0k 61.4k 62.0k 63.0k",
                   leg_ref="btc-leg-1",
                   note="Belongs to the SEPARATE BTC campaign. TP target levels (plan).")],
          "BTC TP levels — part of the BTC campaign, not gold."),
}


def main():
    with open(FIXTURE, encoding="utf-8") as f:
        fx = json.load(f)

    by_id = {}
    for m in fx["messages"]:
        by_id[int(m["message_id"])] = m

    applied = 0
    for mid, (campaign, events, notes) in TRUTH.items():
        m = by_id.get(mid)
        if m is None:
            raise SystemExit(f"message id {mid} not in fixture")
        m["expected_truth"] = {
            "manually_checked": True,
            "checked_by": "Martyn (joint session 2026-06-29)",
            "campaign": campaign,
            "events": events,
            "notes": notes,
        }
        applied += 1

    # top-level authored campaign summary (the fixed human truth)
    fx["authored_campaigns"] = {
        "authored_by": "Martyn (joint session 2026-06-29)",
        "immutable": True,
        "note": "Fixed human-authored ground truth. The LLM extractor must reproduce, "
                "never alter, this.",
        GOLD: {
            "asset": "XAUUSD", "direction": "SELL", "track": TRACK,
            "legs": {
                "leg-1": {"entry_low": "4078", "entry_high": "4092", "stop": "4120",
                          "size": None, "size_quality": "QUALITATIVE_ONLY",
                          "outcome": "STOPPED (likely breakeven, realized_r NULL); later "
                                     "managed/closed — see NEEDS_REVIEW associations"},
                "leg-2": {"size": 0.25, "parent": "leg-1", "note": "quarter-size re-entry"},
                "leg-3": {"entry_low": "4084", "entry_high": "4094", "stop": "4120",
                          "size": None, "size_quality": "QUALITATIVE_ONLY",
                          "parent": None},
            },
            "needs_review": ["worst/best/first entry close-target associations "
                             "(msgs 361, 366, 374, 375, 362)"],
            "closed_by": "msg 374 ('I'll exit and wait for the next one')",
            "rulings": {
                "msg352_size": "NULL / QUALITATIVE_ONLY (no convert)",
                "msg360_stop": "STOP_HIT, realized_r NULL, likely breakeven",
                "msg357_tp1": "PARTIAL_TP non-terminal",
                "msg361_366_assoc": "NEEDS_REVIEW",
            },
        },
        BTC: {"asset": "BTCUSD", "direction": "BUY", "excluded_from_gold": True,
              "note": "Separate campaign; must never attach to the gold campaign."},
    }

    with open(FIXTURE, "w", encoding="utf-8") as f:
        json.dump(fx, f, ensure_ascii=False, indent=2)

    # summary
    gold_events = sum(len(e) for c, e, _ in TRUTH.values() if c == GOLD)
    media_missing = sum(1 for c, e, n in TRUTH.values() if "MEDIA_MISSING" in (n or ""))
    needs_review = sum(1 for c, evs, n in TRUTH.values()
                       for x in evs if x["association_status"] == "NEEDS_REVIEW")
    print(f"applied expected_truth to {applied} messages")
    print(f"gold events: {gold_events} | media-missing msgs: {media_missing} | "
          f"NEEDS_REVIEW events: {needs_review}")


if __name__ == "__main__":
    main()
