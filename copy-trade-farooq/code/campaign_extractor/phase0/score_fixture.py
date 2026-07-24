"""
Generic extractor scorer: score recorded blind-LLM candidates against any locked
fixture truth. Pipeline is real and deterministic: candidates -> extractor parsing ->
validator -> event store -> reducer -> state, then a per-message event-type DIFF vs the
frozen expected_truth. The truth is NEVER modified.

Usage:  python score_fixture.py <YYYY-MM-DD> <candidates_file.json>
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from extractor import extract, ReplayClient
from validator import validate, ArchiveReader
from event_store import EventStore
from reducer import reduce
from leg_resolver import resolve as resolve_legs, LEG_TARGETING as LEG_TARGETING_TYPES
from schema import Status, EventType

DATE = sys.argv[1] if len(sys.argv) > 1 else "2026-06-26"
CAND_FILE = sys.argv[2] if len(sys.argv) > 2 else f"candidates_{DATE.replace('-', '')}.json"
FIXTURE = os.path.join(HERE, "fixtures", f"fixture_{DATE}.json")
CANDS = os.path.join(HERE, "extraction", CAND_FILE)
MSGS = os.path.join(HERE, "extraction", f"messages_{DATE.replace('-', '')}.json")

CANON = {
    "OPEN_LEG": "ENTRY", "NEW_CAMPAIGN": None, "HOLD_REMAINDER": None, "TP_LEVELS": None,
    "ENTRY": "ENTRY", "RE_ENTER": "RE_ENTER", "ADD": "ADD", "MOVE_STOP": "MOVE_STOP",
    "STOP_HIT": "STOP_HIT", "TP_HIT": "TP_HIT", "PARTIAL_TP": "PARTIAL_TP",
    "PARTIAL_CLOSE": "PARTIAL_CLOSE", "CLOSE": "CLOSE", "CONDITIONAL": "CONDITIONAL",
    "COMMENTARY": None,
}


def canon_set(types):
    return {CANON.get(t, t) for t in types if CANON.get(t, t)}


def asset_of(fields):
    a = fields.get("asset")
    if isinstance(a, dict):
        a = a.get("value")
    return (a or "").upper() or None


def main():
    fx = json.load(open(FIXTURE, encoding="utf-8"))
    by_id = {int(m["message_id"]): m for m in fx["messages"]}
    msgs = json.load(open(MSGS, encoding="utf-8"))
    raw_rec = json.load(open(CANDS, encoding="utf-8"))
    recorded = {k: (v if isinstance(v, str) else json.dumps(v, ensure_ascii=False))
                for k, v in raw_rec.items()}
    arc = ArchiveReader(mem_map={m["message_key"]: m["raw_text"] for m in msgs})

    client = ReplayClient(recorded)
    candidates = extract(msgs, client)
    validated = [validate(c, arc) for c in candidates]
    verdicts = {}
    for v in validated:
        verdicts[v.status] = verdicts.get(v.status, 0) + 1

    # campaign routing by asset (forward-fill) -> ordered gold bucket
    cur_asset = None
    gold_events = []
    btc_events = 0
    for v in validated:
        a = asset_of({n: {"value": f.value} for n, f in v.fields.items()})
        if v.event_type in (EventType.ENTRY.value, EventType.RE_ENTER.value) and a:
            cur_asset = a
        bucket = a or cur_asset
        if bucket and bucket != "XAUUSD" and v.status in (Status.ACCEPTED.value, Status.NEEDS_REVIEW.value):
            btc_events += 1
        if bucket == "XAUUSD":
            gold_events.append(v)

    # REFINEMENT 3: deterministic leg-association pass over the ordered gold campaign,
    # BEFORE reduction. Promotes NEEDS_REVIEW -> ACCEPTED only when unambiguous.
    resolution = resolve_legs(gold_events, arc)

    gold_store = EventStore()
    for v in gold_events:
        if v.status == Status.ACCEPTED.value:
            gold_store.append(v)
    gold_state = reduce(gold_store.events())

    ext_by_key = {}
    for v in validated:
        ext_by_key.setdefault(v.source_message_keys[0], []).append(v)

    diff_rows = []
    tp = fn = fp = 0
    for mid in sorted(by_id):
        m = by_id[mid]
        truth_c = canon_set([e["event_type"] for e in m["expected_truth"]["events"]])
        ext_c = canon_set([v.event_type for v in ext_by_key.get(m["message_key"], [])])
        matched, missed, extra = truth_c & ext_c, truth_c - ext_c, ext_c - truth_c
        tp += len(matched); fn += len(missed); fp += len(extra)
        if (missed or extra):
            diff_rows.append({"mid": mid, "truth": sorted(truth_c), "ext": sorted(ext_c),
                              "missed": sorted(missed), "extra": sorted(extra)})

    key_to_id = {m["message_key"]: m["message_id"] for m in msgs}
    rejects = [(key_to_id.get(v.source_message_keys[0]), v.event_type, v.reasons[0] if v.reasons else "")
               for v in validated if v.status == Status.REJECTED.value]

    # ---- refinement-3 resolution outcomes + WRONG-ASSOCIATION watch-check vs truth
    resolved = [r for r in resolution if r["outcome"] == "RESOLVED"]
    stayed_nr = [r for r in resolution if r["outcome"] == "NEEDS_REVIEW"]
    truth_ev_by_mid = {int(m["message_id"]): m["expected_truth"]["events"] for m in fx["messages"]}
    assoc_check = []
    for v in gold_events:
        if v.event_type not in LEG_TARGETING_TYPES or v.status != Status.ACCEPTED.value or not v.leg_ref:
            continue
        mid = key_to_id.get(v.source_message_keys[0])
        tev = [e for e in truth_ev_by_mid.get(mid, []) if (CANON.get(e["event_type"], e["event_type"])
               == CANON.get(v.event_type, v.event_type))]
        truth_leg = tev[0].get("leg_ref") if tev else None
        truth_assoc = tev[0].get("association_status") if tev else None
        if truth_leg:
            verdict = "CORRECT" if truth_leg == v.leg_ref else "WRONG"
        elif truth_assoc == "NEEDS_REVIEW":
            verdict = "RESOLVED_BEYOND_TRUTH"
        else:
            verdict = "NO_TRUTH_MATCH"
        assoc_check.append({"mid": mid, "event": v.event_type, "resolved_leg": v.leg_ref,
                            "truth_leg": truth_leg, "truth_assoc": truth_assoc, "verdict": verdict})
    wrong = [a for a in assoc_check if a["verdict"] == "WRONG"]

    out = {"date": DATE, "candidates_file": CAND_FILE, "model": client.model_id(),
           "candidates": len(candidates), "verdicts": verdicts,
           "event_diff": {"matched": tp, "missed_truth_only": fn, "extra_ext_only": fp},
           "btc_or_other_asset_events_excluded_from_gold": btc_events,
           "gold_legs": {lid: vars(leg) for lid, leg in gold_state.tracks.get("PROVIDER", {}).items()},
           "leg_resolution": {"resolved": resolved, "stayed_needs_review": stayed_nr,
                              "association_check": assoc_check, "wrong_associations": wrong},
           "rejected": rejects, "divergences": diff_rows}
    json.dump(out, open(os.path.join(HERE, "extraction", f"score_{DATE}_report.json"), "w",
                        encoding="utf-8"), ensure_ascii=False, indent=2)

    print("=" * 64)
    print(f"EXTRACTOR SCORING — {DATE}  (model: {client.model_id()}, file: {CAND_FILE})")
    print("=" * 64)
    print(f"candidates proposed : {len(candidates)}")
    print(f"validator verdicts  : {verdicts}")
    print(f"non-gold-asset events excluded from gold: {btc_events}")
    print(f"event-type diff     : matched={tp}  missed(truth-only)={fn}  extra(ext-only)={fp}")
    print(f"\nREFINEMENT-3 leg association: {len(resolved)} resolved, {len(stayed_nr)} stayed NEEDS_REVIEW")
    for r in resolved:
        print(f"  RESOLVED  msg {key_to_id.get(r['msg'], r['msg'])}  {r['event']} -> {r['leg']} ({r['method']})")
    for r in stayed_nr:
        print(f"  stays NR  msg {key_to_id.get(r['msg'], r['msg'])}  {r['event']}  ({r['reason']})")
    print(f"  WRONG associations: {len(wrong)}  {'<-- INVESTIGATE' if wrong else '(none)'}")
    for a in assoc_check:
        if a["verdict"] != "CORRECT":
            print(f"    {a['verdict']}: msg {a['mid']} {a['event']} -> {a['resolved_leg']} "
                  f"(truth leg={a['truth_leg']} assoc={a['truth_assoc']})")
    print(f"\ngold legs reduced from extractor (PROVIDER track):")
    for lid, leg in gold_state.tracks.get("PROVIDER", {}).items():
        print(f"  {lid}: status={leg.status} entry=({leg.entry}) stop={leg.stop} "
              f"remaining={leg.remaining_fraction} flags={leg.flags} partial_tps={leg.partial_tp_count}")
    if rejects:
        print(f"\nrejected by validator ({len(rejects)}):")
        for k, et, why in rejects[:12]:
            print(f"  {k} {et}: {why}")
    print(f"\nper-message divergences (truth vs extractor):")
    for r in diff_rows:
        print(f"  msg {r['mid']}: missed={r['missed']} extra={r['extra']} "
              f"(truth={r['truth']} ext={r['ext']})")
    if not diff_rows:
        print("  (none — perfect event-type match)")


if __name__ == "__main__":
    main()
