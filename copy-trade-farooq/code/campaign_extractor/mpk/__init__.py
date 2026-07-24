"""
MPK — Multi-Provider Campaign-Keying layer (MPK-1, Step 1: empty foundation).

ISOLATED by construction. This package:
  * creates two NEW canonical SQLite databases (mpk_registry_v1.db, mpk_campaigns_v1.db)
    under mpk/data/, both append-only and empty of business data after initialisation;
  * imports NOTHING from the existing spine, listener, broker, exchange or live paths;
  * opens NO legacy/protected database except read-only (mode=ro) via the helper in
    legacy_readonly.py — and Step 1 creates NO Farouk registration and NO legacy mapping.

Standing locks are not the concern of this package: it loads no credentials, opens no
network socket, and is never imported by the running Telegram listener.
"""
SCHEMA_VERSION = "mpk-1.step1.0"
