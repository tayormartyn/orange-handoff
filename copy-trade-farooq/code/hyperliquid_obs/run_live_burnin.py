"""
H1 Step 2 — LIVE public-data connectivity burn-in (testnet, public, read-only).

Runs the safety gates, connects to the PUBLIC testnet WebSocket, subscribes to BTC l2Book +
trades, streams for a short window, then disconnects cleanly. Prints a JSON report. Loads NO
key; touches NO funds; queries NO account.

Usage: python hyperliquid_obs/run_live_burnin.py [duration_seconds]
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hyperliquid_obs import config
from hyperliquid_obs.live import LivePublicObserver
from hyperliquid_obs.observation_db import ObservationDB, DEFAULT_DB_PATH


def main():
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    db = ObservationDB(DEFAULT_DB_PATH)
    obs = LivePublicObserver(db=db)
    t0 = time.time()
    connected = False
    err = None
    try:
        log = obs.run(duration_s=duration)
        connected = obs.counts["messages"] > 0 or obs.sm.get_state() in ("STREAMING", "SUBSCRIBED")
    except Exception as e:  # noqa: BLE001
        err = repr(e)
        log = []
    finally:
        final_state = obs.disconnect("burn-in complete")
    elapsed = round(time.time() - t0, 1)

    lat = obs.samples["latencies_ms"]
    lat_sorted = sorted(x for x in lat if isinstance(x, int))
    report = {
        "connected": bool(connected),
        "error": err,
        "endpoint_ws": config.APPROVED_TESTNET_WS,
        "endpoint_rest": config.APPROVED_TESTNET_REST,
        "environment": "testnet",
        "execution_enabled": config.HYPERLIQUID_EXECUTION_ENABLED,
        "mainnet_allowed": config.HYPERLIQUID_MAINNET_ALLOWED,
        "duration_s": elapsed,
        "btc_perp": (None if not obs.perp else
                     {"name": obs.perp.name, "asset_id": obs.perp.asset_id,
                      "sz_decimals": obs.perp.sz_decimals, "verified": obs.perp.verified}),
        "samples": obs.samples,
        "counts": obs.counts,
        "reconnects": obs.sm.reconnects,
        "final_state": final_state,
        "db_path": DEFAULT_DB_PATH,
        "db_rows": {t: db.count(t) for t in db.table_names()},
        "db_lineages": db.lineages(),
        "latency_ms": ({"n": len(lat_sorted), "min": lat_sorted[0],
                        "median": lat_sorted[len(lat_sorted) // 2], "max": lat_sorted[-1]}
                       if lat_sorted else None),
    }
    print("=== H1 LIVE BURN-IN REPORT ===")
    print(json.dumps(report, indent=2, default=str))
    db.close()
    return 0 if connected and not err else 1


if __name__ == "__main__":
    sys.exit(main())
