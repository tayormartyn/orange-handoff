# Feb–Mar Export C/D — 15m Import + Recap Bar-Walk Match Report

**Mode: 15M HISTORICAL IMPORT + SAFE RECAP MATCH — REVIEW-ONLY. SINGLE-SESSION.** Date 2026-07-12
(~15:20Z). Machine-readable: `febmar_export_cd_15m_match_results.json`. Matcher:
`tools/recap_bar_walk_matcher_v0_1.py` (new, small, deterministic, review-only). Listener **PID 23012
running/untouched**; live gate clean (store max still 45649 = known IRRELEVANT; market closed).
Gates `PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY` unchanged; CSV read raw (no Excel).
**15m is FALLBACK precision: verdicts are *_AT_15M and never upgrade the June-ledger 1m tier.**

## 1. Import validation — the 15m export is GENUINE March data

| check | result |
|---|---|
| file | `Downloads/XAUUSD_15M_2026-03-10_to_2026-03-29.csv.csv` (561,911 B) |
| cadence | 15-minute confirmed (900s steps; 4,500s gaps at daily maintenance breaks; weekend gaps) |
| actual content window | **2026-03-09 20:15Z → 2026-07-10 20:45Z** (8,057 rows; first bars price ~5139 = March levels ✓) |
| covers Export C (Mar-11→20) | YES, fully |
| covers Export D (Mar-20→29) | YES, fully |
| columns / tz | `time` (epoch s, UTC), OHLC, engulf flags, volume, CRSI — standard TradingView |
| imported as | `stage_c_tooling/price_data/XAUUSD_15M_2026-03-09_to_2026-07-10.csv` (content-true name; sha256 E06F0CE2…19DA; raw copy, unmodified) |

## 2. Matcher (created this step — task-4 provision)
`recap_bar_walk_matcher_v0_1.py`: zone-side-aware first touch (AMBIGUOUS_ENTRY when the day opens
at/through the entry boundary) · date-only anchors (fill sought on the anchor date; walk = 48 trading
hours) · claim target measured from the first-touched zone boundary · **same-bar conflicts →
AMBIGUOUS_SEQUENCE, intra-bar order never guessed** · unknown stays UNKNOWN · hard-wired
candidate_only/executable=False. The excluded 27-03-err row (SL 5075 data error) was never matched.

## 3. Results — all 10 covered rows (Export C: 6, Export D: 4)

| row | claim | 15m verdict |
|---|---|---|
| 12-03 LONG 5035–5050 | MISSED | **SUPPORTED** — zone untraded on Mar-12; first traded Mar-13 14:45 |
| 17-03 LONG 4980–4992 / SL 4966 | WIN +300p all TPs | **SUPPORTED** — fill Mar-17 10:30 → +$30 target traded 12:30; SL only Mar-18 10:30; MFE $39.58 |
| 18-03 SHORT 4870 / SL 4925 | WIN +500p | **AMBIGUOUS_SEQUENCE + AMBIGUOUS_ENTRY** — day opened at/through 4870; fill and SL share the 00:00 bar; −$50 target traded 20:15; MFE after first touch **$367** (claim plausible, unproven) |
| **19-03 LONG 4775 / SL 4767 / "SL hit 4762"** | LOSS (gap row) | **LOSS_CONSISTENT** — see §4 |
| 19-03b SHORT 4619 / SL 4708 | WIN +400p | **AMBIGUOUS_SEQUENCE + AMBIGUOUS_ENTRY** — post-crash open at/through entry; target traded 12:30; MFE $299 (plausible, unproven) |
| 19-03c SHORT 4624 / SL 4708 | WIN +350p | same — **AMBIGUOUS_SEQUENCE**; target traded 12:30; MFE $304 |
| 20-03 LONG 4610–4619 / SL 4585 | WIN +90p, SL-to-entry at TP1 | **SUPPORTED** — fill 13:45 with the +$9 target in the same bar (both favourable → order immaterial); SL region traded only later (14:15+), consistent with the posted TP1-then-scratch management |
| 20-03b LONG 4583 / SL 4560 | LOSS | **LOSS_CONSISTENT** — fill and SL share the 14:15 bar (ordering AMBIGUOUS_SEQUENCE; loss claim consistent) |
| 25-03 LONG 4548–4554 / SL 4530 | WIN TP1 (level unstated) | **CLAIM_LEVEL_UNSTATED** — descriptive only: day opened in-zone (AMBIGUOUS_ENTRY), MFE $48.42, SL region traded 09:45; untestable without a TP price |
| 27-03 SHORT 4433 / SL 4472 | WIN +170p | **AMBIGUOUS_ANCHOR + FEED_EDGE_CASE** — see §5 |

**Scoreboard at 15m: 3 SUPPORTED · 2 LOSS_CONSISTENT · 4 AMBIGUOUS (sequence/anchor) · 1 UNSTATED ·
0 REFUTED/CONTRADICTED.** Both claimed LOSSES check out; nothing contradicts the recap — the
0-contradicted history stands.

## 4. The Mar-19 SL-gap row vs the 60m result
15m **narrows but does not resolve** the ambiguity: the fill (4775), the posted SL (4767) and the
claimed exit (4762) all first trade inside the **06:45 15m bar** (60m had said "the 06:00 hour").
Fill→stop ordering therefore stays **AMBIGUOUS_SEQUENCE** — but the material facts firmed up:
- reachability re-confirmed at finer grain: one 15m bar traverses 4775→below 4762;
- **MFE after fill was just $13.57 over the whole 48h walk** — price essentially fell straight
  through; there was no meaningful favourable excursion for a 4775 long;
- the LOSS is fully consistent; the ~$5 posted-vs-actual gap remains SUPPORTED as reachable.
Sequence resolution now needs **1m or better** — unavailable at this depth (TradingView 1m starts
~Jun-21). Verdict class unchanged: **LOSS_CONSISTENT_AT_15M / gap SUPPORTED / ordering AMBIGUOUS.**

## 5. The 27-03 row — the audit's most interesting new finding
From the FIRST zone touch (02:00), the SL traded (06:00) before the +170p target (10:30) — naïvely
inconsistent. Two honest qualifiers flip this to AMBIGUOUS, not contradicted:
1. **Feed edge case:** the 06:00 bar high was **4472.97 vs posted SL 4472 — a $0.97 graze**, inside
   the documented $0.5–2 Vantage-vs-Pepperstone divergence. On HIS feed the stop may never have
   traded (exactly the S2-graze precedent from the June sprint).
2. **Anchor dependence:** with a date-only anchor, any entry after ~06:00 (price held 4450–4470,
   then fell to 4416 by 10:30) reaches +170p with no further SL touch.
→ **AMBIGUOUS_ANCHOR_AND_FEED_EDGE_CASE_AT_15M; HUMAN_REVIEW; needs entry-time evidence (and 1m) —
not counted against the recap.** This row is now the best documented feed-divergence candidate after
S2 and feeds the `vantage_vs_pepperstone_feed_difference` watchlist item.

## 6. What 15m did and didn't buy (honest precision note)
15m upgraded 60m's coarse checks: +2 rows fully SUPPORTED (20-03 win; 12-03 already supported),
+2 LOSS_CONSISTENT verdicts, the gap-row window narrowed 4×, and the 27-03 feed-edge case surfaced.
It could NOT resolve: crash-bar sequences (18-03, 19-03 fill/stop, 19-03b/c) — those need 1m, which
does not exist at this depth from this source. Remaining ambiguity is now dominated by **date-only
anchors** (no posted entry times in the recap PDF), which no OHLC granularity can fix — only entry-
time evidence (e.g. Telegram history for that era, if it exists) would.

## 7. Follow-ups
1. **February rows (A/B windows):** the 15m file starts Mar-09 — Feb needs its own export:
   XAUUSD (Pepperstone) **15m**, 2026-02-16 00:00 → 2026-03-06 00:00 UTC →
   `XAUUSD_15M_2026-02-16_to_2026-03-06.csv` (same recipe; 15m depth clearly reaches further back).
2. **May six-trade match** stays shovel-ready (local ticks → 1m; exact entry TIMES known — no anchor
   ambiguity there, so verdicts will be far sharper than these).
3. Optional: hunt entry-time evidence for the Feb–Mar recap era in old Telegram history
   (copied-session historical fetch is proven) — would collapse the anchor ambiguity.

## 8. Safety confirmation
Raw CSV import + deterministic bar-walk arithmetic only; no live scoring; v0.2/v0.3/v0.4 untouched;
matcher outputs hard-wired candidate-only/non-executable; no execution built (broker/QST/cTrader/
nano/copy/demo/live absent); no permits/leases/orders; gates unchanged; no TradingView/Worker/R2/
secret action (export made by Martyn's hand). `NOT_INTEGRATION_READY` unchanged.

## Next step
**Cycle 006 / XAU-F001 at tonight's ~22:00Z reopen stays priority.** Offline queue: Feb 15m export
(§7.1) → run the same matcher on A/B rows; May six-trade local match; optional recap-era entry-time
evidence hunt.
