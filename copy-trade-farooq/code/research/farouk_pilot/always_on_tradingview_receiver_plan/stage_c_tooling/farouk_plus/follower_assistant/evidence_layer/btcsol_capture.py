"""Part 9 — BTC / SOL capture-only namespaces.

Append-only evidence ledgers for Farouk BTC and SOL posts. CAPTURE ONLY: no constitution, no
entry legs, no management rules, no market feed, no outcome claim. These records can NEVER alter
Gold campaigns or Gold expectancy — they live in separate files and carry no follower/outcome
fields. Their only purpose is to preserve the raw published evidence for future, separately-approved
research.
"""
from __future__ import annotations

import evidence_schema as es

INSTRUMENTS = {"BTC": es.BTC_LEDGER, "SOL": es.SOL_LEDGER}
# forbidden here beyond the global guard: anything implying a followed trade
FORBIDDEN_KEYS = ("legs", "average_entry", "realized_pips", "unrealized_pips", "outcome",
                  "campaign_state", "follower", "expectancy", "constitution")


def capture(instrument, *, message_id, source_ts, receipt_ts, raw_text_sha256, sender,
            classification):
    """Append a capture-only record for a BTC/SOL post. No trade semantics permitted."""
    if instrument not in INSTRUMENTS:
        raise ValueError(f"unsupported capture instrument {instrument}")
    rec = {
        "record_type": f"{instrument}_CAPTURE_ONLY", "instrument": instrument,
        "message_id": message_id,
        "timestamps": {"source_message_utc": source_ts, "telegram_receipt_utc": receipt_ts},
        "raw_text_sha256": raw_text_sha256, "sender": sender, "classification": classification,
        "capture_only": True,
        "isolation_note": "no legs/average/outcome/expectancy fields; cannot affect Gold campaigns",
    }
    for k in FORBIDDEN_KEYS:
        if k in rec:
            raise ValueError(f"forbidden trade field {k} in capture record")
    rec["evidence_commit_ts"] = receipt_ts
    rec = es.finalize(rec)
    es.append_once(INSTRUMENTS[instrument], rec)
    return rec
