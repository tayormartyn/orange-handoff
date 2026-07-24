# Feb–Mar Export C — Import Validation (1m export MISSED the window; 60m fallback checks run)

**Mode: EXPORT C IMPORT + SAFE MATCH ATTEMPT — REVIEW-ONLY. SINGLE-SESSION.** Date 2026-07-12
(~14:40Z). Machine-readable: `febmar_export_c_import_validation.json`. **Full deterministic matching
was NOT run** (see §2 — the 1m file does not cover the window; 60m cannot sequence). Listener
**PID 23012 running/untouched**; live gate clean (store max still 45649 = known IRRELEVANT; market
closed). Gates `PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY` unchanged; CSVs read raw (no
Excel).

## 1. What arrived vs what it contains (the central finding)

| file (Downloads) | filename says | content ACTUALLY is | verdict |
|---|---|---|---|
| `XAUUSD_1M_2026-03-11_to_2026-03-20.csv.csv` (1,401,508 B, 20,423 rows) | March 1m | **1m, 2026-06-21 22:01Z → 2026-07-10 20:54Z** (epoch-verified; prices ~4100–4160 = July levels) | **EXPORT FAILED for March** — TradingView exported its most recent ~20k 1m bars; **1m history does not reach back to March 2026** (all four June 1m exports are the same 1,401,508 B for the same reason: fixed ~20k-bar dumps) |
| `PEPPERSTONE_XAUUSD, 60.csv` (141,218 B, 1,996 rows, exported 5 min earlier) | (60-minute) | **60m, 2026-03-10 16:00Z → 2026-07-10 20:00Z**, hourly cadence with weekend gaps | **COVERS the March window — but at 60m, below the 1m requirement** |

Header format (both): `time,open,high,low,close,Bull Engulf,Bear Engulf,Volume,CRSI` — epoch-seconds
UTC, standard TradingView export.

**Imported to project price_data (raw copies, content-true names, sha256):**
- `stage_c_tooling/price_data/XAUUSD_1M_2026-06-21_to_2026-07-10_MISLABELED_EXPORT_C.csv`
  (sha256 2E0D565D…53AF) — kept: it usefully extends the sprint's 1m coverage across Jun-21→Jul-10
  (incl. the Jul-1 loss day) even though it is NOT March.
- `stage_c_tooling/price_data/XAUUSD_60M_2026-03-10_to_2026-07-10.csv` (sha256 DD4F875F…FF59).
The canonical name `XAUUSD_1M_2026-03-11_to_2026-03-20.csv` was deliberately NOT used — storing a
July file under a March name would poison provenance.

## 2. Why full matching did not run
(a) No 1m data exists for the window; (b) the 60m bars cannot adjudicate TP/SL order inside violent
hours (Mar-18/19 were crash days with $50–90 hourly ranges); (c) recap rows carry dates only — no
entry timestamps; (d) the existing `outcome_matcher_v0_1` is a short-horizon excursion tool, not a
recap bar-walker. Forcing any of this would produce guessed sequences — forbidden.

## 3. Bounded 60m support checks (deterministic range facts only — NOT outcome adjudication)

| recap row | 60m finding | verdict at 60m |
|---|---|---|
| **12-03 LONG 5050–5035, claim MISSED** | all of Mar-12 stayed above 5050 (window low 5009.59 occurs later); zone first traded **Mar-13 14:00** | **MISSED SUPPORTED for the posting day**; zone filled next day (consistent with an expired/removed limit) |
| **17-03 LONG 4992–4980 / SL 4966, claim WIN +300p all TPs** | fill first-touch Mar-17 10:00 → **+$30 target (5022) traded Mar-17 12:00**; SL 4966 first traded Mar-18 10:00 (next day, after target) | **WIN +300p SUPPORTED** (bar-level sequence decisive: target strictly before SL) |
| **18-03 SHORT 4870 / SL 4925, claim WIN +500p** | first Mar-18 bar spans BOTH 4870 and 4925 (crash-day range); −$50 target (4820) traded Mar-18 20:00; post-fill low 4502.69 | target traded, but fill/SL share one bar → **AMBIGUOUS_SEQUENCE** (needs ≤5m + entry time) |
| **19-03 LONG 4775 / posted SL 4767 / "SL hit at 4762" — THE GAP ROW** | zone first traded **Mar-19 06:00**; the SAME hourly bar trades through **4767 AND 4762, low 4747.84**; subsequent bars fall to **4477.38** | **SL-GAP CLAIM SUPPORTED**: a 4762 exit was physically available — price indisputably traded through both the posted SL and the claimed actual exit (and ~$15 beyond within the hour). The LOSS itself is directionally confirmed (market collapsed ~$300 after the zone traded). Intra-bar fill→stop ordering: AMBIGUOUS_SEQUENCE at 60m, but reachability does not depend on it (4762 also traded in later bars regardless) |
| **19-03b SHORT 4619 / SL 4708, claim +400p** | window-start bar spans entry and SL (post-crash volatility); −$40 target traded Mar-19 12:00; low 4477.38 | target traded (**+400p plausible**) but **AMBIGUOUS_SEQUENCE** without entry time + finer bars |
| **19-03c SHORT 4624 / SL 4708, claim +350p** | same structure | same — **AMBIGUOUS_SEQUENCE** |

Score so far at 60m: **2 SUPPORTED (17-03 win, 12-03 missed) + 1 KEY SUPPORTED (19-03 SL-gap
reachability + loss) + 3 AMBIGUOUS_SEQUENCE; 0 REFUTED.** Nothing contradicts the recap — consistent
with the 0-contradicted history.

## 4. Exact next tasks
1. **Export C-5M (Martyn):** XAUUSD (Pepperstone) **5-minute**, 2026-03-10 00:00 → 2026-03-29 00:00
   UTC → `XAUUSD_5M_2026-03-10_to_2026-03-29.csv`. TradingView's 5m depth may reach March (the June
   5m export shows ~6x longer depth per file); 5m matches the June-ledger fallback precedent (23/34
   setups were adjudicated on 5m). If 5m also cannot reach March, export **15m** as the coarse
   fallback and accept wider AMBIGUOUS margins.
2. **Matcher task (separate approved session):** author `recap_bar_walk_matcher` — zone-side-aware
   first-touch (handles price already beyond entry), TP/SL bar-walk, AMBIGUOUS_SEQUENCE on same-bar
   conflicts, date-only anchors with whole-day sensitivity; reusable for the May six-trade run
   (tick→1m aggregation feeds the same walker).
3. Same-recipe checks extend to D/A/B rows once their exports land (the 60m file already covers the
   D window for coarse checks; February needs its own export — the 60m file starts Mar-10).

## 5. Safety confirmation
Raw CSV reads + file copies + deterministic arithmetic only; no live scoring; v0.2/v0.3/v0.4
untouched; no execution built (broker/QST/cTrader/nano/copy/demo/live absent); no permits/leases/
orders; gates unchanged; no TradingView/Worker/R2/secret action (the exports were made by Martyn's
own hand). `NOT_INTEGRATION_READY` unchanged.

## Next step
**Cycle 006 / XAU-F001 at tonight's ~22:00Z reopen stays priority.** Offline: Export C-5M attempt
per §4.1; then the recap bar-walk matcher; the May six-trade local match remains shovel-ready.
