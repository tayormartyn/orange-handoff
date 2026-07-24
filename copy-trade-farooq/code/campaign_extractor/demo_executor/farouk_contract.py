"""
FAROUK SIGNAL INTERPRETATION CONTRACT (versioned, deterministic, FAIL-CLOSED). Interprets provider
instructions — it never invents or improves a trading decision. Ties together classification (intent
precedence), shorthand extraction, OCR normalization + material-change detection, contradiction
detection, TTL, quote-path/health, and deduplication into one decision. A false negative (human
review) is always preferred to a false positive (an executable proposal). Nothing here constructs or
sends a broker action.
"""
from __future__ import annotations
import re

import config as CFG
import ocr_normalize
import contradiction as CON
import signal_ttl as TTL
import quote_path as QP
import idempotency as ID
import cancel_intent as CANCEL


def _ocr():
    """ocr_adapter lives in the console package; import it path-aware + cache."""
    global _OCR
    try:
        return _OCR
    except NameError:
        import os
        import sys
        _console = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "paper_loop", "console")
        if _console not in sys.path:
            sys.path.insert(0, _console)
        import ocr_adapter as _oa
        _OCR = _oa
        return _OCR


def _result_card(text):
    return _ocr().result_card(text)


def _oa_classify(text, lines):
    return _ocr().classify(text, lines)

CONTRACT_VERSION = CFG.FAROUK_INTERPRETATION_CONTRACT_VERSION
PRECEDENCE = ("TRADE_RESULT", "CANCEL_PENDING", "TRADE_UPDATE", "NEW_SIGNAL", "UNKNOWN")
ACTIVE_QUOTE_STATE = "QUOTES_ACTIVE"

_INSTRUMENTS = {"gold": "XAUUSD", "xauusd": "XAUUSD", "xau/usd": "XAUUSD", "xau usd": "XAUUSD", "xau": "XAUUSD"}
_OTHER_INSTRUMENTS = {"btcusd": "BTCUSD", "btc": "BTCUSD", "bitcoin": "BTCUSD", "ethusd": "ETHUSD",
                      "eth": "ETHUSD", "xagusd": "XAGUSD", "silver": "XAGUSD", "nasdaq": "NAS100",
                      "us30": "US30", "eurusd": "EURUSD", "gbpusd": "GBPUSD"}
_DIR = {"buy": "BUY", "long": "BUY", "sell": "SELL", "short": "SELL"}
_MGMT = {
    "MOVE_SL_BREAKEVEN": ("be", "breakeven", "break even", "move sl to entry", "move stop to entry", "sl to be"),
    "PARTIAL_CLOSE": ("secure some", "take partial", "take half", "close half", "take some profit", "partial close"),
    "FULL_CLOSE": ("close trade", "take everything", "close all", "full close"),
    "HOLD_NO_ACTION": ("hold runner", "hold the runner", "let it run", "hold"),
}


def _dirs(t):
    return [_DIR[m.lower()] for m in re.findall(r"\b(buy|sell|long|short)\b", t, re.I)]


def _instruments(t):
    found = []
    for tbl in (_INSTRUMENTS, _OTHER_INSTRUMENTS):
        for k, v in tbl.items():
            if re.search(r"\b" + re.escape(k) + r"\b", t, re.I) and v not in found:
                found.append(v)
    return found


def extract_fields(text):
    t = text or ""
    instruments = _instruments(t)
    directions = _dirs(t)
    instrument = instruments[0] if instruments else None
    direction = directions[0] if directions else None

    order_type = None
    m = re.search(r"\b(buy|sell)\s*(limit|stop)\b", t, re.I)
    if m:
        order_type = (m.group(1).upper() + "_" + m.group(2).upper())

    entry_low = entry_high = None
    zone_reversed = False
    z = re.search(r"(?:entry|enter|zone|from)?\D{0,8}(\d{3,5}(?:\.\d+)?)\s*(?:-|–|/|to)\s*(\d{3,5}(?:\.\d+)?)", t, re.I)
    if z:
        a, b = float(z.group(1)), float(z.group(2))
        zone_reversed = a > b                       # written high-low => malformed (not silently fixed)
        entry_low, entry_high = min(a, b), max(a, b)
    else:
        s = re.search(r"(?:entry|enter|@)\D{0,6}(\d{3,5}(?:\.\d+)?)", t, re.I)
        if s:
            entry_low = entry_high = float(s.group(1))

    stops = [float(x) for x in re.findall(r"(?:sl|stop\s*loss|stoploss|\bstop\b)\D{0,5}(\d{3,5}(?:\.\d+)?)", t, re.I)]
    stop = stops[0] if stops else None

    targets = [float(x) for x in re.findall(r"(?:tp\d?|target|take\s*profit)\D{0,5}(\d{3,5}(?:\.\d+)?)", t, re.I)]

    return {"instrument": instrument, "direction": direction, "order_type": order_type,
            "entry_low": entry_low, "entry_high": entry_high, "stop": stop, "targets": targets,
            "zone_reversed": zone_reversed,
            "all_instruments": instruments, "all_directions": directions, "all_stops": stops}


def map_management(text):
    tl = (text or "").lower()
    if CANCEL.detect_cancel(text)[0]:
        return "CANCEL_PENDING"
    for plan, phrases in _MGMT.items():
        if any(p in tl for p in phrases):
            # a partial-close plan combined with breakeven wording
            if plan == "PARTIAL_CLOSE" and any(p in tl for p in _MGMT["MOVE_SL_BREAKEVEN"]):
                return "PARTIAL_CLOSE_AND_BREAKEVEN"
            return plan
    if any(w in tl for w in ("take one out", "take 1 out", "reduce", "trim", "take out")):
        return "UNKNOWN_UPDATE"                     # ambiguous quantity -> blocks
    return None                                     # no management wording at all


def classify_intent(raw_text, ocr_text=None):
    src = ocr_text or raw_text or ""
    rc = _result_card(src)
    oa_cls = _oa_classify(src, [])[0]
    if rc is not None or oa_cls == "TRADE_RESULT":
        return "TRADE_RESULT"
    if CANCEL.detect_cancel(raw_text or src)[0]:
        return "CANCEL_PENDING"
    if oa_cls == "TRADE_UPDATE" or map_management(src) is not None:
        return "TRADE_UPDATE"
    f = extract_fields(src)
    if f["instrument"] and f["direction"] and (f["entry_low"] is not None) and f["stop"] is not None:
        return "NEW_SIGNAL"
    return "UNKNOWN"


def interpret(*, raw_text, ocr_text=None, provider_ts_ms=None, ingestion_ts_ms=None, ocr_ts_ms=None,
              now_ms, quote=None, quote_path=None, quote_health_state=ACTIVE_QUOTE_STATE,
              existing_signals=None, matched_position=None, targets_optional=True,
              material_confirmed=False):
    """The full deterministic interpretation. Returns a decision dict; fail-closed on any doubt."""
    src = ocr_text or raw_text or ""
    norm = ocr_normalize.normalize(src)
    normalized = norm["normalized_text"]
    mat = ocr_normalize.scan_material_corrections(src, normalized)
    material_unconfirmed = mat["any_material"] and not material_confirmed

    intent = classify_intent(raw_text, ocr_text)
    fields = extract_fields(normalized)
    blockers = []
    warnings = []
    reasons = [f"intent={intent} by precedence {'>'.join(PRECEDENCE)}"]

    # ---- TRADE_RESULT: replay-only, never actionable ----
    if intent == "TRADE_RESULT":
        return _decision(intent, fields, normalized, raw_text, norm, mat,
                         flags=["COMPLETED_TRADE_RESULT", "REPLAY_VALIDATION_ONLY", "NOT_ACTIONABLE_SIGNAL"],
                         blockers=["NOT_ACTIONABLE_SIGNAL"], reasons=reasons + ["completed movement + P&L"],
                         execution_eligible=False, human_review=False, may_create_proposal=False,
                         provider_ts_ms=provider_ts_ms, now_ms=now_ms)

    # quote-health gate applies to any actionable intent
    if quote_health_state != ACTIVE_QUOTE_STATE:
        blockers.append("QUOTE_HEALTH_NOT_ACTIVE:" + str(quote_health_state))

    if material_unconfirmed:
        blockers.append(CON.MATERIAL_OCR_CORRECTION_UNCONFIRMED)

    # ---- CANCEL_PENDING ----
    if intent == "CANCEL_PENDING":
        if matched_position != "VERIFIED":
            blockers.append("CANCEL_TARGET_NOT_UNIQUELY_MATCHED")
        return _decision(intent, fields, normalized, raw_text, norm, mat, flags=["CANCEL_PROPOSAL_DRY_RUN"],
                         blockers=blockers, reasons=reasons + ["explicit cancellation instruction"],
                         execution_eligible=False, human_review=True,
                         may_create_proposal=(not blockers), provider_ts_ms=provider_ts_ms, now_ms=now_ms,
                         management_plan="CANCEL_PENDING")

    # ---- TRADE_UPDATE ----
    if intent == "TRADE_UPDATE":
        plan = map_management(normalized) or "UNKNOWN_UPDATE"
        if plan == "UNKNOWN_UPDATE":
            blockers.append("AMBIGUOUS_MANAGEMENT_WORDING")
        con = CON.detect(direction=fields["direction"], entry_low=fields["entry_low"],
                         entry_high=fields["entry_high"], stop=fields["stop"], is_trade_update=True,
                         matched_position=matched_position, material_ocr_unconfirmed=material_unconfirmed)
        blockers += con
        return _decision(intent, fields, normalized, raw_text, norm, mat, flags=[plan],
                         blockers=sorted(set(blockers)), reasons=reasons + [f"management_plan={plan}"],
                         execution_eligible=False, human_review=True, may_create_proposal=False,
                         provider_ts_ms=provider_ts_ms, now_ms=now_ms, management_plan=plan)

    # ---- NEW_SIGNAL (the only path to a gated preview) ----
    if intent == "NEW_SIGNAL":
        # mandatory fields
        for name, val in (("instrument", fields["instrument"]), ("direction", fields["direction"]),
                          ("entry", fields["entry_low"]), ("stop", fields["stop"])):
            if val is None:
                blockers.append(f"MISSING_{name.upper()}")
        if fields["instrument"] and fields["instrument"] != "XAUUSD":
            blockers.append("UNSUPPORTED_INSTRUMENT")
        if not fields["targets"]:
            warnings.append("NO_TAKE_PROFIT_SET" if targets_optional else "MISSING_TARGETS")
            if not targets_optional:
                blockers.append("MISSING_TARGETS")
        # contradictions
        con = CON.detect(direction=fields["direction"], entry_low=fields["entry_low"],
                         entry_high=fields["entry_high"], stop=fields["stop"], order_type=fields["order_type"],
                         instruments=fields["all_instruments"], directions=fields["all_directions"],
                         stops=fields["all_stops"], material_ocr_unconfirmed=material_unconfirmed)
        blockers += con
        if fields.get("zone_reversed"):
            blockers.append(CON.MALFORMED_ENTRY_ZONE)
        # TTL (provider timestamp only)
        fr = TTL.evaluate_freshness(provider_ts_ms=provider_ts_ms, now_ms=now_ms,
                                    ingestion_ts_ms=ingestion_ts_ms, stage="proposal_construction")
        if not fr["execution_eligible"]:
            blockers.append(fr["blocking_reason"])
        # quote-path coverage + zone (fail closed if missing)
        za = None
        if quote is not None and fields["entry_low"] is not None:
            za = QP.zone_analysis(quote_path or [], direction=fields["direction"],
                                  entry_low=fields["entry_low"], entry_high=fields["entry_high"],
                                  start_ms=(provider_ts_ms or now_ms), end_ms=now_ms)
            if za["blocker"]:
                blockers.append(za["blocker"])
            elif za["zone_touched"] or za["entry_passed"]:
                blockers.append("ZONE_ALREADY_TOUCHED" if za["zone_touched"] else "ENTRY_ALREADY_PASSED")
        else:
            blockers.append("QUOTE_PATH_UNVERIFIED")
        # duplicate
        if existing_signals:
            new = _dedup_view(raw_text, fields, provider_ts_ms)
            dup = ID.check_duplicate(new, existing_signals, now_ms=now_ms)
            if not dup["execution_eligible"]:
                blockers.append(dup["blocking_reason"])
        blockers = sorted(set(blockers))
        eligible = not blockers
        return _decision(intent, fields, normalized, raw_text, norm, mat,
                         flags=(["EXECUTION_ELIGIBLE_PENDING_CONFIRMATION"] if eligible else ["BLOCKED"]),
                         blockers=blockers, reasons=reasons + ["mandatory fields + freshness + path + dedup"],
                         execution_eligible=eligible, human_review=True, may_create_proposal=eligible,
                         provider_ts_ms=provider_ts_ms, now_ms=now_ms, warnings=warnings, zone=za)

    # ---- UNKNOWN ----
    return _decision("UNKNOWN", fields, normalized, raw_text, norm, mat, flags=["UNKNOWN"],
                     blockers=["UNKNOWN_INTENT"] + blockers, reasons=reasons + ["no clear actionable pattern"],
                     execution_eligible=False, human_review=True, may_create_proposal=False,
                     provider_ts_ms=provider_ts_ms, now_ms=now_ms)


def _dedup_view(raw_text, fields, provider_ts_ms):
    return {"signal_id": "candidate", "state": "PROPOSED", "provider_ts_ms": provider_ts_ms,
            "source_fingerprint": ID.source_fingerprint(raw_text=raw_text),
            "semantic_fingerprint": ID.semantic_fingerprint(provider="farouk", instrument=fields["instrument"],
                                                            direction=fields["direction"], order_intent=fields["order_type"] or "LIMIT",
                                                            entry_low=fields["entry_low"], entry_high=fields["entry_high"],
                                                            stop=fields["stop"], targets=fields["targets"], provider_ts_ms=provider_ts_ms),
            "execution_identity": ID.execution_identity()}


def _decision(intent, fields, normalized, raw_text, norm, mat, *, flags, blockers, reasons,
              execution_eligible, human_review, may_create_proposal, provider_ts_ms, now_ms,
              warnings=None, management_plan=None, zone=None):
    age = None if provider_ts_ms is None else round((now_ms - provider_ts_ms) / 1000.0, 1)
    return {
        "contract_version": CONTRACT_VERSION,
        "intent": intent, "flags": flags, "classification_reasons": reasons,
        "raw_text": raw_text, "normalized_text": normalized,
        "normalizations_applied": norm["normalizations_applied"],
        "material_corrections": mat["material_corrections"],
        "confirmation_required_ocr": mat["confirmation_required"],
        "fields": {k: fields.get(k) for k in ("instrument", "direction", "order_type", "entry_low",
                                              "entry_high", "stop", "targets")},
        "provider_timestamp_ms": provider_ts_ms, "signal_age_seconds": age,
        "management_plan": management_plan, "zone_analysis": zone, "warnings": warnings or [],
        "execution_eligible": execution_eligible, "human_confirmation_required": human_review,
        "may_create_proposal": may_create_proposal, "blocking_reasons": blockers,
        "note": "Advisory interpretation only. Fail-closed. No broker action constructed or sent.",
    }
