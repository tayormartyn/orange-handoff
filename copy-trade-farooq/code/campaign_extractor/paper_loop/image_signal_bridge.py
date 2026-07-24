"""
Image signal adapter (Phases 7-9). Turns human-APPROVED signal-announcement media facts into an
IMAGE_CONFIRMED UnifiedSignal, runs the UNCHANGED Q4A kernel at three honestly-labelled time
anchors, and records to the append-only paper store + image-bridge extension + alert. It reuses
Vision V1.1, Q4A and the paper loop unchanged and edits none of their decision logic.
"""
from __future__ import annotations
import os
import sys
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_CE = os.path.dirname(_HERE)
_Q4 = os.path.join(_CE, "q4_align")
for p in (_Q4, _HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import paper_gate                                        # thin Q4A wrapper, unchanged
import image_profile
from unified_signal import build_unified
from paper_const import LABELS

GOLD = ("XAUUSD", "GOLD", "XAU")


def _ms(s):
    if not s:
        return None
    d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    return int((d if d.tzinfo else d.replace(tzinfo=timezone.utc)).timestamp() * 1000)


# ---------------------------------------------------------------- adapter: facts -> UnifiedSignal
def build_image_unified_signal(approved, manifest, review_refs):
    """(status, unified_or_None, reason). Rejects everything that must not become a signal."""
    sc = approved.get("semantic_class")
    if not image_profile.may_propose_signal(sc, approved.get("isolated_signal_block", False)):
        return "REJECTED", None, "NOT_A_SIGNAL"
    if not approved.get("all_facts_human_confirmed"):
        return "NEEDS_REVIEW", None, "UNCONFIRMED_FACTS"
    if not approved.get("provider_verified"):
        return "NEEDS_REVIEW", None, "PROVIDER_UNVERIFIED"
    if approved.get("mixed_blocks_not_separated"):
        return "NEEDS_REVIEW", None, "SIGNAL_BLOCKS_NOT_SEPARATED"
    if approved.get("conflicting_high_impact"):
        return "NEEDS_REVIEW", None, "CONFLICTING_HIGH_IMPACT_FIELDS"
    if str(approved.get("instrument", "")).upper() not in GOLD:
        return "REJECTED", None, "UNSUPPORTED_ASSET"
    if str(approved.get("direction", "")).upper() not in ("BUY", "SELL"):
        return "NEEDS_REVIEW", None, "AMBIGUOUS_DIRECTION"
    lo, hi = approved.get("entry_low"), approved.get("entry_high")
    if lo is None or hi is None or str(lo).strip() == "" or str(hi).strip() == "":
        return "NEEDS_REVIEW", None, "MISSING_ENTRY"

    unified = build_unified(
        provider_id="FAROUK", source_type="IMAGE_CONFIRMED",
        source_channel_id=manifest.get("source_server_channel_text"),
        source_message_id=manifest.get("discord_message_ref") or manifest.get("intake_id"),
        source_message_timestamp=approved.get("provider_posted_at"),
        listener_received_at=manifest.get("screenshot_imported_at"),   # anchors overridden per-run
        parsed_at=approved.get("human_confirmed_at"),
        instrument="XAUUSD", direction=str(approved["direction"]).upper(),
        entry_low=str(lo), entry_high=str(hi), stop_price=approved.get("stop_price"),
        target_prices=approved.get("target_prices"),
        source_evidence_references=review_refs, human_confirmed=True,
        reviewer_reference=approved.get("reviewer_reference"),
        confirmation_timestamp=approved.get("human_confirmed_at"))
    unified["source_platform"] = "DISCORD"
    unified["original_image_sha256"] = manifest.get("original_image_sha256")
    return "IMAGE_CONFIRMED", unified, None


# ---------------------------------------------------------------- three honest time anchors
def _anchor(unified, quotes, config, anchor_time, label, unverifiable_reason):
    if anchor_time is None:
        return {"anchor": label, "status": "PAPER_UNKNOWN", "reason": unverifiable_reason,
                "raw_q4a_actionable": None}
    s = dict(unified)
    s["listener_received_at"] = anchor_time
    s["parsed_at"] = anchor_time
    d = paper_gate.decide(s, quotes, config)             # unchanged Q4A via unchanged paper gate
    act = d.get("actionable") or {}
    return {"anchor": label, "status": d["status"], "reason": d.get("reason"),
            "raw_q4a_actionable": act, "bid": act.get("bid"), "ask": act.get("ask"),
            "executable_side": act.get("executable_side"),
            "transport": "MANUAL_DISCORD_IMAGE — NOT a Telegram listener-delivery event"}


def run_three_anchors(unified, quotes, config, *, provider_posted_at, provider_posted_provenance,
                      screenshot_imported_at, human_confirmed_at):
    pp = provider_posted_at if (provider_posted_provenance and
                                provider_posted_provenance != "UNVERIFIABLE") else None
    return {
        "PROVIDER_POST_TIME_RESULT": _anchor(unified, quotes, config, pp,
            "PROVIDER_POST_TIME_RESULT", "POST_TIME_UNVERIFIABLE"),
        "MANUAL_IMPORT_TIME_RESULT": _anchor(unified, quotes, config, screenshot_imported_at,
            "MANUAL_IMPORT_TIME_RESULT", "IMPORT_TIME_MISSING"),
        "HUMAN_CONFIRMED_ACTIONABLE_RESULT": _anchor(unified, quotes, config, human_confirmed_at,
            "HUMAN_CONFIRMED_ACTIONABLE_RESULT", "CONFIRM_TIME_MISSING"),
    }


def latencies(*, provider_posted_at, screenshot_captured_at, screenshot_imported_at, human_confirmed_at):
    def diff(a, b):
        A, B = _ms(a), _ms(b)
        return round((A - B) / 1000, 3) if (A is not None and B is not None) else None
    return {"capture_latency_s": diff(screenshot_captured_at, provider_posted_at),
            "import_latency_s": diff(screenshot_imported_at, provider_posted_at),
            "actionable_latency_s": diff(human_confirmed_at, provider_posted_at)}


def build_alert(unified, anchors, *, intake_id, provider_posted_provenance, latency_s):
    hc = anchors["HUMAN_CONFIRMED_ACTIONABLE_RESULT"]
    pp = anchors["PROVIDER_POST_TIME_RESULT"]
    return {
        "banner": "MANUAL DISCORD IMAGE / PAPER ONLY / NOT A FILL / NOT AN OUTCOME",
        "labels": list(LABELS) + ["IMAGE_CONFIRMED", "MANUAL_DISCORD"],
        "provider": unified["provider_id"], "instrument": unified["instrument"],
        "direction": unified["direction"], "entry_range": [unified["entry_low"], unified["entry_high"]],
        "stop": unified.get("stop_price"), "source_reference": unified.get("source_message_id"),
        "intake_id": intake_id, "original_image_sha256": unified.get("original_image_sha256"),
        "provider_post_timestamp": unified.get("source_message_timestamp"),
        "provider_post_provenance": provider_posted_provenance,
        "provider_post_quote_result": f"{pp['status']}/{pp.get('reason')}",
        "import_time_quote_result": anchors["MANUAL_IMPORT_TIME_RESULT"]["status"],
        "confirmation_time_quote_result": hc["status"],
        "pepperstone_bid": hc.get("bid"), "pepperstone_ask": hc.get("ask"),
        "executable_side": hc.get("executable_side"), "reason": hc.get("reason"),
        "actionable_latency_s": latency_s.get("actionable_latency_s"),
        "transport": "MANUAL_DISCORD_IMAGE (not Telegram delivery)",
    }
