"""
INST-1 deterministic, idempotent reference seed for instrument_registry_v1.db.

Seeds canonical underlyings, synthetic canonical instruments, the global alias catalog, and
the global mapping rules. NO provider-specific aliases and NO mapping decisions are seeded
(those are produced per-request / in tests). Re-running is a no-op once seeded.

The synthetic canonical instruments are REFERENCE rows only — their existence implies nothing
about venue support, broker availability, or trading eligibility.
"""
from __future__ import annotations
import os

import sys as _sys
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)
from registry_db import InstrumentRegistryDB

DATA_DIR = os.path.join(_HERE, "data")
REGISTRY_DB_PATH = os.path.join(DATA_DIR, "instrument_registry_v1.db")
SEED_EFFECTIVE_FROM = "2020-01-01T00:00:00Z"

UNDERLYINGS = [
    ("underlying_gold", "Gold", "METAL"), ("underlying_silver", "Silver", "METAL"),
    ("underlying_btc", "Bitcoin", "CRYPTO"), ("underlying_eth", "Ethereum", "CRYPTO"),
    ("underlying_wti", "WTI Crude", "ENERGY"), ("underlying_brent", "Brent Crude", "ENERGY"),
    ("underlying_sp500", "S&P 500", "INDEX"), ("underlying_nasdaq100", "Nasdaq 100", "INDEX"),
    ("underlying_djia", "Dow Jones Industrial Average", "INDEX"),
]
INSTRUMENTS = [
    ("instrument_xauusd_spot_reference", "underlying_gold", "SPOT_REFERENCE", "XAU", "USD"),
    ("instrument_xauusd_cfd", "underlying_gold", "CFD", "XAU", "USD"),
    ("instrument_gold_future", "underlying_gold", "FUTURE", "XAU", "USD"),
    ("instrument_gold_perpetual", "underlying_gold", "PERPETUAL", "XAU", "USD"),
    ("instrument_btcusd_spot_reference", "underlying_btc", "SPOT_REFERENCE", "BTC", "USD"),
    ("instrument_btcusd_cfd", "underlying_btc", "CFD", "BTC", "USD"),
    ("instrument_btcusd_perpetual", "underlying_btc", "PERPETUAL", "BTC", "USD"),
    ("instrument_btc_future", "underlying_btc", "FUTURE", "BTC", "USD"),
]
# (normalised_token, raw_example, target_underlying, target_instrument_or_None)
GLOBAL_RULES = [
    ("XAUUSD", "XAU/USD", "underlying_gold", "instrument_xauusd_spot_reference"),
    ("GOLD", "GOLD", "underlying_gold", None),
    ("BTCUSD", "BTC/USD", "underlying_btc", "instrument_btcusd_spot_reference"),
    ("BTC", "BTC", "underlying_btc", None),
    ("BITCOIN", "Bitcoin", "underlying_btc", None),
    ("BTCUSDT", "BTCUSDT", "underlying_btc", None),
    ("BTCPERPETUAL", "BTC PERPETUAL", "underlying_btc", "instrument_btcusd_perpetual"),
    ("SILVER", "SILVER", "underlying_silver", None),
    ("XAGUSD", "XAGUSD", "underlying_silver", None),
    ("WTI", "WTI", "underlying_wti", None),
    ("BRENT", "BRENT", "underlying_brent", None),
    ("US30", "US30", "underlying_djia", None),
    ("DOW", "DOW", "underlying_djia", None),
    ("NASDAQ", "NASDAQ", "underlying_nasdaq100", None),
    ("SPX", "SPX", "underlying_sp500", None),
    # OIL is genuinely ambiguous at the UNDERLYING level -> two distinct candidate rules
    ("OIL", "OIL", "underlying_wti", None),
    ("OIL", "OIL", "underlying_brent", None),
]


def seed(db: InstrumentRegistryDB, created_at=None):
    if db.count("canonical_underlyings") > 0:
        return "ALREADY_SEEDED"
    items = []
    for uid, label, cls in UNDERLYINGS:
        items.append(("canonical_underlyings",
                      db.underlying(underlying_id=uid, display_label=label, asset_class=cls,
                                    created_at=created_at)))
    for iid, u, ct, base, quote in INSTRUMENTS:
        items.append(("canonical_instruments",
                      db.instrument(instrument_id=iid, canonical_underlying_id=u, contract_type=ct,
                                    base_asset=base, quote_asset=quote,
                                    notes="reference only; implies no venue/broker availability",
                                    created_at=created_at)))
    seen_tokens = set()
    for idx, (token, raw_ex, u, i) in enumerate(GLOBAL_RULES):
        suffix = u.replace("underlying_", "")
        rule_uid = f"rule_{token}_{suffix}_v1"
        items.append(("mapping_rules",
                      db.rule(mapping_rule_uid=rule_uid, rule_version=1, scope="GLOBAL",
                              input_token=token, target_underlying_id=u, target_instrument_id=i,
                              effective_from=SEED_EFFECTIVE_FROM, admin_reason="initial seed",
                              created_at=created_at)))
        if token not in seen_tokens:     # one catalog alias row per distinct token
            seen_tokens.add(token)
            alias_u = u if sum(1 for t, *_ in GLOBAL_RULES if t == token) == 1 else None
            items.append(("global_aliases",
                          db.global_alias(alias_uid=f"galias_{token}", normalised_token=token,
                                          raw_example=raw_ex, canonical_underlying_id=alias_u,
                                          note="ambiguous underlying" if alias_u is None else None,
                                          created_at=created_at)))
    db.append_many_atomic(items)
    return "SEEDED"


def initialise(created_at=None):
    db = InstrumentRegistryDB(REGISTRY_DB_PATH, applied_at_utc=created_at)
    action = seed(db, created_at=created_at)
    report = {"action": action, "path": REGISTRY_DB_PATH, "counts": db.counts(),
              "tables": db.table_names()}
    db.close()
    return report


if __name__ == "__main__":
    import json
    print(json.dumps(initialise(), indent=2, sort_keys=True))
