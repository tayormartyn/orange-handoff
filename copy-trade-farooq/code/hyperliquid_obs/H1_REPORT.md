# H1 + H2-LITE — Hyperliquid public observation report

**Package:** `hyperliquid_obs/` (isolated, pure-stdlib, no third-party deps)
**Date:** 2026-06-29
**Scope built:** H1 (public market-data observation, offline + live burn-in) and H2-LITE
(public address-based account-state read). H2/H3/H4, faucet, and any signing wallet remain
PARKED and unbuilt.

## Safety posture (all enforced)
- **No key loaded** — `safety.assert_no_signing_key_in_process()` scans the live process env
  and `sys.modules`; verified empty before every connection. Observation needs no key.
- `HYPERLIQUID_EXECUTION_ENABLED = False` (identity check), `HYPERLIQUID_MAINNET_ALLOWED = False`.
- **No trading path** — `source_scan.scan_no_trading_path()` walks all 14 package files and
  finds zero order/cancel/transfer/deposit/withdrawal/signing references and no signing
  endpoint path. This test BLOCKS the suite; a planted `place_order` def is caught.
- **Isolated store** — `hyperliquid_obs/data/hyperliquid_observation_v1.db`, append-only
  (engine triggers), every row stamped `data_lineage = hyperliquid_testnet_public_marketdata`.
  Never reads/writes gold/Telegram/campaign evidence.

## STEP 1 — offline build (proven)
`python hyperliquid_obs/tests/test_h1_offline.py` → **45/45 passed**. Covers: safety gates,
endpoint policy, BTC-perp identification from returned metadata (not assumed), book/trade
classification (admissible / crossed / stale / duplicate / out-of-order / one-sided / empty /
invalid), the WS state machine + reconnect re-walk, the isolated append-only DB, deterministic
replay (identical input → identical logical hash), isolation from campaign evidence, and the
no-trading-path source scan.

## STEP 2 — live public market-data burn-in (testnet)
- **Connected: YES.** WS `wss://api.hyperliquid-testnet.xyz/ws` (public, no auth/header/key).
  REST `https://api.hyperliquid-testnet.xyz/info` (public POST).
- **BTC perp identified from LIVE metadata:** name `BTC`, asset_id **3**, szDecimals 5
  (resolved from the returned universe of 208 perps — never assumed; note the live index 3
  differs from the offline fixture's 0, confirming we resolve rather than hardcode).
- **Live sample:** allMids BTC ≈ 59713; book best bid 59682 / best ask 59744; 36 live trades
  streamed (e.g. side B 59722 @ 0.00018).
- **Counts (60s run):** 12 book updates (all admissible), 36 trades (all admissible), 21 WS
  messages, **0 reconnects**, clean `CLOSED`.
- **Latency (local_recv − exch_ts):** min 831 / median ~900 / max 1198 ms.
- Reconnect path is implemented and unit-proven offline; no drop occurred live, so it did not
  trigger.

## H2-LITE — public account-state read
Address (public, not a secret): `0x35b68664a913e20f853365dd8a45b57d5f49ae5e`
- **API connected: YES**, HTTP 200 structured responses on BOTH mainnet
  (`api.hyperliquid.xyz/info`) and testnet — public, no auth, no signing.
- **Balance / positions:** `accountValue 0.0`, `withdrawable 0.0`, no perp positions, empty
  spot balances, staking 0.0, no vault equity, portfolio history flat 0.0 — on BOTH networks.
- **Resolves on:** neither (no funds present). The ~$26 expected was **not** visible on this
  address. The connectivity proof succeeded; the address simply holds nothing on Hyperliquid.
  Likely the funds are on a different wallet, or not yet bridged/deposited to Hyperliquid.
- This path is a SEPARATE, narrower gate from the H1 testnet-only market-data gate; H1's
  testnet-only guarantee is unchanged.

## Isolation / non-interference (verified after all live runs)
- Gold/campaign tree: 93 hashed artifacts, **0 changed/added/removed = INTACT**.
  `prompt_lock` sha256 `3dfe482f09caf1fe0e698a4aadd76c3ab83b394bf860f8902256a4b462b1e33c`.
- Telegram listener (PID 16564) running, untouched.
- Crypto data only in its own isolated DB (single lineage).

## Parked (do NOT build without separate approval)
H2 (full account observation), H3 (testnet orders), H4 (automated mgmt), the faucet / any
mainnet deposit, and loading any signing/agent wallet.
