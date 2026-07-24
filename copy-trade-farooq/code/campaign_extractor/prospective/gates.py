"""
Two SEPARATE permission gates (Brick 5C architectural clarification).

  1. EVIDENCE CAPTURE GATE  — may raw text/media from a (channel, sender) be PRESERVED?
  2. TRADE-STATE MUTATION GATE — may that sender CREATE or ALTER tracked trade plans,
     campaigns, legs or outcomes?

Passing the capture gate NEVER implies passing the mutation gate. An approved evidence-only
sender (e.g. wazwithazed in quant-flow) may have messages/media preserved while remaining
CONTEXT_ONLY — it can never mutate trade state. Only Farouk (or a sender Martyn has
explicitly approved as tracked) passes the mutation gate.
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # campaign_extractor
from sender_gate import is_farouk


def capture_allowed(channel_id, channel_allowlist) -> bool:
    """EVIDENCE CAPTURE GATE: preserve evidence only from an allowlisted channel."""
    return channel_id in set(channel_allowlist)


def mutation_allowed(sender_handle, tracked_senders=None) -> bool:
    """TRADE-STATE MUTATION GATE: only Farouk (or an explicitly Martyn-approved tracked
    sender) may create/alter trade state. Capture approval does NOT grant this."""
    if is_farouk(sender_handle):
        return True
    return sender_handle in set(tracked_senders or [])


def sender_status(sender_handle, tracked_senders=None) -> str:
    """TRACKED (may mutate) vs CONTEXT_ONLY (capture only, never mutates)."""
    return "TRACKED" if mutation_allowed(sender_handle, tracked_senders) else "CONTEXT_ONLY"
