"""SHADOW CANDIDATE DETECTOR v0.1 — OFFLINE / OBSERVATION ONLY.

Marks POSSIBLE study candidates from a chronological list of v0.2-classified Farouk
events. It flags sequences that *might* be worth a future observation (shadow) study.
It NEVER creates a trade, an order, a permit/lease, or any execution object.

NON-NEGOTIABLE (enforced by construction):
  * Every candidate record is candidate-only. execution_allowed / broker_execution_allowed
    / qst_allowed / order_intent / risk_sizing_allowed are hard-wired False.
  * confidence is LOW or MEDIUM only (this detector never emits HIGH).
  * "direction_hint" is a bias descriptor, NOT an order side.
  * Runs offline over already-classified events. No I/O: no network, no broker/cTrader/
    QST import, no R2, no Worker deploy.
  * Does NOT promote Engulfing->A, ANY_ALERT clusters, or any single-event family
    (A alone / BPR tapped alone / Sweep alone) to a trade candidate.

This module changes nothing about NOT_INTEGRATION_READY. It only reads a list of dicts.
"""

import datetime as dt

DETECTOR_VERSION = "shadow_candidate_detector_v0_1"

# direction bias per event_type (bias descriptor only — never an order side)
_LONG_TYPES = {"SWEEP_LOW", "CHOCH_UP", "BULLISH_ENGULFING", "A_LONG", "A_PLUS"}
_SHORT_TYPES = {"SWEEP_HIGH", "CHOCH_DOWN", "BEARISH_ENGULFING", "A_SHORT"}


def _bias(event_type):
    if event_type in _LONG_TYPES:
        return "LONG"
    if event_type in _SHORT_TYPES:
        return "SHORT"
    return "NEUTRAL"


def _parse(ts):
    """Parse an ISO8601 UTC string (e.g. 2026-07-09T09:42:02.560Z) to aware datetime."""
    if not ts:
        return None
    s = ts.rstrip("Z")
    if "." in s:
        s = s[:26]
        fmt = "%Y-%m-%dT%H:%M:%S.%f"
    else:
        fmt = "%Y-%m-%dT%H:%M:%S"
    return dt.datetime.strptime(s, fmt).replace(tzinfo=dt.timezone.utc)


def _safe_flags():
    """The hard-wired safety block present on EVERY candidate record."""
    return {
        "candidate_only": True,
        "execution_allowed": False,
        "broker_execution_allowed": False,
        "qst_allowed": False,
        "order_intent": False,
        "risk_sizing_allowed": False,
    }


def _mk(candidate_type, seq, direction_hint, confidence, reason,
        disqualifiers=None, warnings=None, index=0):
    """Build one candidate record. confidence is forced to LOW/MEDIUM."""
    if confidence not in ("LOW", "MEDIUM"):
        confidence = "LOW"
    ev = [{"received_at_utc": e.get("received_at_utc"),
           "raw_text": e.get("raw_text"),
           "event_type": e.get("event_type"),
           "direction": e.get("direction"),
           "instrument": e.get("instrument"),
           "timeframe": e.get("timeframe")} for e in seq]
    rec = {
        "candidate_id": f"{candidate_type}-{index:04d}",
        "detector_version": DETECTOR_VERSION,
        "candidate_type": candidate_type,
        "window_start_utc": seq[0].get("received_at_utc"),
        "window_end_utc": seq[-1].get("received_at_utc"),
        "events_in_sequence": ev,
        "direction_hint": direction_hint,
        "confidence": confidence,
        "reason": reason,
        "disqualifiers": list(disqualifiers or []),
        "warnings": list(warnings or []),
    }
    rec.update(_safe_flags())
    return rec


def _has_opposite_A(events, i_start, i_end, want_dir):
    """True if an A signal of the OPPOSITE direction to want_dir appears in [i_start,i_end]."""
    opp = "A_SHORT" if want_dir == "LONG" else "A_LONG"
    for k in range(i_start, i_end + 1):
        if events[k].get("event_type") == opp:
            return True
    return False


def detect(events):
    """Detect shadow candidates + disqualified/noisy clusters over classified events.

    events: chronological list of v0.2-classified dicts. Returns
    {"candidates": [...], "disqualified": [...]}.
    """
    ev = sorted(events, key=lambda e: e.get("received_at_utc") or "")
    n = len(ev)
    times = [_parse(e.get("received_at_utc")) for e in ev]
    candidates = []
    counters = {}

    def nxt(ct):
        counters[ct] = counters.get(ct, 0)
        i = counters[ct]
        counters[ct] += 1
        return i

    def within(i, j, seconds):
        if times[i] is None or times[j] is None:
            return False
        return 0 <= (times[j] - times[i]).total_seconds() <= seconds

    # ---- A. ALIGNED_CHOCH_TO_A (CHoCH_UP->A_LONG / CHoCH_DOWN->A_SHORT within 15m) ----
    A_PAIR = {"CHOCH_UP": ("A_LONG", "LONG"), "CHOCH_DOWN": ("A_SHORT", "SHORT")}
    for i in range(n):
        et = ev[i].get("event_type")
        if et not in A_PAIR:
            continue
        want_a, hint = A_PAIR[et]
        for j in range(i + 1, n):
            if not within(i, j, 900):
                break
            if ev[j].get("event_type") == want_a:
                # aligned instrument/timeframe? CHoCH carries TF, A carries TF.
                same_it = (ev[i].get("instrument") == ev[j].get("instrument")
                           and ev[i].get("timeframe") == ev[j].get("timeframe")
                           and ev[i].get("instrument") is not None)
                contra = _has_opposite_A(ev, i, j, hint)
                disq = []
                warn = []
                if contra:
                    disq.append("contradictory opposite-A signal inside window")
                if not same_it:
                    warn.append("instrument/timeframe not confirmed identical")
                confidence = "MEDIUM" if (same_it and not contra) else "LOW"
                reason = (f"{et} followed by {want_a} within 15m "
                          f"({'aligned' if not contra else 'aligned type but contradicted'})")
                candidates.append(_mk("ALIGNED_CHOCH_TO_A", [ev[i], ev[j]], hint,
                                      confidence, reason, disq, warn, nxt("ALIGNED_CHOCH_TO_A")))
                break  # nearest aligned A only

    # ---- B. SWEEP_TO_CHOCH_CONTEXT (Sweep low->CHoCH_UP / Sweep high->CHoCH_DOWN <=30m) ----
    S_PAIR = {"SWEEP_LOW": ("CHOCH_UP", "LONG"), "SWEEP_HIGH": ("CHOCH_DOWN", "SHORT")}
    for i in range(n):
        et = ev[i].get("event_type")
        if et not in S_PAIR:
            continue
        want_c, hint = S_PAIR[et]
        for j in range(i + 1, n):
            if not within(i, j, 1800):
                break
            if ev[j].get("event_type") == want_c:
                candidates.append(_mk(
                    "SWEEP_TO_CHOCH_CONTEXT", [ev[i], ev[j]], hint, "LOW",
                    f"{et} followed by {want_c} within 30m (liquidity->structure context)",
                    [], ["context-only; sweep raw carries no timeframe (TIMEFRAME_MISSING)"],
                    nxt("SWEEP_TO_CHOCH_CONTEXT")))
                break

    # ---- C. BPR_TO_A_CONTEXT (BPR_TAPPED -> A_LONG/A_SHORT within 15m) ----
    for i in range(n):
        if ev[i].get("event_type") != "BPR_TAPPED":
            continue
        for j in range(i + 1, n):
            if not within(i, j, 900):
                break
            if ev[j].get("event_type") in ("A_LONG", "A_SHORT"):
                hint = "LONG" if ev[j].get("event_type") == "A_LONG" else "SHORT"
                candidates.append(_mk(
                    "BPR_TO_A_CONTEXT", [ev[i], ev[j]], hint, "LOW",
                    f"BPR_TAPPED followed by {ev[j].get('event_type')} within 15m (proximity context)",
                    [], ["BPR_TAPPED is directionless; proximity only, not a lead"],
                    nxt("BPR_TO_A_CONTEXT")))
                break

    # ---- D. CONTRADICTORY_CLUSTER (opposite direction hints within 15m) — disqualifier ----
    disqualified = []
    dcount = 0
    used_starts = set()
    for i in range(n):
        # collect the directional biases inside a 15m window starting at i
        grp = []
        for j in range(i, n):
            if not within(i, j, 900):
                break
            b = _bias(ev[j].get("event_type"))
            if b != "NEUTRAL":
                grp.append(j)
        biases = {_bias(ev[k].get("event_type")) for k in grp}
        if "LONG" in biases and "SHORT" in biases and len(grp) >= 3:
            # dedupe near-identical anchors (same first directional index)
            anchor = grp[0]
            if anchor in used_starts:
                continue
            used_starts.add(anchor)
            rec = _mk("CONTRADICTORY_CLUSTER", [ev[k] for k in grp], "NONE_AMBIGUOUS",
                      "LOW",
                      "opposite LONG and SHORT direction hints within 15m",
                      ["contradictory direction — NOT a candidate to follow"],
                      ["noisy cluster"], dcount)
            dcount += 1
            disqualified.append(rec)

    return {"candidates": candidates, "disqualified": disqualified}


def summary_counts(result):
    """Counts by candidate_type + disqualified count (descriptive only)."""
    by = {}
    for c in result["candidates"]:
        by[c["candidate_type"]] = by.get(c["candidate_type"], 0) + 1
    return {"by_candidate_type": by,
            "candidates_total": len(result["candidates"]),
            "disqualified_total": len(result["disqualified"])}


if __name__ == "__main__":
    import json
    import sys
    src = json.load(open(sys.argv[1], encoding="utf-8"))
    res = detect(src)
    print(json.dumps(summary_counts(res), indent=2))
