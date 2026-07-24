# Step 6A — J24 Deterministic Rematch (screenshot-recovered entry): **VERIFIED_WIN**

**Mode: J24 DETERMINISTIC REMATCH ONLY.** Observation-only. Date 2026-07-11.
Listener PID 87988 untouched. Deterministic OHLC matching is the authority; the screenshot evidence only
supplied the missing *input* (his fill). Append-only: the Day-4/Day-5 INSUFFICIENT_DATA records for J24 are
preserved untouched — this is a **revision-2** adjudication on new evidence. No execution surface; gates
`PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY` unchanged.

## 1. Inputs

SHORT @ **4132.02** (MT5 position widgets on msgs 45015/45017/45021, sha256-addressed — Step-6 recovery).
No hard SL was ever posted (only the "my sellzone is 4140" note); "sl to entry" instructed 10:25:04Z.
Claims: 70 pips @10:43:25Z · 100 pips tp2 @10:57:09Z · 170 pips @12:14:10Z. Existing **1m** Pepperstone
coverage fully spans Jun-23 — used directly (no new data needed).

## 2. Deterministic results (1m)

| check | result |
|---|---|
| fill plausibility | **PLAUSIBLE** — 7 one-minute bars contain 4132.02 between 10:02–10:20Z (position provably open by the 10:20:43Z message) |
| 70p level (4124.99) | **touched 10:42Z** — 1 min before his message; 77.6p achieved by claim time |
| 100p level (4122.02) | **touched 10:51Z** — 6 min before his message; 119.6p by claim time |
| 170p level (4114.99) | **touched 12:13Z** — 1 min before his message; 189.5p by claim time |
| MFE / MAE from fill | **267p** (low 4105.29) / 85p (high 4140.57 — right at his stated 4140 sellzone) |
| hard SL | none existed → nothing to violate |
| **status** | **VERIFIED_WIN (1m-confirmed)** — claim verdict SUPPORTED, widget-exact |

**Follower-divergence caveat (preserved for R6, third quantified case):** after the 10:25Z "sl to entry"
instruction, price returned to the fill price at **10:34Z** — a follower with SL exactly at 4132.02 would
have been scratched flat *before* the 267-pip move. His own position provably survived to +170p (widgets)
— his stop sat elsewhere or his UTC+3 feed differed. His-outcome ≠ follower-outcome again; logged as
`fill_divergence_preserved_for_R6 = true` in the JSON, strictly as an expectancy-model input — never an
execution artefact.

## 3. Updated final June counts (strict 30 setups / 33 executions / ~24 grouped campaigns)

| status | count |
|---|---|
| VERIFIED_WIN | **19** (was 18; J24 upgraded) |
| VERIFIED_LOSS | 2 |
| PARTIAL | 9 |
| CONTRADICTED / AMBIGUOUS_INTRABAR | 0 / 0 |
| **INSUFFICIENT_DATA** | **0** (was 1) — **June is now 100% adjudicated** |

**Cumulative sprint sample: 34 trades matched / 18 sessions — 21 VERIFIED_WIN · 3 VERIFIED_LOSS ·
10 PARTIAL · 0 CONTRADICTED · 0 INSUFFICIENT** (11 × 1m-confirmed, 23 × 5m-fallback).

## 4. Safety confirmation

Offline deterministic run on already-imported data; no broker/QST/cTrader/nano/copy/demo/live execution;
no permits/leases/orders; gates unchanged; listener PID 87988 running (start 2026-07-10 21:54:45
unchanged); no TradingView/Worker/R2/secret action; nothing promoted to trade-ready.
`NOT_INTEGRATION_READY` unchanged.

## Next step

Fold the three quantified his-vs-follower divergence cases (J24 BE-scratch divergence, J30 below-zone fill,
J11 realised-vs-claimed) into the **R6 follower-fill expectancy design**, and continue daily forward cycles
(Cycle 002 → XAU-F001 on the next gold-trades activity).
