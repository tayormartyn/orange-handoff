"""
Region-first candidate extraction interfaces + a deterministic mock for fixture 1.

The real extractor would call a vision model on the imported image (NOT run here — no image, no
network). MockFixture1Extractor returns the human-authored fixture-1 expectation AS CANDIDATES
(numerics accepted=NULL, pending human review). Includes dual-reading comparison and the
instrument firewall (BTCUSD is never Gold; Gold association requires human-confirmed XAUUSD).
"""
from __future__ import annotations

from __init__ import EXTRACTOR_VERSION

GOLD_ALIASES = {"XAUUSD", "GOLD", "XAU"}


# ---------------------------------------------------------------- dual reading (deterministic)
def dual_reading(reading_a, reading_b):
    if reading_a is None and reading_b is None:
        return "UNREADABLE"
    if reading_a is None or reading_b is None:
        return "ONE_READER_ONLY"
    return "READERS_AGREE" if str(reading_a).strip() == str(reading_b).strip() else "READERS_DISAGREE"


# ---------------------------------------------------------------- instrument firewall
class GoldAssociationBlocked(Exception):
    pass


def classify_instrument(value):
    v = (value or "").strip().upper().replace("/", "")
    if v in ("BTCUSD", "BTC"):
        return "BTCUSD"
    if v in GOLD_ALIASES:
        return "XAUUSD"
    return None                                        # unclear -> NULL, never guessed


def associate_gold(human_confirmed_instrument):
    """Permitted ONLY when a human has confirmed the instrument is XAUUSD/Gold. Channel context
    must never override visible instrument evidence."""
    if human_confirmed_instrument != "XAUUSD":
        raise GoldAssociationBlocked(
            f"instrument '{human_confirmed_instrument}' is not human-confirmed Gold")
    return True


# ---------------------------------------------------------------- extractor interface
class Extractor:
    version = EXTRACTOR_VERSION

    def extract(self, media_id, sha256):
        raise NotImplementedError


def _cand(region_id, region_type, field_type, value, domain, *, alt=None, conf=0.9,
          dual="READERS_AGREE", raw=None, crop="crop0000"):
    return {"region_id": region_id, "region_type": region_type, "field_type": field_type,
            "raw_visible_text": raw if raw is not None else value,
            "candidate_value_string": value, "evidence_domain": domain,
            "alternative_readings": alt or [value], "extractor_confidence": conf,
            "dual_reading_state": dual, "crop_sha256": f"{crop}{region_id}",
            "bbox": [0, 0, 10, 10]}


class MockFixture1Extractor(Extractor):
    """Represents what a vision model WOULD propose from the BTCUSD screenshot. Candidate-only."""

    def extract(self, media_id, sha256):
        R = {"hdr": "INSTRUMENT_HEADER", "t1": "TICKET_1", "t2": "TICKET_2",
             "chart": "CHART", "comm": "COMMENTARY_TEXT"}
        regions = [{"region_id": f"{media_id}:{k}", "region_type": v, "bbox": [0, 0, 100, 20],
                    "crop_sha256": f"cropregion-{k}", "detection_confidence": 0.95}
                   for k, v in R.items()]
        h, t1, t2, comm = (f"{media_id}:hdr", f"{media_id}:t1", f"{media_id}:t2", f"{media_id}:comm")
        candidates = [
            _cand(h, "INSTRUMENT_HEADER", "INSTRUMENT", "BTCUSD", "VISIBLE_TRADE_FACT", conf=0.99),
            # ticket 1 — kept strictly separate from ticket 2
            _cand(t1, "TICKET_1", "DIRECTION", "BUY", "VISIBLE_TRADE_FACT"),
            _cand(t1, "TICKET_1", "ENTRY_PRICE", "58585.70", "VISIBLE_TRADE_FACT"),
            _cand(t1, "TICKET_1", "EXIT_PRICE", "59008.70", "VISIBLE_TRADE_FACT"),
            _cand(t1, "TICKET_1", "PROVIDER_DISPLAYED_PNL", "+423.00", "PROVIDER_DISPLAYED"),
            # ticket 2
            _cand(t2, "TICKET_2", "DIRECTION", "BUY", "VISIBLE_TRADE_FACT"),
            _cand(t2, "TICKET_2", "ENTRY_PRICE", "58569.78", "VISIBLE_TRADE_FACT"),
            _cand(t2, "TICKET_2", "EXIT_PRICE", "59008.70", "VISIBLE_TRADE_FACT"),
            _cand(t2, "TICKET_2", "PROVIDER_DISPLAYED_PNL", "+438.92", "PROVIDER_DISPLAYED"),
            # commentary / management (candidate-only)
            _cand(comm, "COMMENTARY_TEXT", "COMMENTARY_TEXT",
                  "break 1H bearish FVG toward TP1; take TP1 now and move stop to breakeven",
                  "COMMENTARY", dual="ONE_READER_ONLY"),
            _cand(comm, "COMMENTARY_TEXT", "MANAGEMENT_INSTRUCTION", "TAKE_TP1_INSTRUCTION",
                  "COMMENTARY", dual="ONE_READER_ONLY"),
            _cand(comm, "COMMENTARY_TEXT", "MANAGEMENT_INSTRUCTION", "MOVE_STOP_TO_ENTRY_INSTRUCTION",
                  "COMMENTARY", dual="ONE_READER_ONLY"),
        ]
        semantics = {"classification": "POSITION_MANAGEMENT", "has_clean_entry_range": False,
                     "is_clean_new_entry_signal": False,
                     "management_candidates": ["TAKE_TP1_INSTRUCTION", "MOVE_STOP_TO_ENTRY_INSTRUCTION"]}
        return {"regions": regions, "candidates": candidates, "semantics": semantics}
