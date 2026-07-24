"""RAW FAROUK TEXT CLASSIFIER v0.1 — OFFLINE / OBSERVATION ONLY.

Turns a captured Farouk raw TradingView `alert()` string into CANDIDATE descriptive
fields for observation. It describes *what fired*, never *what to do*.

NON-NEGOTIABLE (enforced by construction below):
  * Raw text is the source of truth and is preserved verbatim in the output.
  * Every output is candidate-only. There is NO execution interpretation, NO trade
    instruction, NO order intent, NO broker route, NO lot size, NO account ID, NO
    risk sizing, NO permit / lease / order. Those fields are hard-wired False/absent.
  * Runs offline over already-captured strings. It performs NO I/O: no network, no
    broker/cTrader/QST import, no R2 access, no Worker deploy.

This module changes nothing about NOT_INTEGRATION_READY. It only reads a string.
"""

import re

PARSE_VERSION = "raw_farouk_text_classifier_v0_1"

# Instrument/timeframe like "on XAUUSD 3" (timeframe is the trailing chart number).
_INSTRUMENT_TF_RE = re.compile(
    r"\bon\s+([A-Z][A-Z0-9]{2,15})\s+(\d{1,4})\b", re.IGNORECASE
)


def _extract_instrument_timeframe(raw_text):
    """Return (instrument, timeframe, warnings) parsed from 'on <SYM> <TF>'.

    instrument/timeframe are None when the pattern is absent (never guessed).
    """
    warnings = []
    m = _INSTRUMENT_TF_RE.search(raw_text or "")
    if not m:
        warnings.append("instrument/timeframe pattern 'on <SYM> <TF>' not found")
        return None, None, warnings
    return m.group(1).upper(), m.group(2), warnings


# Ordered rules: FIRST match wins. Order matters — the most specific / highest-grade
# patterns are checked before the generic ones (A+++ before A+ before "A LONG";
# engulfing/choch/sweep/bpr before the bare A directional match).
#
# Each rule: (compiled regex, field dict). Fields are candidate descriptors only.
_RULES = [
    # --- grade signals (candidate_only; NOT observed in the Gate G sample) ---
    (re.compile(r"a\+{3}", re.IGNORECASE),
     dict(event_family="A_TRIPLE_PLUS", event_type="A_TRIPLE_PLUS",
          direction=None, candidate_only=True)),
    (re.compile(r"a\+\s*or\s*better", re.IGNORECASE),
     dict(event_family="A_PLUS", event_type="A_PLUS_OR_BETTER",
          direction=None, candidate_only=True)),
    (re.compile(r"a\+\s*long", re.IGNORECASE),
     dict(event_family="A_PLUS", event_type="A_PLUS", direction="LONG",
          candidate_only=True)),
    (re.compile(r"a\+\s*short", re.IGNORECASE),
     dict(event_family="A_PLUS", event_type="A_PLUS", direction="SHORT",
          candidate_only=True)),
    (re.compile(r"a\+", re.IGNORECASE),
     dict(event_family="A_PLUS", event_type="A_PLUS", direction=None,
          candidate_only=True)),

    # --- structure ---
    (re.compile(r"choch\s*up", re.IGNORECASE),
     dict(event_family="STRUCTURE", event_type="CHOCH_UP", direction="LONG_HINT")),
    (re.compile(r"choch\s*down", re.IGNORECASE),
     dict(event_family="STRUCTURE", event_type="CHOCH_DOWN", direction="SHORT_HINT")),

    # --- engulfing ---
    (re.compile(r"bullish\s*engulfing", re.IGNORECASE),
     dict(event_family="ENGULFING", event_type="BULLISH_ENGULFING",
          direction="LONG_HINT")),
    (re.compile(r"bearish\s*engulfing", re.IGNORECASE),
     dict(event_family="ENGULFING", event_type="BEARISH_ENGULFING",
          direction="SHORT_HINT")),

    # --- balanced price range ---
    (re.compile(r"bpr\s*formed", re.IGNORECASE),
     dict(event_family="BPR", event_type="BPR_FORMED", direction=None)),
    (re.compile(r"bpr\s*tapped", re.IGNORECASE),
     dict(event_family="BPR", event_type="BPR_TAPPED", direction=None)),

    # --- liquidity sweep ---
    (re.compile(r"sweep\s*high", re.IGNORECASE),
     dict(event_family="LIQUIDITY_SWEEP", event_type="SWEEP_HIGH",
          direction="SHORT_HINT")),
    (re.compile(r"sweep\s*low", re.IGNORECASE),
     dict(event_family="LIQUIDITY_SWEEP", event_type="SWEEP_LOW",
          direction="LONG_HINT")),

    # --- bare A directional (checked AFTER A+ / A+++ so "A+ LONG" never lands here) ---
    (re.compile(r"\ba\s+long\b", re.IGNORECASE),
     dict(event_family="A_SIGNAL", event_type="A_LONG", direction="LONG")),
    (re.compile(r"\ba\s+short\b", re.IGNORECASE),
     dict(event_family="A_SIGNAL", event_type="A_SHORT", direction="SHORT")),
]


def classify_raw_farouk_text(raw_text, received_at_utc=None, r2_object_key=None):
    """Classify one raw Farouk alert string into candidate descriptor fields.

    Returns a dict. Raw text is preserved verbatim under 'raw_text'. All
    execution-related flags are hard-wired safe (False). Nothing here can be
    interpreted as a trade instruction.
    """
    warnings = []

    # Preserve the original exactly; only use a local copy for matching.
    text_for_match = raw_text if isinstance(raw_text, str) else ""
    if not isinstance(raw_text, str):
        warnings.append("raw_text was not a string; preserved as-is, classified UNKNOWN")
    elif text_for_match.strip() == "":
        warnings.append("raw_text is empty/whitespace")

    matched = None
    for pattern, fields in _RULES:
        if pattern.search(text_for_match):
            matched = fields
            break

    if matched is None:
        matched = dict(event_family="UNKNOWN", event_type=None, direction=None)
        if text_for_match.strip():
            warnings.append("no known Farouk pattern matched; event_family=UNKNOWN")

    instrument, timeframe, itf_warnings = _extract_instrument_timeframe(text_for_match)
    warnings.extend(itf_warnings)

    event_family = matched.get("event_family", "UNKNOWN")
    event_type = matched.get("event_type")
    direction = matched.get("direction")
    candidate_only_flag = matched.get("candidate_only", False)

    # Confidence is a description-quality heuristic only — NOT a trade-quality score.
    if event_family == "UNKNOWN":
        confidence = 0.0
    elif instrument and timeframe:
        confidence = 0.9
    else:
        confidence = 0.6

    # is_trade_signal_candidate: candidate label ONLY, never a permission. It flags the
    # families that a *human* might later look at more closely. It authorises nothing.
    is_trade_signal_candidate = event_family in (
        "A_SIGNAL", "A_PLUS", "A_TRIPLE_PLUS", "STRUCTURE", "LIQUIDITY_SWEEP",
    ) or bool(candidate_only_flag)

    return {
        "raw_text": raw_text,                       # source of truth, verbatim
        "parse_version": PARSE_VERSION,
        "received_at_utc": received_at_utc,         # passthrough, verbatim (may be None)
        "r2_object_key": r2_object_key,             # passthrough, verbatim (may be None)
        "event_family": event_family,
        "event_type": event_type,
        "direction": direction,
        "instrument": instrument,
        "timeframe": timeframe,
        "is_trade_signal_candidate": is_trade_signal_candidate,
        "candidate_only": True,                     # always: this is observation only
        "execution_allowed": False,                 # hard-wired
        "broker_execution_allowed": False,          # hard-wired
        "qst_allowed": False,                        # hard-wired
        "confidence": confidence,
        "warnings": warnings,
    }


if __name__ == "__main__":
    import json
    import sys
    src = " ".join(sys.argv[1:]) or "Farouks Playbook: A LONG on XAUUSD 3"
    print(json.dumps(classify_raw_farouk_text(src), indent=2))
