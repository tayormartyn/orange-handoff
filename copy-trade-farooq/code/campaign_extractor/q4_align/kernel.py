"""
Deterministic Q4A alignment kernel. Pure Python — no LLM, no network, no invented fields.

align(signal, quotes, config) -> a result with a DELIVERY anchor (first valid quote after
listener_received_at) and an ACTIONABLE anchor (first valid quote after parsed_at). BUY is
evaluated against ASK, SELL against BID, inclusive range boundaries, Decimal at XAUUSD precision.
Every result is labelled OBSERVATION_ONLY / NOT_A_FILL / NOT_AN_OUTCOME and never claims an outcome.
"""
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from q4_config import load_config, ThresholdConfigMissing

# result codes
INSIDE, OUTSIDE, UNKNOWN = "INSIDE_ZONE", "OUTSIDE_ZONE", "UNKNOWN"
LABELS = {"assertion": "OBSERVATION_ONLY", "fill": "NOT_A_FILL", "outcome": "NOT_AN_OUTCOME"}
_BAD_FLAGS = ("MALFORMED", "NEGATIVE_SPREAD", "INCOMPLETE_NO_SIDES")


def _parse_ms(s):
    if s is None or str(s).strip() == "":
        return None
    t = str(s).strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(t)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _unknown(reason, **extra):
    d = {"result": UNKNOWN, "reason": reason}
    d.update(extra)
    return d


def normalise_signal(sig):
    """Validate + normalise a human-confirmed signal. Returns (ok, norm_or_reasoncode)."""
    if not sig.get("human_confirmed") is True:
        return False, "NOT_HUMAN_CONFIRMED"
    asset = str(sig.get("asset", "")).upper()
    if asset not in ("XAUUSD", "GOLD"):
        return False, "UNSUPPORTED_ASSET"
    direction = str(sig.get("direction", "")).strip().upper()
    if direction not in ("BUY", "SELL"):
        return False, "AMBIGUOUS_DIRECTION"
    lo, hi = sig.get("entry_low"), sig.get("entry_high")
    if lo is None or hi is None or str(lo).strip() == "" or str(hi).strip() == "":
        return False, "ENTRY_RANGE_MISSING"
    try:
        d_lo, d_hi = Decimal(str(lo)), Decimal(str(hi))
    except Exception:
        return False, "ENTRY_RANGE_INVALID"
    if d_lo <= 0 or d_hi <= 0:
        return False, "ENTRY_RANGE_INVALID"
    posted = _parse_ms(sig.get("telegram_posted_at"))
    received = _parse_ms(sig.get("listener_received_at"))
    parsed = _parse_ms(sig.get("parsed_at"))
    if received is None:
        return False, "CLOCK_ANOMALY"           # no anchorable listener_received_at
    if posted is not None and received < posted:
        return False, "CLOCK_ANOMALY"
    if parsed is not None and parsed < received:
        return False, "CLOCK_ANOMALY"
    return True, {
        "message_id": sig.get("source_telegram_message_id"),
        "evidence_ref": sig.get("source_evidence_ref"),
        "direction": direction,
        "orig_entry_low": str(lo), "orig_entry_high": str(hi),
        "entry_low": min(d_lo, d_hi), "entry_high": max(d_lo, d_hi),   # normalised deterministically
        "posted_ms": posted, "received_ms": received, "parsed_ms": parsed,
    }


def _session_integrity(quotes_sorted, symbol_id):
    """A session is healthy iff: contiguous unique sequences, symbol matches, broker ts
    non-decreasing, no duplicate (broker_ts,bid,ask), no integrity-flagged event."""
    seqs = [q["seq"] for q in quotes_sorted]
    if seqs != list(range(seqs[0], seqs[0] + len(seqs))):
        return False
    if any(q.get("symbol_id") not in (None, symbol_id) for q in quotes_sorted):
        return False
    bts = [q["broker_ts"] for q in quotes_sorted if q.get("broker_ts") is not None]
    if any(bts[i] < bts[i - 1] for i in range(1, len(bts))):
        return False
    keys = [(q.get("broker_ts"), q.get("raw_bid"), q.get("raw_ask")) for q in quotes_sorted]
    if len(keys) != len(set(keys)):
        return False
    for q in quotes_sorted:
        if any(b in (q.get("flags") or "") for b in _BAD_FLAGS):
            return False
    return True


def _age_ms(quote, prov_seq, mono_by_seq):
    if prov_seq is None or prov_seq not in mono_by_seq:
        return None
    return (quote["mono_ns"] - mono_by_seq[prov_seq]) / 1e6


def _align_anchor(anchor_ms, norm, quotes, cfg):
    sym = cfg["xauusd_symbol_id"]
    after = [q for q in quotes if q["wall_ms"] >= anchor_ms]
    if not after:
        return _unknown("NO_COVERAGE")
    first_after = min(after, key=lambda q: (q["wall_ms"], q["seq"]))
    session = first_after["session"]
    sq = sorted((q for q in quotes if q["session"] == session), key=lambda q: q["seq"])
    if not _session_integrity(sq, sym):
        return _unknown("SESSION_INTEGRITY_FAILURE", session=session)
    mono_by_seq = {q["seq"]: q["mono_ns"] for q in sq}

    delay_ms = first_after["wall_ms"] - anchor_ms
    if delay_ms > cfg["max_match_delay_ms"]:
        return _unknown("NO_FRESH_QUOTE", post_anchor_delay_ms=delay_ms)

    before = [q for q in sq if q["wall_ms"] < anchor_ms]
    last_before = max(before, key=lambda q: (q["wall_ms"], q["seq"])) if before else None
    if last_before is None:
        return _unknown("NO_COVERAGE", detail="no in-session quote before anchor")
    coverage_gap_ms = (first_after["mono_ns"] - last_before["mono_ns"]) / 1e6
    if coverage_gap_ms > cfg["coverage_gap_ms"]:
        return _unknown("NO_COVERAGE", surrounding_coverage_gap_ms=round(coverage_gap_ms, 3))

    q = first_after
    if q.get("symbol_id") not in (None, sym):
        return _unknown("SESSION_INTEGRITY_FAILURE", detail="symbol mismatch")
    if q["bid"] is None:
        return _unknown("MISSING_BID")
    if q["ask"] is None:
        return _unknown("MISSING_ASK")
    if q["spread"] is None or Decimal(str(q["spread"])) < 0:
        return _unknown("SESSION_INTEGRITY_FAILURE", detail="negative/absent spread")
    if any(b in (q.get("flags") or "") for b in _BAD_FLAGS):
        return _unknown("SESSION_INTEGRITY_FAILURE", detail="integrity-flagged quote")

    bid_age = _age_ms(q, q.get("bid_prov_seq"), mono_by_seq)
    ask_age = _age_ms(q, q.get("ask_prov_seq"), mono_by_seq)
    if bid_age is None or bid_age > cfg["stale_rejection_ms"]:
        return _unknown("STALE_BID", bid_source_age_ms=bid_age)
    if ask_age is None or ask_age > cfg["stale_rejection_ms"]:
        return _unknown("STALE_ASK", ask_source_age_ms=ask_age)

    digits = cfg["xauusd_digits"]
    quant = Decimal(1).scaleb(-digits)
    bid = Decimal(str(q["bid"])).quantize(quant, ROUND_HALF_UP)
    ask = Decimal(str(q["ask"])).quantize(quant, ROUND_HALF_UP)
    price = ask if norm["direction"] == "BUY" else bid          # BUY->ASK, SELL->BID
    inside = norm["entry_low"] <= price <= norm["entry_high"]   # inclusive
    return {
        "result": INSIDE if inside else OUTSIDE,
        "reason": None,
        "session": session,
        "matched_seq": q["seq"],
        "executable_side": "ASK" if norm["direction"] == "BUY" else "BID",
        "executable_price": str(price), "bid": str(bid), "ask": str(ask),
        "spread": str(Decimal(str(q["spread"])).quantize(quant, ROUND_HALF_UP)),
        "bid_source_age_ms": round(bid_age, 3), "ask_source_age_ms": round(ask_age, 3),
        "post_anchor_delay_ms": delay_ms,
        "surrounding_coverage_gap_ms": round(coverage_gap_ms, 3),
        "last_quote_before_anchor_wall_ms": last_before["wall_ms"],
        "first_quote_after_anchor_wall_ms": first_after["wall_ms"],
    }


def align(signal, quotes, config=None):
    """Top-level: validate signal, align at both anchors, attach timing + hard labels."""
    # config fail-closed
    try:
        cfg = load_config() if config is None else load_config(override=config)
    except ThresholdConfigMissing as e:
        return {"labels": LABELS, "delivery": _unknown("THRESHOLD_CONFIG_MISSING"),
                "actionable": _unknown("THRESHOLD_CONFIG_MISSING"), "config_error": str(e)}

    ok, norm = normalise_signal(signal)
    if not ok:
        # norm is a reason code (AMBIGUOUS_DIRECTION / ENTRY_RANGE_* / CLOCK_ANOMALY /
        # UNSUPPORTED_ASSET / NOT_HUMAN_CONFIRMED) — surface it verbatim on both anchors
        return {"labels": LABELS, "signal_error": norm,
                "delivery": _unknown(norm), "actionable": _unknown(norm)}

    delivery = _align_anchor(norm["received_ms"], norm, quotes, cfg)
    if norm["parsed_ms"] is None:
        actionable = _unknown("PARSE_TIME_MISSING", note="UNKNOWN_PARSE_TIME_MISSING")
    else:
        actionable = _align_anchor(norm["parsed_ms"], norm, quotes, cfg)

    timing = {
        "posted_to_received_ms": (norm["received_ms"] - norm["posted_ms"])
        if norm["posted_ms"] is not None else None,
        "received_to_parsed_ms": (norm["parsed_ms"] - norm["received_ms"])
        if norm["parsed_ms"] is not None else None,
        "received_to_delivery_quote_ms": delivery.get("post_anchor_delay_ms"),
        "parsed_to_actionable_quote_ms": actionable.get("post_anchor_delay_ms"),
    }
    return {
        "labels": LABELS, "config_version": cfg["config_version"],
        "signal": {"message_id": norm["message_id"], "evidence_ref": norm["evidence_ref"],
                   "direction": norm["direction"], "entry_low": str(norm["entry_low"]),
                   "entry_high": str(norm["entry_high"]),
                   "orig_entry_low": norm["orig_entry_low"], "orig_entry_high": norm["orig_entry_high"]},
        "delivery": delivery, "actionable": actionable, "timing": timing,
    }
