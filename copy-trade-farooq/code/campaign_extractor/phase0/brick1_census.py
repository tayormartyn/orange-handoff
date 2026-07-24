"""
BRICK 1 — Unresolved Campaign Census + Evidence-Bounded Materiality.

READ-ONLY DIAGNOSTIC. Runs the existing pipeline (recorded candidates -> validate ->
leg-resolve -> reduce) over the campaigns that exist through extraction (the 4 fixtures),
and reports what resolves vs what stays NEEDS_REVIEW, with a NAMED reason for every
unresolved event (no generic bucket), plus an evidence-bounded materiality read.

It does NOT:
  * modify any event, association, campaign state, expectancy, or baseline
  * touch the locked truths, the prompt, the archive, shadow DBs, or any scoring
It only reads the fixtures + recorded candidate files and writes 3 report files under
phase0/brick1/. Deterministic: identical inputs -> identical output hashes.

CORPUS LIMITATION (reported, not hidden): only the 4 extracted fixtures are censused.
Archive-wide materiality would require full-archive LLM extraction, which is NOT built.
"""
import csv
import hashlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from extractor import extract, ReplayClient
from validator import validate, ArchiveReader
from leg_resolver import resolve as resolve_legs, LEG_TARGETING
from reducer import reduce
from event_store import EventStore
from schema import Status, EventType

OUT = os.path.join(HERE, "brick1")
FIXTURES = [
    ("2026-06-17", "candidates_june17.json", "messages_20260617.json"),
    ("2026-06-24", "candidates_june24.json", "messages_20260624.json"),
    ("2026-06-25", "candidates_june25.json", "messages_20260625.json"),
    ("2026-06-26", "candidates_june26_v2.json", "messages_20260626.json"),
]


def _named_category(event_type, reason):
    """Every unresolved event gets a NAMED reason. No generic 'unexplained' bucket."""
    r = reason.lower()
    if "ranking" in r:
        if event_type in (EventType.CLOSE.value, EventType.PARTIAL_CLOSE.value):
            return "partial-close target unknown (worst/best/highest/lowest ranking)"
        if event_type == EventType.PARTIAL_TP.value:
            return "partial-TP target unknown (worst/best/highest/lowest ranking)"
        return f"{event_type.lower()} target unknown (worst/best/highest/lowest ranking)"
    if "same message opens a leg" in r:
        return "stop-hit leg unknown (price belongs to a co-declared new leg)"
    # multi-open-leg, no disambiguator
    if event_type == EventType.STOP_HIT.value:
        return "stop-hit leg unknown (multiple open legs, no disambiguating price)"
    if event_type in (EventType.CLOSE.value, EventType.PARTIAL_CLOSE.value):
        return "partial-close target unknown (multiple open legs, no disambiguating price)"
    if event_type == EventType.PARTIAL_TP.value:
        return "partial-TP target unknown (multiple open legs, no disambiguating price)"
    if event_type == EventType.MOVE_STOP.value:
        return "move-stop target unknown (multiple open legs, no disambiguating price)"
    if event_type == EventType.ADD.value:
        return "add target unknown (multiple open legs, no disambiguating price)"
    return f"other-named: {event_type.lower()} unresolved ({reason})"


def _asset_of(v):
    f = v.fields.get("asset")
    return (f.value.upper() if (f and not f.rejected and f.value) else None)


def run_fixture(date, cand_file, msg_file):
    fx = json.load(open(os.path.join(HERE, "fixtures", f"fixture_{date}.json"), encoding="utf-8"))
    msgs = json.load(open(os.path.join(HERE, "extraction", msg_file), encoding="utf-8"))
    raw = json.load(open(os.path.join(HERE, "extraction", cand_file), encoding="utf-8"))
    rec = {k: json.dumps(v, ensure_ascii=False) for k, v in raw.items()}
    arc = ArchiveReader(mem_map={m["message_key"]: m["raw_text"] for m in msgs})
    key_to_id = {m["message_key"]: m["message_id"] for m in msgs}

    validated = [validate(c, arc) for c in extract(msgs, ReplayClient(rec))]
    # forward-fill asset routing -> ordered gold bucket
    cur = None
    gold = []
    for v in validated:
        a = _asset_of(v)
        if v.event_type in (EventType.ENTRY.value, EventType.RE_ENTER.value) and a:
            cur = a
        if (a or cur) == "XAUUSD":
            gold.append(v)

    report = resolve_legs(gold, arc)
    store = EventStore()
    for v in gold:
        if v.status == Status.ACCEPTED.value:
            store.append(v)
    state = reduce(store.events())
    legs = state.tracks.get("PROVIDER", {})
    return date, gold, report, legs, key_to_id


def build():
    campaign_rows = []
    event_rows = []
    indeterminate_campaigns = []
    known_R_campaigns = []

    for date, cand_file, msg_file in FIXTURES:
        date_, gold, report, legs, key_to_id = run_fixture(date, cand_file, msg_file)
        leg_targeting = [v for v in gold if v.event_type in LEG_TARGETING]
        resolved = [v for v in leg_targeting if v.status == Status.ACCEPTED.value]
        needs_review = [v for v in leg_targeting if v.status == Status.NEEDS_REVIEW.value]
        leg_count = len(legs)
        style = "multi-leg" if leg_count >= 2 else "single-leg"

        if not needs_review:
            res_status = "FULLY_RESOLVED"
        elif resolved:
            res_status = "PARTIALLY_RESOLVED"
        else:
            res_status = "UNRESOLVED"

        statuses = {leg.status for leg in legs.values()}
        if statuses & {"STOPPED", "CLOSED", "TP"}:
            outcome = "CLOSED"
        elif needs_review and not (statuses & {"STOPPED", "CLOSED", "TP"}):
            outcome = "INDETERMINATE" if res_status == "UNRESOLVED" else "OPEN"
        else:
            outcome = "OPEN"

        # realised R: the pipeline computes none (fail-closed on entry-fill/exit/size).
        realised_R = "INDETERMINATE"
        realised_R_reason = ("no deterministically-supported realised R: entry-fill / exit / "
                             "size / fractions are NULL by fail-closed design")
        if realised_R == "INDETERMINATE":
            indeterminate_campaigns.append(f"{date}:gold")

        cid = f"{date}:gold:provider"
        campaign_rows.append({
            "date": date, "campaign_id": cid, "asset": "XAUUSD", "style": style,
            "leg_count": leg_count, "leg_targeting_events": len(leg_targeting),
            "resolved_events": len(resolved), "needs_review_events": len(needs_review),
            "resolution_status": res_status, "terminal_outcome": outcome,
            "realised_R": realised_R, "realised_R_reason": realised_R_reason,
            "month": date[:7],
        })
        for v in needs_review:
            rep = next((r for r in report if r.get("msg") == v.source_message_keys[0]
                        and r.get("event") == v.event_type), {})
            reason = rep.get("reason", "unresolved")
            event_rows.append({
                "date": date, "campaign_id": cid,
                "message_id": key_to_id.get(v.source_message_keys[0]),
                "message_key": v.source_message_keys[0], "event_type": v.event_type,
                "ambiguity_category": _named_category(v.event_type, reason),
                "raw_reason": reason,
            })

    # ---- write CSVs (sorted, no timestamps -> deterministic)
    os.makedirs(OUT, exist_ok=True)

    def write_csv(rows, fields, name):
        rows_sorted = sorted(rows, key=lambda r: tuple(str(r[f]) for f in fields))
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for r in rows_sorted:
            w.writerow(r)
        content = buf.getvalue()
        open(os.path.join(OUT, name), "w", encoding="utf-8", newline="").write(content)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    camp_fields = ["date", "month", "campaign_id", "asset", "style", "leg_count",
                   "leg_targeting_events", "resolved_events", "needs_review_events",
                   "resolution_status", "terminal_outcome", "realised_R", "realised_R_reason"]
    evt_fields = ["date", "campaign_id", "message_id", "message_key", "event_type",
                  "ambiguity_category", "raw_reason"]
    camp_hash = write_csv(campaign_rows, camp_fields, "unresolved_campaign_census.csv")
    evt_hash = write_csv(event_rows, evt_fields, "unresolved_event_census.csv")

    # ---- aggregates
    total_campaigns = len(campaign_rows)
    fully = sum(1 for r in campaign_rows if r["resolution_status"] == "FULLY_RESOLVED")
    partial = sum(1 for r in campaign_rows if r["resolution_status"] == "PARTIALLY_RESOLVED")
    unresolved = sum(1 for r in campaign_rows if r["resolution_status"] == "UNRESOLVED")
    total_ambiguous = len(event_rows)
    cat_counts = {}
    for e in event_rows:
        cat_counts[e["ambiguity_category"]] = cat_counts.get(e["ambiguity_category"], 0) + 1
    by_month = {}
    for r in campaign_rows:
        by_month.setdefault(r["month"], {"campaigns": 0, "unresolved": 0})
        by_month[r["month"]]["campaigns"] += 1
        if r["resolution_status"] != "FULLY_RESOLVED":
            by_month[r["month"]]["unresolved"] += 1

    # KNOWN-EVIDENCE-ONLY SCENARIO accounting (NOT a floor; bias direction unknown)
    included = len(known_R_campaigns)                       # campaigns with a known realised R
    excluded = total_campaigns - included                   # the unresolved/complex ones
    total_known_R = sum(known_R_campaigns) if known_R_campaigns else 0.0
    denominator = included                                  # campaign-level denominator
    mean_R = (total_known_R / denominator) if denominator else None
    mean_R_str = f"{mean_R:.4f}R" if mean_R is not None else "UNDEFINED (denominator = 0)"

    summary = f"""# BRICK 1 — Unresolved Campaign Census + Evidence-Bounded Materiality

READ-ONLY diagnostic. No event, association, campaign state, expectancy, or baseline was
modified. Deterministic: identical inputs reproduce identical output hashes.

## Corpus (and its limitation)
Censused: the {total_campaigns} campaigns that exist through the extraction pipeline —
the fixtures June 17 / 24 / 25 / 26. **This is NOT the full archive.** An archive-wide
materiality read would require full-archive LLM extraction, which is NOT built. Treat
these numbers as a pipeline-behaviour census on the available campaigns, not a
population-level edge estimate.

## Census
- Total campaigns: {total_campaigns}
- Fully resolved: {fully}
- Partially resolved: {partial}
- Unresolved: {unresolved}
- Total ambiguous (NEEDS_REVIEW leg-targeting) events: {total_ambiguous}

### Ambiguity categories (every event has a NAMED reason; no generic bucket)
""" + "".join(f"- {c}: {n}\n" for c, n in sorted(cat_counts.items())) + f"""
### By month
""" + "".join(f"- {m}: {v['campaigns']} campaigns, {v['unresolved']} not fully resolved\n"
              for m, v in sorted(by_month.items())) + f"""
### By campaign style
- single-leg: {sum(1 for r in campaign_rows if r['style']=='single-leg')}
- multi-leg: {sum(1 for r in campaign_rows if r['style']=='multi-leg')}

All ambiguous events resolve to a single multi-leg campaign (June 26). The single-leg
campaigns (June 17 / 24 / 25) fully resolve via the deterministic single-open-leg rule.

## MATERIALITY (evidence-bounded)

### KNOWN-EVIDENCE-ONLY SCENARIO (a SCENARIO — not a floor, not truth; bias direction UNKNOWN)
This is NOT a conservative floor. Excluding the unresolved campaigns can bias the result
UP or DOWN, and the direction is unknown, because the excluded set is not a random sample —
it is specifically the COMPLEX (multi-leg) campaigns. Reported strictly as a scenario:
- campaigns INCLUDED (known realised R): {included}
- campaigns EXCLUDED (unresolved / no known R): {excluded}
- total known realised R (sum over included): {total_known_R:.4f}R
- mean R over INCLUDED only: {mean_R_str}
- denominator used: {denominator} (campaign-level, = number of included campaigns)

With {included} included campaigns the scenario is UNCOMPUTABLE (denominator 0): there are
no fully-supported realised-R campaigns at all. This is BY DESIGN — the extractor
fail-closes on entry-fill price, exit price, size and fractions, so it emits auditable
campaign STRUCTURE (legs, events, terminal status) but no realised R. It does NOT yet emit
an edge number.

### LIKE-FOR-LIKE with +0.17R: NOT directly comparable (reconcile first)
The +0.17R baseline and this scenario differ on every axis of analysis:
| axis | +0.17R baseline | this scenario |
|------|-----------------|---------------|
| unit of analysis | per SIGNAL | per CAMPAIGN |
| population | signal-level history (price-aware system) | 4 extracted fixtures |
| denominator | signals scored | campaigns with known R ({included}) |
| scoring | all-in, price-derived R | fail-closed; R not computed |
Because population, denominator AND unit differ and cannot be reconciled here, the two are
**NOT directly comparable**. We therefore do NOT claim the edge moved or held. Any future
comparison MUST first reconcile population, denominator and unit (same population, same
unit, same scoring) before any number is set beside +0.17R.

### Materiality to the +0.17R signal-level baseline: **0R (structural)**
Separate from the comparability question: this campaign-extractor is PAPER / advisory and
never writes to the signal-level scoring path that produces +0.17R (EXECUTION_ENABLED=False).
The maximum defensible shift to +0.17R from ANY resolution of these unresolved campaigns is
**0R** — they cannot move that baseline at all, by architecture.

### Bounds for the {unresolved} unresolved (multi-leg) campaign
- lower bound: INDETERMINATE — affected leg / size / outcome unknown; no defensible lower
  numeric bound exists. (The known-evidence-only number is NOT substituted as a bound.)
- upper bound: INDETERMINATE — same; no defensible upper numeric bound exists.
- zero-for-unknown (SCENARIO ONLY, not truth, not a bound): treating every unknown as 0R
  contributes exactly 0R — an accounting convention, not a measured or bounded outcome.
- genuinely INDETERMINATE campaigns (no defensible numerical bound — unknown size /
  affected leg / outcome): {len(indeterminate_campaigns)} ({', '.join(indeterminate_campaigns)}).

NOTE: no false worst-case or best-case is manufactured. Where size, affected leg, or
outcome is unknown, the value is reported as INDETERMINATE, never as a number, and the
known-evidence-only scenario is never presented as a bound.

## Determinism / integrity
- unresolved_campaign_census.csv sha256: {camp_hash}
- unresolved_event_census.csv sha256: {evt_hash}
- No source DB, archive, shadow DB, expectancy, baseline, locked truth, or prompt was
  changed by this diagnostic.
"""
    open(os.path.join(OUT, "unresolved_summary.md"), "w", encoding="utf-8").write(summary)
    sum_hash = hashlib.sha256(summary.encode("utf-8")).hexdigest()

    return {"total_campaigns": total_campaigns, "fully": fully, "partial": partial,
            "unresolved": unresolved, "total_ambiguous": total_ambiguous,
            "cat_counts": cat_counts, "included": included, "excluded": excluded,
            "total_known_R": total_known_R, "mean_R": mean_R, "denominator": denominator,
            "indeterminate": len(indeterminate_campaigns),
            "camp_hash": camp_hash, "evt_hash": evt_hash, "sum_hash": sum_hash}


def main():
    r = build()
    print("BRICK 1 census written to phase0/brick1/")
    print(f"campaigns={r['total_campaigns']} fully={r['fully']} partial={r['partial']} unresolved={r['unresolved']}")
    print(f"ambiguous events={r['total_ambiguous']}")
    for c, n in sorted(r["cat_counts"].items()):
        print(f"  [{n}] {c}")
    print(f"KNOWN-EVIDENCE-ONLY scenario: included={r['included']} excluded={r['excluded']} "
          f"total_known_R={r['total_known_R']:.4f} mean_R={'UNDEFINED' if r['mean_R'] is None else round(r['mean_R'],4)} "
          f"denominator={r['denominator']}")
    print(f"indeterminate campaigns={r['indeterminate']}")
    print(f"HASHES campaign_csv={r['camp_hash'][:16]} event_csv={r['evt_hash'][:16]} summary={r['sum_hash'][:16]}")


if __name__ == "__main__":
    main()
