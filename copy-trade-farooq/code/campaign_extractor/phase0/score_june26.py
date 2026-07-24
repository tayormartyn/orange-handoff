"""
Score the LLM extractor against the LOCKED June 26 human-authored truth.

Pipeline (all real, deterministic): recorded blind-LLM candidates -> extractor parsing
-> validator -> event store -> reducer -> final gold campaign state. Then DIFF vs the
frozen expected_truth. The truth is NEVER modified here; the extractor must earn its match.

Campaign routing: events are grouped by asset (forward-filled from the most recent ENTRY),
so the BTC posts form a separate campaign and never enter the gold state — mirroring the
authored truth, without touching the locked reducer (which separates by track only).
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
from schema import Status, EventType

FIXTURE = os.path.join(HERE, "fixtures", "fixture_2026-06-26.json")
CANDS = os.path.join(HERE, "extraction",
                     sys.argv[1] if len(sys.argv) > 1 else "candidates_june26.json")

# canonical mutating/important event vocabulary for the diff
CANON = {
    "OPEN_LEG": "ENTRY", "NEW_CAMPAIGN": None, "HOLD_REMAINDER": None, "TP_LEVELS": None,
    "ENTRY": "ENTRY", "RE_ENTER": "RE_ENTER", "ADD": "ADD", "MOVE_STOP": "MOVE_STOP",
    "STOP_HIT": "STOP_HIT", "TP_HIT": "TP_HIT", "PARTIAL_TP": "PARTIAL_TP",
    "PARTIAL_CLOSE": "PARTIAL_CLOSE", "CLOSE": "CLOSE", "CONDITIONAL": "CONDITIONAL",
    "COMMENTARY": None,
}


def canon_set(event_types):
    out = set()
    for et in event_types:
        c = CANON.get(et, et)
        if c:
            out.add(c)
    return out


def asset_of(fields):
    a = fields.get("asset")
    if isinstance(a, dict):
        a = a.get("value")
    return (a or "").upper() or None


def main():
    fx = json.load(open(FIXTURE, encoding="utf-8"))
    by_id = {int(m["message_id"]): m for m in fx["messages"]}
    msgs = json.load(open(os.path.join(HERE, "extraction", "messages_june26.json"), encoding="utf-8"))
    raw_rec = json.load(open(CANDS, encoding="utf-8"))    # message_key -> {"candidates":[...]}
    recorded = {k: (v if isinstance(v, str) else json.dumps(v, ensure_ascii=False))
                for k, v in raw_rec.items()}

    # immutable evidence archive (read-only, from fixture raw_text)
    arc = ArchiveReader(mem_map={m["message_key"]: m["raw_text"] for m in msgs})

    # ---- 1. extract candidates (sender gate + parsing inside extract())
    client = ReplayClient(recorded)
    candidates = extract(msgs, client)

    # ---- 2. validate every candidate
    validated = [validate(c, arc) for c in candidates]
    verdict_counts = {}
    for v in validated:
        verdict_counts[v.status] = verdict_counts.get(v.status, 0) + 1

    # ---- 3. campaign routing by asset (forward-fill), then reduce GOLD through the spine
    key_to_id = {m["message_key"]: m["message_id"] for m in msgs}
    cur_asset = None
    gold_store = EventStore()
    routed = {"XAUUSD": [], "BTCUSD": [], "_unrouted": []}
    for v in validated:
        a = asset_of({n: {"value": f.value} for n, f in v.fields.items()})
        if v.event_type in (EventType.ENTRY.value, EventType.RE_ENTER.value) and a:
            cur_asset = a
        bucket = a or cur_asset
        if v.status in (Status.ACCEPTED.value, Status.NEEDS_REVIEW.value):
            routed.setdefault(bucket or "_unrouted", []).append(v)
        if bucket == "XAUUSD" and v.status == Status.ACCEPTED.value:
            gold_store.append(v)
    gold_state = reduce(gold_store.events())

    # ---- 4. event-level diff per message (truth vs validated extractor)
    ext_by_key = {}
    for v in validated:
        ext_by_key.setdefault(v.source_message_keys[0], []).append(v)

    diff_rows = []
    tp = fn = fp = 0   # matched, missed (truth-only), extra (extractor-only)
    for mid in sorted(by_id):
        m = by_id[mid]
        truth_types = [e["event_type"] for e in m["expected_truth"]["events"]]
        truth_c = canon_set(truth_types)
        ext_list = ext_by_key.get(m["message_key"], [])
        ext_c = canon_set([v.event_type for v in ext_list])
        matched = truth_c & ext_c
        missed = truth_c - ext_c
        extra = ext_c - truth_c
        tp += len(matched); fn += len(missed); fp += len(extra)
        if truth_c or ext_c:
            diff_rows.append({"mid": mid, "truth": sorted(truth_c), "extractor": sorted(ext_c),
                              "matched": sorted(matched), "missed": sorted(missed),
                              "extra": sorted(extra)})

    # ---- 5. field-level check on the gold OPEN_LEG (msg 352) — the ruling-#1 size case
    field_notes = []
    if 352 in ext_by_key.get("telegram:baseline:352", []) or True:
        ents = [v for v in ext_by_key.get("telegram:baseline:352", [])
                if v.event_type in ("ENTRY", "OPEN_LEG")]
        if ents:
            sf = ents[0].fields.get("size")
            field_notes.append(f"msg352 size after validation: value={sf.value if sf else 'MISSING'}"
                               f" (truth=NULL/QUALITATIVE_ONLY) -> "
                               f"{'MATCH' if (sf is None or sf.value is None) else 'DIVERGES'}")
        else:
            field_notes.append("msg352: extractor produced no ENTRY/OPEN_LEG -> DIVERGES (missed open)")

    # rejected candidates (deterministic guard in action)
    rejects = [(v.source_message_keys[0], v.event_type, v.reasons[0] if v.reasons else "")
               for v in validated if v.status == Status.REJECTED.value]

    report = {
        "model": client.model_id(),
        "candidates_proposed": len(candidates),
        "validator_verdicts": verdict_counts,
        "gold_legs_reduced": {lid: {"status": leg.status, "entry_low": leg.entry,
                                    "stop": leg.stop, "size_present": leg.entry is not None}
                              for lid, leg in gold_state.legs("XAUUSD").items()} if False else
                             {lid: vars(leg) for lid, leg in gold_state.tracks.get("PROVIDER", {}).items()},
        "event_diff_totals": {"matched": tp, "missed_truth_only": fn, "extra_extractor_only": fp},
        "field_notes": field_notes,
        "rejected_candidates": rejects,
        "btc_routed_separately": len(routed.get("BTCUSD", [])),
    }
    out_path = os.path.join(HERE, "extraction", "score_june26_report.json")
    json.dump({"report": report, "per_message_diff": diff_rows},
              open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # ---- human summary
    print("=" * 64)
    print(f"EXTRACTOR SCORING — June 26 (model: {client.model_id()})")
    print("=" * 64)
    print(f"candidates proposed : {len(candidates)}")
    print(f"validator verdicts  : {verdict_counts}")
    print(f"BTC routed separately: {report['btc_routed_separately']} events (excluded from gold)")
    print(f"event-type diff     : matched={tp}  missed(truth-only)={fn}  extra(extractor-only)={fp}")
    for n in field_notes:
        print("  -", n)
    print(f"\ngold campaign legs reduced from extractor (PROVIDER track):")
    for lid, leg in gold_state.tracks.get("PROVIDER", {}).items():
        print(f"  {lid}: status={leg.status} entry=({leg.entry}) stop={leg.stop} "
              f"size_q_flags={leg.flags} partial_tps={leg.partial_tp_count}")
    if rejects:
        print(f"\nrejected by validator ({len(rejects)}) — deterministic guard working:")
        for k, et, why in rejects[:12]:
            print(f"  {key_to_id.get(k,k)} {et}: {why}")
    print("\nper-message divergences (truth vs extractor):")
    for r in diff_rows:
        if r["missed"] or r["extra"]:
            print(f"  msg {r['mid']}: missed={r['missed']} extra={r['extra']} "
                  f"(truth={r['truth']} ext={r['extractor']})")
    print(f"\nfull report -> {os.path.relpath(out_path, HERE)}")


if __name__ == "__main__":
    main()
