"""
ASSOC-1R — real-evidence read-only replay of the Farouk XAUUSD short sequence through the
verified ASSOC-1 decision-only engine.

Reads existing evidence STRICTLY read-only. Writes only to an isolated replay DB
(assoc_replay/data/association_real_replay_v1.db) and temp fixtures. Never mutates any
campaign, prospective evidence, provider/instrument registry, or Gold/broker DB. Never
infers execution, fills, broker confirmation, or realised profit. No LLM/OCR/vision; no
network; no credentials.
"""
REPLAY_VERSION = "assoc-1r.0"
