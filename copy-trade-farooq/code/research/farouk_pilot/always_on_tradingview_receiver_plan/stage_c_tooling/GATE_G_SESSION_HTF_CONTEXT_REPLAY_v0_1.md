# Gate G — Session + HTF Context Replay v0.1

**Mode:** OFFLINE. Session resolver + HTF bias resolver applied to the 3 Gate G candidates using the
imported XAUUSD 1m CSV. **Proxy / candidate-only.** `NOT_INTEGRATION_READY` unchanged.

## Results

| candidate | anchor (UTC) | session_label | session_conf | HTF proxy | 15m / 1h | HTF vs hint |
|---|---|---|---|---|---|---|
| ALIGNED_CHOCH_TO_A (LONG) | 04:12:01Z | ASIA_UTC_PROXY | UNCONFIRMED | **BEARISH_PROXY** | BEARISH / insufficient | ❌ opposes LONG |
| SWEEP_TO_CHOCH_CONTEXT (LONG) | 00:03:01Z | ASIA_UTC_PROXY | UNCONFIRMED | **BULLISH_PROXY** | BULLISH / insufficient | ✅ agrees LONG |
| BPR_TO_A_CONTEXT (SHORT) | 05:42:01Z | ASIA_UTC_PROXY | UNCONFIRMED | **BULLISH_PROXY** | BULLISH / insufficient | ❌ opposes SHORT |

## Notes

- **Session:** all three anchors sit in 00–08Z → `ASIA_UTC_PROXY`, all `SESSION_UNCONFIRMED`. Per the
  session policy, **Asia has no corpus clock window** and the timezone is unresolved, so this is a proxy
  and cannot satisfy the scorer's session factor.
- **HTF bias:** every 1h proxy was `NEUTRAL_OR_INSUFFICIENT_DATA` (only 8–13 aggregated 1h bars in an
  ~11.6h window; need ≥22). Combined proxies fell back to the 15m read (flagged weak).
- **HTF vs direction_hint:** only 1 of 3 agreed (SWEEP). Notably the ALIGNED CHoCH→A (which had the
  favourable-ish outcome) shows a **BEARISH** HTF proxy *against* its LONG hint — a caution flag, and a
  reminder these are proxies, not signals.
- These HTF proxies are **descriptive context only**; they were **not** added to the methodology score
  (the corpus defines no HTF rule to weight).

## Safety confirmations

- All proxy; candidate-only; no execution / order / broker / lot / account / risk / permit / lease.
- Offline; read-only CSV; no broker/cTrader/QST; no live download; no deploy.
- **`NOT_INTEGRATION_READY` unchanged.**
