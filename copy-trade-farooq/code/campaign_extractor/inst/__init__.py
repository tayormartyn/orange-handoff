"""
INST-1 — canonical instrument registry + fail-closed symbol normalisation.

Fully ISOLATED: its own SQLite database (inst/data/instrument_registry_v1.db), its own
append-only primitives, and NO imports from mpk/, the listener, broker, exchange, or any
credential path. Deleting this package/DB leaves all MPK, Farouk, Gold, prospective, and
broker data completely intact.

INST-1 normalises asset references deterministically and FAILS CLOSED: a bare underlying
(GOLD/BTC/OIL/SILVER/index) resolves at most to a canonical underlying, never to a specific
instrument/contract, and never to a venue. No fuzzy matching, no LLM, no OCR/vision, no
network, no inference from nearby words without an explicit deterministic rule.
"""
SCHEMA_VERSION = "inst-1.0"
