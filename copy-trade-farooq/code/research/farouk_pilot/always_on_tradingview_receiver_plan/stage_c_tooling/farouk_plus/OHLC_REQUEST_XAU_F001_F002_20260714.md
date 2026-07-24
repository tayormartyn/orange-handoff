# OHLC Export Request — XAU-F001-20260714 + XAU-F002-20260714

**One export covers both campaigns.** Please produce the standard Pepperstone TradingView export:

- **Symbol:** XAUUSD (PEPPERSTONE feed)
- **Timeframe:** 1 minute
- **Timezone:** UTC (export chart timezone must be UTC)
- **Window:** **2026-07-14 07:30:00 UTC → 2026-07-16 13:30:00 UTC**
  (≥60 min before the XAU-F001 entry message 45711 @ 08:38:06Z; runs through all management of both
  campaigns and the full 48-hour deterministic-matching window after the XAU-F002 entry @ 13:26:21Z)
- **Format/destination:** cleaned CSV per `XAUUSD_OHLC_IMPORT_SCHEMA_v0_1.md` →
  `stage_c_tooling/price_data/` (follow `PRICE_DATA_IMPORT_INSTRUCTIONS.md`)

Per-campaign minimum sub-windows (if the full window is impractical):
- XAU-F001 (BUY 4007-4019, closed 12:32:09Z): 2026-07-14 07:30Z → 2026-07-16 09:00Z
- XAU-F002 (SELL 4084-4094, open at commit): 2026-07-14 12:15Z → 2026-07-16 13:30Z

On import, the deterministic matcher resolves: outcome_status for both campaigns, F2 zone-touch
formation counts (v0.3 recheck, weight applied as ratified), scratch_trigger after the SL_TO_ENTRY
instructions, tp_banking posted-before-touch flags, and claim_vs_achievable (90/130/700 pips F001;
100/140 pips F002). **Same-bar conflicts stay AMBIGUOUS_SEQUENCE unless finer evidence resolves them.**
48h SLA per the ledger schema. Never fabricate price data — no data → NO_DATA.
