"""
Author the June 25 fixture expected_truth — SECOND HELD-OUT blind-test fixture.

Locked BEFORE any extractor run (strict order). Same rules as June 24/26: text-only,
image/video-only -> NULL, .mov/empty -> no events, conditionals -> CONDITIONAL, members
-> context (sender gate), no invented legs. R-family rulings applied where they recur.

Martyn rulings (confirmed 2026-06-29):
  TP LADDER (msg 344) -> Option A: record tp1/tp2/tp3 as literal OPEN_LEG fields; TP4=4065
    and TP5="open" logged as a SCHEMA-LIMITATION note (published schema is tp1-3 only;
    TP5 has no numeric target -> NULL). Not dropped, not invented, schema NOT extended.
    A missing TP4/TP5 in the scorecard is the 3-wide schema, NOT an extractor miss.
  msg 345 "tp sl entry" -> PARTIAL_TP + MOVE_STOP (matches June 24 #328).

Locked uncertainty (the point of a held-out fixture):
  msg 349 "hold 25%" -> remaining_fraction NULL ("hold 25%" is NOT the allowlist phrase
    "leave 25%"; morphology/non-allowlist -> NULL).
  msg 351 "leave 10% open" -> remaining_fraction 0.10 (allowlisted DETERMINISTIC_CONVERSION;
    the first *successful* fraction conversion across the fixtures).
  campaign ends OPEN (~10% runner, no full CLOSE).
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "fixtures", "fixture_2026-06-25.json")
TRACK = "PROVIDER"
GOLD = "GOLD_BUY_2026-06-25"

LT, DC, UNS = "LITERAL_TEXT", "DETERMINISTIC_CONVERSION", "UNSUPPORTED"


def F(name, value, prov, **extra):
    d = {"value": value, "provenance": prov}
    d.update(extra)
    return {name: d}


def ev(event_type, quote, leg_ref=None, parent_ref=None, fields=None,
       association="CONFIRMED", note=None):
    e = {"event_type": event_type, "track": TRACK, "leg_ref": leg_ref, "parent_ref": parent_ref,
         "fields": fields or {}, "association_status": association, "evidence_quote": quote}
    if note:
        e["note"] = note
    return e


def merge(*fds):
    out = {}
    for fd in fds:
        out.update(fd)
    return out


# Single clear leg: leg-1 (the posted BUY signal).
TRUTH = {
    344: (GOLD, [ev("NEW_CAMPAIGN", "XAUUSD BUY 4016-4006"),
                 ev("OPEN_LEG", "XAUUSD BUY 4016-4006  SL 3970", leg_ref="leg-1",
                    fields=merge(
                        F("asset", "XAUUSD", LT), F("direction", "BUY", LT),
                        F("entry_low", "4006", LT), F("entry_high", "4016", LT),
                        F("stop", "3970", LT),
                        F("tp1", "4022", LT), F("tp2", "4027", LT), F("tp3", "4040", LT),
                        F("size", None, UNS, size_quality="NOT_STATED")),
                    note="RULING (Option A): tp1/tp2/tp3 literal. TP4=4065 and TP5='open' are "
                         "in the text but BEYOND the published tp1-3 schema -> logged as a "
                         "schema limitation (see known_limitations). TP5='open' has no numeric "
                         "target -> NULL. Size not stated -> NULL.")],
          "Campaign open: gold BUY leg-1 with a 5-target TP ladder (only tp1-3 are schema fields)."),
    345: (GOLD, [ev("PARTIAL_TP", "tp", leg_ref="leg-1",
                    note="RULING: 'tp sl entry' = partial TP (non-terminal) + SL->entry "
                         "(matches June 24 #328)."),
                 ev("MOVE_STOP", "sl entry", leg_ref="leg-1",
                    fields=F("stop_to", "entry", LT))], None),
    346: (GOLD, [], "EMPTY body -> image-only -> MEDIA_MISSING. No event."),
    347: (GOLD, [], "COMMENTARY — '300 pips' magnitude + emoji. No event."),
    348: (GOLD, [], "COMMENTARY — member-directed ('show profit in bragging-rights'), not an "
                    "account trade action."),
    349: (GOLD, [ev("HOLD_REMAINDER", "hold 25% for higher levels", leg_ref="leg-1",
                    fields=F("remaining_fraction", None, UNS),
                    note="RULING: 'hold 25%' is NOT the allowlist phrase 'leave 25%' -> "
                         "remaining_fraction NULL (non-allowlist/morphology). No 'take 75% off' "
                         "invented."),
                 ev("MOVE_STOP", "sl to entry", leg_ref="leg-1",
                    fields=F("stop_to", "entry", LT))], None),
    350: (GOLD, [], "RULING R5: '.mov Gold breakdown' screencast -> MEDIA_REFERENCE_ONLY. No "
                    "events, no numbers. (NB: 'Schermopname' Dutch -> auto media regex misses it.)"),
    351: (GOLD, [ev("PARTIAL_CLOSE", "take more profit leave 10% open", leg_ref="leg-1",
                    fields=F("remaining_fraction", 0.10, DC),
                    note="RULING: 'take more profit' = direct call to act (real event). "
                         "'leave 10%' IS in the allowlist -> remaining_fraction 0.10 "
                         "(DETERMINISTIC_CONVERSION). Leaves ~10% runner -> campaign OPEN.")],
          "Partial close leaving a 10% runner; campaign remains OPEN."),
}


def main():
    fx = json.load(open(FIXTURE, encoding="utf-8"))
    by_id = {int(m["message_id"]): m for m in fx["messages"]}

    applied = 0
    for mid, (campaign, events, notes) in TRUTH.items():
        m = by_id.get(mid)
        if m is None:
            raise SystemExit(f"message id {mid} not in fixture")
        m["expected_truth"] = {
            "manually_checked": True,
            "checked_by": "Martyn (held-out lock 2026-06-29)",
            "campaign": campaign,
            "events": events,
            "notes": notes,
        }
        applied += 1

    fx["authored_campaigns"] = {
        "authored_by": "Martyn (held-out lock 2026-06-29)",
        "immutable": True,
        "held_out_blind_test": True,
        "note": "Second held-out fixture. Locked BEFORE any extractor run. LLM must reproduce, "
                "never alter, this — INCLUDING the locked uncertainty.",
        GOLD: {
            "asset": "XAUUSD", "direction": "BUY", "track": TRACK,
            "legs": {
                "leg-1": {"entry_low": "4006", "entry_high": "4016", "stop": "3970",
                          "tp1": "4022", "tp2": "4027", "tp3": "4040",
                          "size": None, "size_quality": "NOT_STATED", "status": "OPEN",
                          "outcome": "Ends OPEN (~10% runner). Partial TP (345), hold-25% NULL "
                                     "(349), partial close leaving 10% (351, remaining=0.10)."},
            },
            "leg_count": 1,
            "needs_review": [],
            "closed_by": None,
            "final_state": {"campaign_status": "OPEN", "remaining_fraction": 0.10,
                            "full_close": False,
                            "note": "Final explicit fraction is 'leave 10% open' (351) -> 0.10 "
                                    "(allowlisted). Intermediate 'hold 25%' (349) stayed NULL."},
            "rulings": {
                "tp_ladder_optionA": "tp1-3 literal; TP4/TP5 schema-limitation (TP5 NULL)",
                "msg345": "tp sl entry = PARTIAL_TP + MOVE_STOP",
                "msg349_hold25": "non-allowlist -> remaining NULL",
                "msg351_leave10": "allowlisted -> remaining 0.10 (DETERMINISTIC_CONVERSION)",
                "media_350": "MEDIA_REFERENCE_ONLY, no events",
            },
            "known_limitations": [
                "SCHEMA COVERAGE: published fields are tp1/tp2/tp3 only. Msg 344's TP4=4065 and "
                "TP5='open' are real in the text but UNREPRESENTABLE in the 3-wide schema. A "
                "missing TP4/TP5 in the scorecard is the SCHEMA, NOT an extractor miss. TP5='open' "
                "has no numeric target -> NULL regardless.",
                "VALIDATOR MORPHOLOGY: allowlist is literal. 'hold 25%' != 'leave 25%' -> "
                "remaining NULL (349). 'leave 10%' DOES match -> 0.10 (351). These NULLs are the "
                "allowlist being literal, not the extractor failing.",
                "AUTO media_status may mis-read msg 350 (.mov) as TEXT_ONLY ('Schermopname' is "
                "Dutch); truth marks it MEDIA_REFERENCE_ONLY.",
            ],
        },
    }

    json.dump(fx, open(FIXTURE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    gold_events = sum(len(e) for c, e, _ in TRUTH.values() if c == GOLD)
    print(f"applied expected_truth to {applied} messages")
    print(f"gold events: {gold_events} | leg_count: 1 | final_state OPEN, remaining 0.10")
    print(f"349 remaining NULL | 351 remaining 0.10 | TP4/TP5 schema-limitation logged")


if __name__ == "__main__":
    main()
