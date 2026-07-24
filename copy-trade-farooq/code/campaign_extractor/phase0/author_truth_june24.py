"""
Author the June 24 fixture expected_truth — HELD-OUT BLIND-TEST GROUND TRUTH.

Locked BEFORE any extractor run against it (strict order). Same rules as June 26:
text-only archive, image/video-only -> NULL, conditionals labelled CONDITIONAL, empty
bodies -> no events. Rulings R1-R5 (Martyn, confirmed 2026-06-29):

  R1  "taking 50%/90% off" -> PARTIAL_CLOSE, remaining_fraction = NULL. STRICT fail-closed:
      the validator allowlist phrases are literally "take 50% off"/"take 90% off"; the text
      says "tak-ING ... off", which is NOT a literal substring. These NULLs are the allowlist
      being LITERAL, not the extractor failing. Logged as a known morphology limitation so the
      later blind number is read correctly. (Allowlist is NOT widened now.)
  R2  "take another 25% off" -> 25% not in allowlist at all -> remaining NULL.
  R3  "second is Whaleroom" -> author ONE leg only; a second/Whaleroom entry is NEEDS_REVIEW,
      no invented leg.
  R4  BTC "waiting for a retest before entry" -> COMMENTARY, separate asset, NO leg, NO campaign.
  R5  ".mov GOLD BREAKDOWN" -> MEDIA_REFERENCE_ONLY, no events, no numbers.

Campaign ends OPEN (~10% runner, no explicit full CLOSE) — locked that way.

The uncertainty is LOCKED, not just the facts: remaining_fraction NULL and campaign OPEN are
asserted as truth so a later pass cannot quietly "improve" them into guessed numbers.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "fixtures", "fixture_2026-06-24.json")
TRACK = "PROVIDER"
GOLD = "GOLD_SELL_2026-06-24"

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


# Single clear leg this day: leg-1 (the posted SELL signal). R3: no second leg invented.
TRUTH = {
    327: (GOLD, [ev("NEW_CAMPAIGN", "XAUUSD SELL 4030-4045"),
                 ev("OPEN_LEG", "XAUUSD SELL 4030-4045  SL 4130", leg_ref="leg-1",
                    fields=merge(
                        F("asset", "XAUUSD", LT), F("direction", "SELL", LT),
                        F("entry_low", "4030", LT), F("entry_high", "4045", LT),
                        F("stop", "4130", LT),
                        F("size", None, UNS, size_quality="QUALITATIVE_ONLY")),
                    note="'HIGH RISK LOW LOT' -> size NULL (qualitative).")],
          "Campaign open: gold SELL leg-1."),
    328: (GOLD, [ev("PARTIAL_TP", "tp 1", leg_ref="leg-1",
                    fields=F("pips", "100", LT),
                    note="'tp 1' partial, NON-terminal. '100 pips' = magnitude, NOT R."),
                 ev("MOVE_STOP", "move sl to entry", leg_ref="leg-1",
                    fields=F("stop_to", "entry", LT))], None),
    329: (GOLD, [], "EMPTY body -> image-only -> MEDIA_MISSING. No event."),
    330: (GOLD, [], "COMMENTARY — execution clarification. RULING R3: 'second is Whaleroom' "
                    "is NOT a determinable leg -> NEEDS_REVIEW, NO second leg invented. Only "
                    "leg-1 (the posted signal) exists."),
    331: (GOLD, [], "COMMENTARY — '120 pisp' magnitude. No event."),
    332: (GOLD, [], "EMPTY body -> image-only -> MEDIA_MISSING. No event."),
    333: (GOLD, [], "COMMENTARY — sell rationale (H4 BOS, H1 nBOS, 3m/5m OB). No event."),
    334: (GOLD, [ev("PARTIAL_TP", "take tp 4", leg_ref="leg-1",
                    fields=F("pips", "200", LT),
                    note="partial TP, NON-terminal. '200 pips' magnitude, NOT R.")], None),
    335: (GOLD, [ev("CONDITIONAL",
                    "if I get stopped out at the initial entry, I’ll look to re-enter around the 4070–4080 zone",
                    note="RULING: conditional re-entry PLAN -> creates NO leg. The 4070-4080 "
                         "zone is a FUTURE/conditional level and is NOT extracted as an entry.")],
          "Conditional re-entry plan only."),
    336: (GOLD, [ev("PARTIAL_CLOSE", "im taking 50% off now", leg_ref="leg-1",
                    fields=F("remaining_fraction", None, UNS),
                    note="RULING R1: 'taking 50% off' does NOT literally match allowlist phrase "
                         "'take 50% off' -> remaining_fraction NULL (morphology, fail-closed). "
                         "Action is real; exact fraction unknown."),
                 ev("MOVE_STOP", "(sl to entry)", leg_ref="leg-1",
                    fields=F("stop_to", "entry", LT))], None),
    337: (GOLD, [], "EMPTY body -> image-only -> MEDIA_MISSING. No event."),
    338: (GOLD, [], "RULING R5: '.mov GOLD BREAKDOWN' screencast -> MEDIA_REFERENCE_ONLY. No "
                    "events, no numbers. (NB: auto media_status mis-read this as TEXT_ONLY "
                    "because 'Schermopname' is Dutch — English media regex missed it.)"),
    339: (GOLD, [ev("PARTIAL_CLOSE", "take another 25% off", leg_ref="leg-1",
                    fields=F("remaining_fraction", None, UNS),
                    note="RULING R2: '25% off' is NOT in the conversion allowlist -> "
                         "remaining_fraction NULL. '300 pips' magnitude, not R."),
                 ev("COMMENTARY", "Super proud of you guys!")],
          "Partial close + bragging-rights commentary in one message."),
    340: (GOLD, [], "COMMENTARY — celebration / @mentions. No event."),
    341: (None, [], "RULING R4: BTC 'waiting for a retest before entry' = NO actual entry -> "
                    "COMMENTARY, separate asset, NO leg, NO campaign."),
    342: (GOLD, [ev("PARTIAL_CLOSE", "take more off!!!", leg_ref="leg-1",
                    fields=F("remaining_fraction", None, UNS),
                    note="Direct call to act -> REAL event. No quantity stated -> "
                         "remaining_fraction NULL (never invented).")], None),
    343: (GOLD, [ev("PARTIAL_CLOSE", "taking 90% off", leg_ref="leg-1",
                    fields=F("remaining_fraction", None, UNS),
                    note="RULING R1: 'taking 90% off' does NOT literally match 'take 90% off' "
                         "-> remaining_fraction NULL (morphology). '650 pips' magnitude, not R. "
                         "Leaves ~10% runner -> campaign still OPEN (no full CLOSE).")],
          "Near-full partial close; campaign remains OPEN with a runner."),
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
        "note": "Held-out fixture. Locked BEFORE any extractor run. The LLM extractor must "
                "reproduce, never alter, this — INCLUDING the locked uncertainty.",
        GOLD: {
            "asset": "XAUUSD", "direction": "SELL", "track": TRACK,
            "legs": {
                "leg-1": {"entry_low": "4030", "entry_high": "4045", "stop": "4130",
                          "size": None, "size_quality": "QUALITATIVE_ONLY",
                          "status": "OPEN",
                          "outcome": "Ends OPEN (~10% runner). Partial TPs (tp1, tp4) + partial "
                                     "closes (50%/25%/'more'/90%), ALL remaining_fraction NULL."},
            },
            "leg_count": 1,
            "needs_review": ["second/Whaleroom entry existence (msg 330) — NO leg invented (R3)"],
            "closed_by": None,
            "final_state": {"campaign_status": "OPEN", "remaining_fraction": None,
                            "full_close": False},
            "rulings": {
                "R1_taking_morphology": "PARTIAL_CLOSE, remaining_fraction NULL (allowlist literal)",
                "R2_25pct": "not allowlisted -> NULL",
                "R3_second_entry": "one leg only; second = NEEDS_REVIEW",
                "R4_btc": "COMMENTARY, no leg, no campaign",
                "R5_mov": "MEDIA_REFERENCE_ONLY, no events",
            },
            "known_limitations": [
                "VALIDATOR MORPHOLOGY: allowlist matches literal 'take 50% off' / 'take 90% off' "
                "only; 'TAKING 50%/90% off' does NOT match -> remaining_fraction NULL. These "
                "NULLs are the allowlist being literal, NOT the extractor failing. Read the "
                "blind-test number accordingly.",
                "AUTO media_status mis-classified msg 338 (.mov) as TEXT_ONLY because "
                "'Schermopname' is Dutch; truth marks it MEDIA_REFERENCE_ONLY.",
            ],
        },
        "BTC": {"present": False, "note": "R4 — no BTC entry occurred (waiting for retest); "
                                          "no BTC campaign exists on this date."},
    }

    json.dump(fx, open(FIXTURE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    gold_events = sum(len(e) for c, e, _ in TRUTH.values() if c == GOLD)
    partial_closes = sum(1 for c, evs, _ in TRUTH.values() for x in evs
                         if x["event_type"] == "PARTIAL_CLOSE")
    print(f"applied expected_truth to {applied} messages")
    print(f"gold events: {gold_events} | partial_closes (all remaining NULL): {partial_closes}")
    print(f"leg_count locked: 1 | final_state: OPEN, remaining_fraction NULL")


if __name__ == "__main__":
    main()
