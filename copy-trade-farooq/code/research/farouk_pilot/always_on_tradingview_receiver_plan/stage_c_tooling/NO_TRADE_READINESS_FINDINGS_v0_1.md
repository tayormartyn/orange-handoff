# No-Trade Readiness Findings v0.1

**Mode:** OFFLINE FINDINGS. Candidate-only. **This document authorises nothing.** It records why the
evidence does **not** support trading and keeps `NOT_INTEGRATION_READY` correct.

## Verdict: ⛔ NOT trade-ready — observation only

The shadow-candidate detector v0.1 found **3 candidates** (1 MEDIUM, 2 LOW) and **20 disqualified
contradictory clusters** across the single Gate G window. That is not a basis to trade.

## Why not (evidence gaps)

1. **No price/outcome data.** Every candidate is a *sequence of alerts*, never paired with what price
   did next. Direction hints are unverified.
2. **Tiny, one-dimensional sample.** One ~11.6 h window, one symbol (XAUUSD/3m), one session.
3. **Directional ambiguity dominates.** 20 contradictory clusters vs 3 candidates (~6.7:1).
4. **Highest-grade families absent.** A+ / A+ or better = 0, A+++ = 0, BPR formed = 0. The trade-quality
   trigger (A+) has not been observed at all yet (H1 mirror still waiting).
5. **Best candidate is n=1.** The one MEDIUM aligned CHoCH→A (04:00Z→04:12Z) is a single instance with
   no repeat or confirmation.

## What is explicitly NOT a trade signal

- Engulfing→A (co-firing / noise), ANY_ALERT clusters, A alone, BPR tapped alone, Sweep alone.
- Any contradictory cluster (disqualified by design).
- Any candidate at LOW confidence.
- Even MEDIUM candidates — MEDIUM here means "worth watching in a future observation study," not
  "actionable."

## Hard stops (unchanged)

No broker/cTrader/QST connection; no permits/leases/orders; no execution-gate change; no risk-policy
change; no order intent; no lot size; no account binding. `NOT_INTEGRATION_READY` remains unchanged.

## Status

No-trade posture confirmed. Continue capture-only observation; keep H1/H2 mirrors collecting the rare
families.
