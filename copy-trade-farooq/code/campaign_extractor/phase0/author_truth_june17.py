"""
Author the June 17 fixture expected_truth — THIRD HELD-OUT blind-test fixture.

HEADLINE new property: the FIRST CLOSED campaign. Prior held-outs (24/25) ended OPEN;
June 17 closes via a breakeven stop-at-entry AFTER taking TPs (msg 266).

Locked BEFORE any extractor run. Same rules as 24/25/26. Martyn rulings (2026-06-29):
  msg 257 (standalone "TP1:4,328 TP2:4,332 TP3:4,345") -> TP_LEVELS literal targets, associated
    to leg-1. SAFE because there is exactly ONE open leg at that point (only attachment, not a
    guess). Multiple legs would have been NEEDS_REVIEW.
  msg 258 ("take tp on highest entry hold lowest entry") -> NEEDS_REVIEW association
    (June 26 worst/best/highest/lowest precedent — do not invent which fill is which).
  msg 266 ("sl entry hit after tp 2") -> STOP_HIT, realized_r NULL, likely breakeven (SL was
    moved to entry), CLOSES the campaign. Do not assert a loss/gain magnitude.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "fixtures", "fixture_2026-06-17.json")
TRACK = "PROVIDER"
GOLD = "GOLD_BUY_2026-06-17"

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


# Single leg: leg-1 (the posted BUY signal). Campaign CLOSES at msg 266.
TRUTH = {
    256: (GOLD, [ev("NEW_CAMPAIGN", "XAUUSD buy 4323-4315"),
                 ev("OPEN_LEG", "XAUUSD buy 4323-4315 sl 4295", leg_ref="leg-1",
                    fields=merge(
                        F("asset", "XAUUSD", LT), F("direction", "BUY", LT),
                        F("entry_low", "4315", LT), F("entry_high", "4323", LT),
                        F("stop", "4295", LT),
                        F("size", None, UNS, size_quality="NOT_STATED")),
                    note="Size not stated -> NULL.")],
          "Campaign open: gold BUY leg-1."),
    257: (GOLD, [ev("TP_LEVELS", "TP1 : 4,328   TP2 : 4,332   TP3 : 4,345", leg_ref="leg-1",
                    fields=merge(F("tp1", "4328", LT), F("tp2", "4332", LT), F("tp3", "4345", LT)),
                    note="RULING: standalone TP-targets message -> literal TP levels for leg-1. "
                         "SAFE association: exactly ONE open leg (only attachment, not a guess). "
                         "Source has thousands-commas (4,328) -> normalised 4328.")],
          "TP targets for leg-1, posted as a follow-up message."),
    258: (GOLD, [ev("PARTIAL_TP", "take tp on highest entry", leg_ref=None,
                    association="NEEDS_REVIEW",
                    note="RULING: 'highest entry' fill not determinable from text -> "
                         "NEEDS_REVIEW (June 26 precedent). Non-terminal."),
                 ev("HOLD_REMAINDER", "hold lowest entry", leg_ref=None,
                    association="NEEDS_REVIEW",
                    note="'lowest entry' fill not determinable -> NEEDS_REVIEW.")],
          "Partial TP on one fill, hold the other — fills not resolvable."),
    259: (GOLD, [ev("MOVE_STOP", "sl to entry", leg_ref="leg-1",
                    fields=F("stop_to", "entry", LT))], None),
    260: (GOLD, [], "COMMENTARY — describing a member following the rules ('he follow the rules "
                    "take tp and move sl'); '50 pips' magnitude. Not an account action."),
    261: (GOLD, [], "EMPTY body -> image-only -> MEDIA_MISSING. No event."),
    262: (GOLD, [ev("PARTIAL_TP", "take tp 2", leg_ref="leg-1",
                    fields=F("pips", "100", LT),
                    note="partial TP, non-terminal. '100 pips' magnitude, not R.")], None),
    263: (GOLD, [], "COMMENTARY — 'making bread and trading'. No event."),
    264: (GOLD, [ev("PARTIAL_TP", "tp 1 -2 hit", leg_ref="leg-1",
                    note="TP1 & TP2 reported hit -> partial TP (non-terminal). The 'show profit "
                         "in bragging-rights' part is member-directed COMMENTARY.")], None),
    265: (GOLD, [], "COMMENTARY — reason for the long (Asian low sweep, 5m FVG, BPR). No event."),
    266: (GOLD, [ev("STOP_HIT", "sl entry hit after tp 2", leg_ref="leg-1",
                    fields=F("realized_r", None, UNS),
                    note="HEADLINE: CLOSES the campaign. STOP_HIT, status STOPPED, realized_r "
                         "NULL. Likely BREAKEVEN — SL had been moved to entry (msg 259). Do NOT "
                         "assert a loss/gain magnitude. TPs were banked earlier (258/262/264).")],
          "Breakeven stop-at-entry after TPs -> campaign CLOSED."),
    267: (GOLD, [], "COMMENTARY — 'Gold is unpredictable... don't risk your profits'. No event."),
    268: (GOLD, [], "RULING R5: '.mov Gold Trade Breakdown' screencast -> MEDIA_REFERENCE_ONLY. "
                    "No events. (NB: 'Schermopname' Dutch -> auto media regex misses it.)"),
    269: (GOLD, [], "COMMENTARY — note about the indicator/education. No event."),
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
        "note": "Third held-out fixture. FIRST CLOSED campaign. Locked BEFORE any extractor run. "
                "LLM must reproduce, never alter, this — including the CLOSED outcome.",
        GOLD: {
            "asset": "XAUUSD", "direction": "BUY", "track": TRACK,
            "legs": {
                "leg-1": {"entry_low": "4315", "entry_high": "4323", "stop": "4295",
                          "tp1": "4328", "tp2": "4332", "tp3": "4345",
                          "size": None, "size_quality": "NOT_STATED", "status": "STOPPED",
                          "outcome": "TPs banked (258/262/264), SL->entry (259), then stopped at "
                                     "entry after TP2 (266) -> STOPPED/CLOSED. realized_r NULL "
                                     "(breakeven on remainder)."},
            },
            "leg_count": 1,
            "needs_review": ["msg 258 highest/lowest entry fills not resolvable"],
            "closed_by": 266,
            "final_state": {"campaign_status": "CLOSED", "closed_via": "breakeven stop-at-entry "
                            "after TPs", "closed_at_msg": 266, "realized_r": None,
                            "full_close": True},
            "rulings": {
                "msg257_tp_levels": "literal TP1-3 for leg-1; SAFE single-leg association",
                "msg258_highest_lowest": "NEEDS_REVIEW (fills not determinable)",
                "msg266_stop": "STOP_HIT breakeven, realized_r NULL, CLOSES campaign",
                "media_268": "MEDIA_REFERENCE_ONLY, no events",
            },
            "known_limitations": [
                "AUTO media_status may mis-read msg 268 (.mov) as TEXT_ONLY ('Schermopname' is "
                "Dutch); truth marks it MEDIA_REFERENCE_ONLY.",
                "CLOSED state requires leg association: msg 266 STOP_HIT needs a leg_ref to "
                "reduce. The extractor (refinement-3 OUT) emits no leg_ref -> the event is held "
                "NEEDS_REVIEW and will NOT reduce to CLOSED. Carrying CLOSED into reduced state "
                "is a refinement-3 (leg-association) dependency, by design.",
            ],
        },
    }

    json.dump(fx, open(FIXTURE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    gold_events = sum(len(e) for c, e, _ in TRUTH.values() if c == GOLD)
    print(f"applied expected_truth to {applied} messages")
    print(f"gold events: {gold_events} | leg_count: 1 | campaign CLOSED via msg 266")


if __name__ == "__main__":
    main()
