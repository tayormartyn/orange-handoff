# Gate G — Chart Context Replay v0.1

**Mode:** OFFLINE. `chart_context_extractor_v0_1` applied to the 3 Gate G shadow candidates using the
imported XAUUSD 1m CSV. **All proxy / candidate-only.** `NOT_INTEGRATION_READY` unchanged.

## Extracted context

| candidate | session (proxy) | sweep_cand | struct_cand | disp_cand | disp ratio | fvg_cand (dir) | OB | HTF | context_confidence |
|---|---|---|---|---|---|---|---|---|---|
| ALIGNED_CHOCH_TO_A (04:12Z) | ASIA_UTC_PROXY | false | false | **false** | 1.91 | true (bullish) | not claimed | MISSING | LOW_PROXY |
| SWEEP_TO_CHOCH_CONTEXT (00:03Z) | ASIA_UTC_PROXY | false | false | **true** | 4.18 | true (bullish) | not claimed | MISSING | MEDIUM_PROXY |
| BPR_TO_A_CONTEXT (05:42Z) | ASIA_UTC_PROXY | false | false | **true** | 11.40 | true (bullish) | not claimed | MISSING | MEDIUM_PROXY |

## Notes

- **Session:** all three anchors fall in the 00–08Z bucket → `ASIA_UTC_PROXY`, every one carrying
  `TIMEZONE_POLICY_UNCONFIRMED`. Not a confirmed session.
- **Displacement proxy:** found for 2 of 3 (ratios 4.18, 11.40 ≥ 2.0× ATR); the aligned CHoCH→A was just
  under threshold (1.91). All flagged `NEEDS_HUMAN_REVIEW` (corpus size threshold UNKNOWN).
- **FVG proxy:** a bullish 3-candle imbalance near each anchor (all `NEEDS_HUMAN_REVIEW`, fill rule
  UNKNOWN). Not confirmed Farouk FVGs.
- **Order block:** **not claimed for any candidate** (`MISSING_ORDER_BLOCK_DETECTOR`) — by design.
- **HTF bias:** unavailable from a single 1m file (`MISSING_HTF_DATA`) for all.
- The extractor's crude sweep/structure proxies did **not** fire here; this does not contradict the raw
  TradingView CHoCH/Sweep alerts (the proxy is a coarse close-beyond check and never overrides the alert).

## Safety confirmations

- All proxy; candidate-only; no execution / order / broker / lot / account / risk / permit / lease field.
- Offline; read-only CSV; no broker/cTrader/QST; no deploy.
- **`NOT_INTEGRATION_READY` unchanged.**
