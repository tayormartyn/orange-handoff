# Gate G — Shadow Candidate Outcome Matching v0.1

**Mode:** OFFLINE. Status: **✅ COMPLETE — 3/3 candidates outcome-matched against real XAUUSD 1m data.**

**Data:** `price_data/XAUUSD_1M_2026-07-08_2026-07-09_IMPORT_HERE.csv` (1145 candles, 1m, UTC, source
PEPPERSTONE_TradingView_export). All three candidates `data_quality: FULL`, no warnings.

**Reading these numbers:** MFE = max favourable excursion, MAE = max adverse excursion, both in **price
units (USD/oz)** oriented to the candidate's `direction_hint`. final = close-at-horizon minus entry,
oriented to the hint. **These are descriptive price statistics — NOT PnL, NOT pips-as-profit, NOT
position sizing, NOT a trade instruction.** MAE ≤ 0 = move against the hint; MFE ≥ 0 = move in favour.

## Candidate 1 — ALIGNED_CHOCH_TO_A (the MEDIUM candidate)

- candidate_id `ALIGNED_CHOCH_TO_A-0000`, direction_hint **LONG**
- anchor_time_utc `2026-07-09T04:12:01Z`, entry_reference_price **4063.96**, data_quality **FULL**

| Horizon | MFE | MAE | final close Δ |
|---|---|---|---|
| 15m | +0.15 | −6.76 | −4.85 |
| 30m | +0.63 | −6.76 | −4.96 |
| 60m | +12.07 | −7.54 | +8.13 |
| 120m | **+35.49** | −7.54 | **+25.56** |

Flags: candidate_only=true; execution_allowed / broker_execution_allowed / qst_allowed / order_intent /
risk_sizing_allowed = **false**.

## Candidate 2 — SWEEP_TO_CHOCH_CONTEXT (LOW context)

- candidate_id `SWEEP_TO_CHOCH_CONTEXT-0000`, direction_hint **LONG**
- anchor_time_utc `2026-07-09T00:03:01Z`, entry_reference_price **4080.83**, data_quality **FULL**

| Horizon | MFE | MAE | final close Δ |
|---|---|---|---|
| 15m | +8.87 | −3.50 | +3.94 |
| 30m | +8.87 | −6.87 | −2.29 |
| 60m | +8.87 | −14.28 | −12.81 |
| 120m | +8.87 | **−18.57** | −5.38 |

Flags: all safety flags false (as above).

## Candidate 3 — BPR_TO_A_CONTEXT (LOW context)

- candidate_id `BPR_TO_A_CONTEXT-0000`, direction_hint **SHORT**
- anchor_time_utc `2026-07-09T05:42:01Z`, entry_reference_price **4074.97**, data_quality **FULL**

| Horizon | MFE | MAE | final close Δ |
|---|---|---|---|
| 15m | +1.15 | −9.28 | −8.24 |
| 30m | +1.15 | −24.48 | −14.55 |
| 60m | +1.15 | −31.87 | −24.80 |
| 120m | +1.15 | **−36.16** | **−34.75** |

Flags: all safety flags false (as above).

## Plain-English summary

- **MEDIUM CHoCH→A (LONG): eventually moved favourably, after early adverse heat.** It first dipped
  ~−6.8 within 30m (close −4.96), then followed through in the hinted LONG direction: +8.13 at 60m and
  **+25.56 close / +35.49 peak by 120m**. Directionally it agreed with the hint — but only after a
  meaningful drawdown a real position would have had to survive.
- **LOW context #1 Sweep→CHoCH (LONG): did NOT hold.** A brief favourable spike (+3.94 at 15m) then
  reversed to adverse (−12.81 at 60m), ending −5.38 at 120m with MAE −18.57. Weak / failed.
- **LOW context #2 BPR→A (SHORT): the hint was wrong.** Price rose against the short throughout —
  MFE only +1.15, MAE −36.16, close **−34.75** at 120m. Clear miss.
- **Was adverse excursion significant?** **Yes, for all three.** Even the "good" LONG carried ~−6.8
  early heat; the failed short ran ~−36 against.
- **Directional agreement at 120m close: 1 of 3** (only the MEDIUM CHoCH→A).

## Trade-ready?

**No.** n=3 (1 eventual-hit-with-drawdown, 1 fade, 1 clear miss), single session, no validated campaign
logic, no statistical basis. One favourable case — with early adverse heat — is an *observation to keep
studying*, not an edge. See `NO_TRADE_READINESS_FINDINGS_v0_2.md`.

## Safety confirmations

- Candidate-only; no execution / order intent / broker route / lot size / account ID / risk sizing /
  permit / lease / order anywhere. Numbers are descriptive price stats, not PnL.
- Offline; read-only CSV; no broker/cTrader/QST; no live download.
- **`NOT_INTEGRATION_READY` unchanged.**
