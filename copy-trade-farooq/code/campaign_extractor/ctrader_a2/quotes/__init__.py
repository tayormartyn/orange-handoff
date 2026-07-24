"""
Q1 — Bounded XAUUSD Quote Capture (read-only, view-only).

Dedicated, isolated component for a bounded ProtoOASubscribeSpots capture of XAUUSD (symbol 41)
on the Pepperstone demo account. Append-only evidence in data/ctrader_quotes_v1.db (raw +
normalised, kept separate). NO order/amend/cancel/close/trading anywhere. All incoming envelopes
pass through the central live_transport.extract_message boundary before parse/error-handling.
"""
Q1_VERSION = "ctrader-q1.0"
