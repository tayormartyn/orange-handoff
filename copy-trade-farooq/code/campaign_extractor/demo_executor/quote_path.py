"""
Prospective quote-path coverage from provider_message_timestamp -> current time. Answers whether the
recorded quote history is sufficient to decide entry-zone touch/traversal — and refuses to fabricate
continuous coverage from a single isolated quote. Pure/testable: quotes are injected as
[{'bid','ask','ts_ms'}].
"""
from __future__ import annotations

MAX_COVERAGE_GAP_MS = 60_000       # a gap larger than this leaves coverage INSUFFICIENT
MIN_POINTS = 2                     # one isolated quote is never continuous coverage


def coverage(quotes, *, start_ms, end_ms, max_gap_ms=MAX_COVERAGE_GAP_MS):
    pts = sorted([q for q in quotes if q.get("ts_ms") is not None and start_ms <= q["ts_ms"] <= end_ms],
                 key=lambda q: q["ts_ms"])
    if len(pts) < MIN_POINTS:
        return {"coverage_available": False, "reason": "ISOLATED_QUOTE_NOT_COVERAGE" if pts else "NO_QUOTES",
                "first_quote_ms": (pts[0]["ts_ms"] if pts else None),
                "last_quote_ms": (pts[-1]["ts_ms"] if pts else None), "points": len(pts),
                "max_gap_ms": None}
    gaps = [pts[i + 1]["ts_ms"] - pts[i]["ts_ms"] for i in range(len(pts) - 1)]
    max_gap = max(gaps) if gaps else 0
    # coverage must span from ~start to ~end with no oversized gap
    lead_gap = pts[0]["ts_ms"] - start_ms
    tail_gap = end_ms - pts[-1]["ts_ms"]
    ok = max_gap <= max_gap_ms and lead_gap <= max_gap_ms and tail_gap <= max_gap_ms
    return {"coverage_available": ok, "reason": None if ok else "QUOTE_PATH_UNVERIFIED",
            "first_quote_ms": pts[0]["ts_ms"], "last_quote_ms": pts[-1]["ts_ms"], "points": len(pts),
            "max_gap_ms": max_gap, "lead_gap_ms": lead_gap, "tail_gap_ms": tail_gap}


def zone_analysis(quotes, *, direction, entry_low, entry_high, start_ms, end_ms):
    """Consumes stored quotes; returns touch/traversal/entry-passed for the zone, only over covered
    quotes. Never claims a result when coverage is insufficient."""
    cov = coverage(quotes, start_ms=start_ms, end_ms=end_ms)
    lo, hi = min(entry_low, entry_high), max(entry_low, entry_high)
    pts = sorted([q for q in quotes if q.get("ts_ms") is not None and start_ms <= q["ts_ms"] <= end_ms],
                 key=lambda q: q["ts_ms"])
    touched = any(min(q["bid"], q["ask"]) <= hi and max(q["bid"], q["ask"]) >= lo for q in pts)
    below = any(max(q["bid"], q["ask"]) < lo for q in pts)
    above = any(min(q["bid"], q["ask"]) > hi for q in pts)
    d = (direction or "").upper()
    # "entry passed": price moved beyond the far side of the intended entry
    passed = (below and d == "BUY") or (above and d == "SELL")
    return {"coverage": cov, "zone_touched": touched if cov["coverage_available"] else None,
            "zone_traversed": (below and above) if cov["coverage_available"] else None,
            "entry_passed": passed if cov["coverage_available"] else None,
            "blocker": None if cov["coverage_available"] else "QUOTE_PATH_UNVERIFIED"}
