"""
H1 — Hyperliquid TESTNET public market-data OBSERVATION package.

OFFLINE-FIRST, READ-ONLY BY CONSTRUCTION. This package:
  * loads NO signing key (mainnet OR testnet) — observation needs none;
  * touches NO funds and reads NO account state (that is parked H2);
  * uses ONLY the public /info POST + public WebSocket feeds — never the signing route;
  * defines NO order / cancel / transfer / deposit / withdrawal / signing path
    (proven by an automated source scan that BLOCKS the brick if violated);
  * writes to a SEPARATE, ISOLATED database that is never backfilled from or into
    the gold / Telegram / campaign evidence.

In THIS build nothing connects to the network. Mocks + replay fixtures prove the
behaviour offline. A live testnet connection is a SEPARATE, separately-approved step.
"""

OBSERVER_VERSION = "hl-obs-0.1.0"

# Stamped on every persisted row so isolation is auditable: this lineage value must
# never appear in gold/Telegram/campaign stores, and those lineages must never appear here.
DATA_LINEAGE = "hyperliquid_testnet_public_marketdata"
