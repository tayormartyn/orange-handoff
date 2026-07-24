# Gate G — Order-Block Proxy Replay v0.1

**Mode:** OFFLINE. `order_block_proxy_detector_v0_1` applied to the 3 Gate G candidates using the imported
XAUUSD 1m CSV. **Proxy-only; requires_human_review=true; no confirmed OB claimed.**
`NOT_INTEGRATION_READY` unchanged.

## Results

| candidate | hint | OB proxy found | proxy_direction | zone (body) | disp ratio | mitigation | dist from anchor | confidence |
|---|---|---|---|---|---|---|---|---|
| ALIGNED_CHOCH_TO_A | LONG | **No** | — | — | — | — | — | LOW |
| SWEEP_TO_CHOCH_CONTEXT | LONG | **Yes** | BULLISH_OB_PROXY | 4076.28–4076.89 | 2.79× | **fresh** (not re-entered) | 5.0 min | LOW |
| BPR_TO_A_CONTEXT | SHORT | **Yes** | BEARISH_OB_PROXY | 4071.48–4072.05 | 4.79× | **touched → degraded/"spent"** | 13.0 min | LOW |

## Notes

- **ALIGNED CHoCH→A: no OB proxy** — no qualifying displacement proxy of the required (bullish) colour
  before its anchor. So the detector correctly returns not-found rather than forcing a zone.
- **SWEEP_TO_CHOCH: fresh bullish OB proxy** (zone not re-entered before the anchor). Still LOW confidence,
  NEEDS_HUMAN_REVIEW; FVG-left-behind / first-tap / HTF alignment all left in `missing_evidence`.
- **BPR_TO_A: bearish OB proxy but mitigated** — price re-entered the zone after displacement, so the
  proxy is flagged degraded/possibly "spent" (a *weak*-OB signature per corpus).
- **Every record:** `requires_human_review=true`, confidence LOW, zone bounds descriptive only (no
  entry/SL/TP). **No confirmed Farouk order block asserted.**

## Reading

Even where OB proxies appear, they are unreviewed, LOW-confidence, and one is already mitigated. The
detector's "best" methodology candidate (ALIGNED) has **no** OB proxy at all. This is consistent with
"nothing trade-ready."

## Safety confirmations

- Proxy-only; candidate-only; no execution / order / broker / lot / account / risk / permit / lease.
- Offline; read-only CSV; no broker/cTrader/QST; no deploy.
- **`NOT_INTEGRATION_READY` unchanged.**
