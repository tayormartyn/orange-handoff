"""
Q4A — Deterministic offline signal-to-quote alignment kernel (OBSERVATION_ONLY).

Aligns a human-confirmed Farouk XAUUSD signal to the first valid Pepperstone demo quote after
two anchors (listener_received_at, parsed_at). Pure/deterministic — no LLM matching, no live
connection. Reads Telegram evidence + data/ctrader_quotes_v1.db READ-ONLY; writes only
data/q4_alignment_v1.db. Never claims a fill, execution, outcome, R, or profitability.
"""
Q4_VERSION = "q4a.1"
