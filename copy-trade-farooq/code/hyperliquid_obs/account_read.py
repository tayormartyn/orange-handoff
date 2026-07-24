"""
H2-LITE — PUBLIC account-state read by wallet ADDRESS (connectivity confirmation only).

This reads a given PUBLIC wallet address's clearinghouse / spot state via the PUBLIC /info
endpoint. The address is public input (not a secret); the request body carries ONLY a type +
the address. There is NO signing, NO auth header, NO key, and NO order/transfer/withdrawal
path. Reading is allowed against BOTH mainnet and testnet because address-based /info data is
public on either; we report which network the address actually resolves on.

This module is deliberately SEPARATE from the H1 market-data safety gate (which is testnet-
only). H1's testnet-only guarantees are unchanged; this path has its own narrower gate:
no signing key in process + execution locked off + a validated public address only.
"""
from __future__ import annotations
import json
import re
import urllib.error
import urllib.request

from . import config, safety

# Public /info bases. The address-based reads below are public on either network.
TESTNET_REST = config.APPROVED_TESTNET_REST
MAINNET_REST = "https://api." + "hyperliquid" + ".xyz"      # public /info host (no signing here)

_ADDR = re.compile(r"^0x[0-9a-fA-F]{40}$")


class AccountReadError(Exception):
    pass


def assert_public_read_safety(address):
    """Narrow gate for the public address read. Does NOT permit anything beyond a public read."""
    if config.HYPERLIQUID_EXECUTION_ENABLED is not False:
        raise safety.HyperliquidSafetyError("execution is not exactly False")
    # observation must run with NO key loaded — same hard guarantee as H1
    safety.assert_no_signing_key_in_process()
    if not isinstance(address, str) or not _ADDR.match(address):
        raise AccountReadError(f"not a valid 42-char public wallet address: {address!r}")
    # a 40-hex public address must never be mistaken for / accompanied by a 64-hex private key
    if re.match(r"^0x?[0-9a-fA-F]{64}$", address):
        raise AccountReadError("refused: value looks like a private key, not a public address")
    return True


def _info_post(base, payload, timeout=10):
    url = base.rstrip("/") + config.APPROVED_REST_PATHS[0]   # always /info, never a signing route
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8")), r.status, url


def read_perp_state(address, base):
    """Public clearinghouseState (perp account value, margin, positions) for an address."""
    return _info_post(base, {"type": "clearinghouseState", "user": address})


def read_spot_state(address, base):
    """Public spotClearinghouseState (spot token balances) for an address."""
    return _info_post(base, {"type": "spotClearinghouseState", "user": address})


def _summarise(perp, spot):
    ms = (perp or {}).get("marginSummary", {}) if isinstance(perp, dict) else {}
    acct_value = ms.get("accountValue")
    withdrawable = (perp or {}).get("withdrawable") if isinstance(perp, dict) else None
    positions = (perp or {}).get("assetPositions", []) if isinstance(perp, dict) else []
    balances = (spot or {}).get("balances", []) if isinstance(spot, dict) else []
    nonzero_balances = [b for b in balances
                        if _f(b.get("total")) not in (None, 0.0)]

    def nz(x):
        return _f(x) not in (None, 0.0)

    has_state = (nz(acct_value) or nz(withdrawable) or bool(positions) or bool(nonzero_balances))
    return {
        "account_value": acct_value,
        "withdrawable": withdrawable,
        "open_positions": len(positions),
        "position_coins": [p.get("position", {}).get("coin") for p in positions
                           if isinstance(p, dict)],
        "spot_balances": [{"coin": b.get("coin"), "total": b.get("total")}
                          for b in nonzero_balances],
        "has_state": has_state,
    }


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def resolve_account(address):
    """Read the address on BOTH networks (public) and report which it resolves on."""
    assert_public_read_safety(address)
    out = {"address": address, "networks": {}}
    for net, base in (("mainnet", MAINNET_REST), ("testnet", TESTNET_REST)):
        rec = {"endpoint": None, "connected": False, "error": None}
        try:
            perp, status, url = read_perp_state(address, base)
            rec["endpoint"] = url
            rec["http_status"] = status
            rec["connected"] = status == 200
            spot = None
            try:
                spot, _, _ = read_spot_state(address, base)
            except (urllib.error.URLError, json.JSONDecodeError, OSError):
                spot = None
            rec.update(_summarise(perp, spot))
        except Exception as e:  # noqa: BLE001 — surface the failure per-network, keep going
            rec["error"] = repr(e)
        out["networks"][net] = rec
    resolved = [n for n, r in out["networks"].items() if r.get("has_state")]
    out["resolves_on"] = resolved
    return out


def main(address):
    report = resolve_account(address)
    print("=== H2-LITE PUBLIC ACCOUNT-STATE READ ===")
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else config.TARGET_PERP_NAME))
