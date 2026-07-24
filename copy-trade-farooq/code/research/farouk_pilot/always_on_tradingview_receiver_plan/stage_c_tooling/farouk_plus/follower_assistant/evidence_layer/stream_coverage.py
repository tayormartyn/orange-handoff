"""Part 6 — published-stream coverage classification (deterministic, additive).

Classifies EVERY published channel message over an observation window into one exhaustive class,
so the record proves what was and was not published. Never claims knowledge of unpublished
private setups. Reuses the interpreter's Farouk-gold gate; other senders/assets are classified by
sender + asset keywords only (no inference of intent beyond wording).
"""
from __future__ import annotations

import re
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
for p in (HERE, PARENT):
    if p not in sys.path:
        sys.path.insert(0, p)
import interpreter                                                 # noqa: E402

CLASSES = ("FAROUK_XAU_SETUP", "FAROUK_XAU_MANAGEMENT", "FAROUK_XAU_CANCELLATION",
           "FAROUK_XAU_MISSED_TRADE", "FAROUK_XAU_LOSS", "FAROUK_XAU_RESULT_CLAIM",
           "FAROUK_BTC_SOL_SETUP", "FAROUK_OTHER_ASSET", "EDUCATION", "COMMENTARY",
           "EXPLICIT_NO_TRADE", "OTHER_PROVIDER", "IRRELEVANT")


def classify_message(raw_text):
    t = (raw_text or "")
    low = t.lower()
    first = t.strip().splitlines()[0] if t.strip() else ""
    is_farouk = first.lower().startswith("seascalperfarouk")
    farouk_gold = interpreter.is_farouk_gold(t)
    if farouk_gold:
        c = interpreter.classify(t)
        if c["kind"] == "ENTRY":
            return "FAROUK_XAU_SETUP"
        if re.search(r"no trade|not taking|skip|stand aside", low):
            return "EXPLICIT_NO_TRADE"
        if re.search(r"missed|didn.?t enter|didn.?t fill|missed my", low):
            return "FAROUK_XAU_MISSED_TRADE"
        if re.search(r"stopped out|sl hit|loss|stop hit|took the loss", low):
            return "FAROUK_XAU_LOSS"
        if re.search(r"closed|pips|profit|tp\b|banked|risk free|out \d", low):
            return "FAROUK_XAU_RESULT_CLAIM"
        if c["kind"] == "MANAGEMENT":
            return "FAROUK_XAU_MANAGEMENT"
        if re.search(r"cancel", low):
            return "FAROUK_XAU_CANCELLATION"
        return "COMMENTARY"
    if is_farouk:
        if re.search(r"\bbtc\b|bitcoin|\bsol\b|solana", low):
            return "FAROUK_BTC_SOL_SETUP" if re.search(r"buy|sell|entry|sl\b|long|short", low) else "COMMENTARY"
        return "FAROUK_OTHER_ASSET"
    if first and re.search(r"posted in", first.lower()):
        return "OTHER_PROVIDER"
    if re.search(r"lesson|learn|educat|example|why |how to", low):
        return "EDUCATION"
    return "IRRELEVANT"


def coverage_report(messages, window_start_utc, window_end_utc):
    """messages: list of {id, raw_text}. Returns an additive coverage record."""
    counts = {c: 0 for c in CLASSES}
    per_msg = []
    for m in messages:
        cls = classify_message(m.get("raw_text"))
        counts[cls] = counts.get(cls, 0) + 1
        per_msg.append({"id": m.get("id"), "class": cls})
    xau_campaigns = counts["FAROUK_XAU_SETUP"]
    return {
        "record_type": "STREAM_COVERAGE",
        "window": {"start_utc": window_start_utc, "end_utc": window_end_utc},
        "message_count": len(messages), "class_counts": counts, "per_message": per_msg,
        "no_published_xau_campaign": xau_campaigns == 0,
        "disclaimer": "classifies PUBLISHED messages only; no claim about unpublished private setups",
    }
