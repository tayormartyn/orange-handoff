"""
Brick 5C Phase 2A — OFFLINE hardening for live Telegram image-byte preservation.

Isolated package. Builds the hardened, fail-closed media-capture machinery that a LATER
controlled activation (Phase 2B) would wire into the listener — but does NOT touch
module_a_telegram.py, does NOT restart the listener, downloads NO live media, and runs NO
catch-up against Telegram. The activation flag defaults False.

Guarantees built here: text-first commit (media can never roll back text), atomic
content-addressed writes, streaming size cap, semantic message/media/revision dedup, rich
append-only statuses, a dedicated isolated DB + directory, and a build-only controlled
read-only catch-up component. No OCR / vision / interpretation / broker / credential / network.
"""
SCHEMA_VERSION = "media-5c2a.0"
