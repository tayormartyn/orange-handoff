# ORANGE — Historical OHLC Readiness Audit (Feb–Mar recap + May six-trade matching)

**Mode: HISTORICAL OHLC READINESS AUDIT — READ-ONLY. SINGLE-SESSION.** Date 2026-07-12 (~14:05Z).
Machine-readable: `historical_ohlc_readiness_audit.json`. **No matching was run** (per rule: only if
already safe AND supported end-to-end — see §5). No internet used. Listener **PID 23012
running/untouched**. Gates `PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY` unchanged; v0.3 live
labels untouched; v0.4 offline.

## 0. Live-priority gate
Store checked at ~13:54Z: max msg id **45649** — the known IRRELEVANT admin/relay request (captured
live during the indicator audit); nothing after it; market closed until ~22:00Z. **No XAU trigger →
audit proceeded.** Cursor remains 45648 (45649 formally examined at Cycle 006).

## 1. Local OHLC/price assets found (complete inventory)

| asset | coverage | quality |
|---|---|---|
| `Downloads/XAUUSD_1M_2026-06-*.csv.csv` (4 files) + `XAUUSD_5M_2026-06-01_to_2026-06-30` | June 2026, 1m + 5m | the sprint's import set (already used for the 34-setup matching) |
| `Downloads/XAUUSD_1M_2026-06-30…07-10 window files` (4) + `PEPPERSTONE_XAUUSD, 1.csv` (2) | Jun-30→Jul-10 windows, 1m | sprint S-series matching set |
| **`data/price_cache/XAUUSD/` tick store** (epoch-ms bid/ask ticks, hour files; **month dirs are 0-indexed** — verified from timestamps: `2026\01`=Feb, `2026\02`=Mar, `2026\04`=May) | Feb 2026: 12 days, partial hours · Mar 2026: 7 days, partial hours · **May 2026: day 22 (17h) + days 25–31 FULL 24h** · June 2026: 25 days | tick-level (better than 1m) where present; sparse hour coverage except late May/June |
| `raw/market_data/` | empty (.gitkeep) | — |

## 2. May six-trade readiness (FP-AUDIT-001 rows, gold only) — **ALL SIX MATCH-READY LOCALLY**

Details recovered from `Downloads/farouk_trade_audit.xlsx` (Row Audit sheet; widths reconcile with the
002B six-sample set 20/24/40/25/25/20):

| # | date/time UTC-ish | dir | entry zone | SL | TPs | audited outcome | OHLC needed (entry−60m → +48h) | local coverage |
|---|---|---|---|---|---|---|---|---|
| M1 | 2026-05-25 09:50 | SHORT | 4567–4575 | 4595 | 4560/4551/4530 | Win TP1 (+partials) | 05-25 08:50 → 05-27 10:00 | **FULL (ticks)** |
| M2 | 2026-05-26 10:26 | SHORT | 4533–4541 | 4565 | 4527/4522/4511 | Win ≥TP2 | 05-26 09:26 → 05-28 11:00 | **FULL (ticks)** |
| M3 | 2026-05-27 14:14 | SHORT | 4452–4460 | 4500 | 4440/4425/4390 | Win TP1 | 05-27 13:14 → 05-29 15:00 | **FULL (ticks)** |
| M4 | 2026-05-28 16:19 | SHORT | 4494–4510 | 4535 | 4483/4455/4390 | Managed profit | 05-28 15:19 → 05-30 17:00 | **FULL (ticks)** |
| M5 | 2026-05-29 11:30 | LONG | 4520–4527 | 4495 | 4540/4570/4580 | Managed win 90p→BE | 05-29 10:30 → 06-02 (48h trading) | **FULL** (ticks May-29–31 + June 1m CSVs) |
| M6 | 2026-05-29 14:25 | LONG | 4520–4530 | 4500 | 4550/4570/4580 | Win TP3 (2.2R) | 05-29 13:25 → 06-02 | **FULL** (same) |

**Why matching was still NOT run:** the tick store needs a small deterministic tick→1m aggregation
step to feed `outcome_matcher_v0_1.py` (which consumes caller-provided OHLC rows). That aggregator
does not exist yet — so the end-to-end path is not "already supported by existing matcher code".
**Recommendation (separate approved step):** write the tick→1m aggregator (pure arithmetic, ~50
lines), replay the six May trades through the existing matcher, and reconcile against the claim-based
audit R values. Optional cross-check export E (below) validates the tick-derived bars against
TradingView.

## 3. Feb–Mar recap readiness (FP-RECAP-001, 19 usable + 1 excluded) — **0/19 MATCH-READY**

Recap rows carry **dates only (no intraday times)** → each needs a full-day + 48h window. Tick-store
coverage on recap dates is absent or a few hours at best (Feb-19: 09–10h; Mar-12: 08–14h; Mar-18:
06–07h; Mar-25: 16–23h + Mar-26 00–04h) — **insufficient for every row**. The excluded 27-03
SL-5075 error row stays excluded. Full per-row table in the JSON (19 rows, each mapped to its
missing export window A–D).

## 4. Exact missing exports (Pepperstone XAUUSD, 1m, UTC — TradingView export, same recipe as June)

| id | instrument | TF | start UTC | end UTC | preferred filename | covers |
|---|---|---|---|---|---|---|
| **C** | XAUUSD (Pepperstone) | 1m | 2026-03-11 00:00 | 2026-03-20 00:00 | `XAUUSD_1M_2026-03-11_to_2026-03-20.csv` | 12-03, 17-03, 18-03 (+500p), **all three 19-03 rows incl. the documented posted-vs-actual SL-gap LOSS** |
| **D** | XAUUSD (Pepperstone) | 1m | 2026-03-20 00:00 | 2026-03-29 00:00 | `XAUUSD_1M_2026-03-20_to_2026-03-29.csv` | 20-03 ×2 (incl. LOSS), 25-03, 27-03 (+ the 19-03 48h tails) |
| **A** | XAUUSD (Pepperstone) | 1m | 2026-02-17 00:00 | 2026-02-25 00:00 | `XAUUSD_1M_2026-02-17_to_2026-02-25.csv` | 18-02, 19-02, 20-02 ×3, 24-02 (start) |
| **B** | XAUUSD (Pepperstone) | 1m | 2026-02-25 00:00 | 2026-03-05 00:00 | `XAUUSD_1M_2026-02-25_to_2026-03-05.csv` | 24-02 tail, 26-02, 27-02, **02-03 LOSS** |
| E (optional) | XAUUSD (Pepperstone) | 1m | 2026-05-25 00:00 | 2026-06-01 00:00 | `XAUUSD_1M_2026-05-25_to_2026-06-01.csv` | cross-check of the tick-derived May bars |

**Priority order:** **C first** (highest evidentiary density: the SL-gap loss row 19-03 — the central
caveat's only documented posted-vs-actual number — plus 4 more rows), then **D** (two losses + 48h
tails), then A, B. Value map: C+D+A+B = the Feb–Mar **85%-claim validation** + **+19 stop-width
samples become outcome-verified** (calibration upgrade); the May six need **no export** (local ticks
suffice; E optional). Lane-6 level validation needs none of these (it is a forward test).

## 5. What was deliberately NOT done
No matching run (rule §2); no tick→1m aggregator written (recommendation only); no internet/data
download; no detector change; no capture-spec change beyond this audit note; no v0.4 replay; Cycle-006
forward readiness untouched except the note that the May six-trade matching is now a shovel-ready
offline task.

## 6. Safety confirmation
Read-only audit (files read: batch JSONs, audit xlsx via stdlib zip/XML — no packages installed;
tick files sampled for timestamp verification). No execution built (broker/QST/cTrader/nano/copy/
demo/live absent); no permits/leases/orders; gates unchanged; no TradingView/Worker/R2/secret action;
no sizing fields (xlsx sizing columns were not extracted). `NOT_INTEGRATION_READY` unchanged.

## Next step
**Cycle 006 / XAU-F001 at the first real XAU post after tonight's ~22:00Z reopen** stays priority.
Offline, in order: (1) Martyn exports **C** then **D** (then A, B) per §4; (2) a separate approved
session writes the tick→1m aggregator and runs the **May six-trade deterministic match** from local
data; (3) Feb–Mar recap match once C/D (and A/B) land — the 85%-claim test.
