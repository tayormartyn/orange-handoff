# Formal training documents — controlled ingestion report (FP-EDU-002/003/004 + Candlestick)

**Mode: CONTROLLED DOCUMENT INGESTION — REVIEW-ONLY. SINGLE-SESSION.** Date 2026-07-13 (~03:35Z).
Live gates clean throughout (store max 45657; listener PID 30268; no XAU post — Cycle 006 still open).
Machine-readable rules: `knowledge/orange_knowledge_register_v1_1_docs_addendum.json`.
Gates `PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY` unchanged; v0.3/v0.2/v0.4 untouched.

## 1. Verified files, dedup, and provenance (Get-ChildItem + SHA-256; originals untouched)

| Downloads file | bytes | sha256 (=repo copy?) | canonical asset | pages | extraction |
|---|---|---|---|---|---|
| `Farouks_Playbook (3).pdf` (mod 07-04 14:44) | 52,489 | 4CB77D9D… **= identical** | `raw/documents/FP-EDU-002_Farouks_Playbook.pdf` | 22 | **full text** → `education_batches/_pdf_text/FP-EDU-002_pagetext.txt` |
| `Whaleroom_Trading_Guide (5).pdf` (14:46) | 4,687,396 | 8B0A9560… **= identical** | `raw/documents/FP-EDU-003_…pdf` | 12 | **image-only PDF** (0 text pages) → all 12 pages read VISUALLY this session (PyMuPDF renders, local) |
| `Whaleroom_OrderBlocks_Strong_vs_Weak.pdf` (14:47) | 677,938 | C005BFFE… **= identical** | `raw/documents/FP-EDU-004_…pdf` | 2 | **image-only** → both pages read visually |
| `Whaleroom_Candlestick_Patterns.pdf` (15:34) | 16,058 | 37ADAE7E… **= identical** | `education_batches/pdf_batch_02/…pdf` | 7 | **full text** → `_pdf_text/FP-EDU-CANDLE_pagetext.txt` |

All four Downloads copies are **byte-identical duplicates of already-registered assets** (register:
`EDUCATION_MASTER_SOURCE_REGISTER_v0.1`) → **no duplicate records created**; ingestion completed the
missing PAGE-LEVEL extraction layer only. Rights: member-distributed WhaleRoom education; private
research use per the standing rights register. Completeness: EDU-002/CANDLE 100% text; EDU-003/004
100% visually reviewed (no unreadable/corrupt pages; EDU-003 pages are designed graphics — chart
examples are stylized illustrations, not real charts).

## 2. Document rules extracted (stable IDs; full detail in the addendum JSON)

**FP-EDU-002 Farouk's Playbook (text, page-cited):**
- **DR-201** (p3) FVG = 3-candle imbalance (c1.high < c3.low bullish / mirror bearish); trade the
  retrace-fill; SL beyond FVG; target next liquidity. **FVG invalid once filled — never trade it again**
  (p3 rule 3). HTF FVGs > LTF (p3 rule 1). FORMAL_RULE, deterministic.
- **DR-202** (p4) FVG-continuation play: bottoming → impulse leaves 5m FVG → **body close above FVG
  confirms** → retrace-fill = entry → target next bearish OB; sessions London 08:00 / NY 13:30 UTC;
  R:R 1:3 target. FORMAL_RULE + WORKED_EXAMPLE.
- **DR-203** (p5) BPR = overlap of opposing FVGs; entry at overlap; SL beyond swing; **BPR + reversal
  candle = A+++** (p5). FORMAL_RULE.
- **DR-204** (p6) OB = last opposing candle before impulse; liquidity map: equal highs/lows, swing
  H/L, **Asia session H/L, PDH/PDL, round numbers**; sweep = wick-through-and-close-back-inside →
  reversal-candle entry. FORMAL_RULE/DEFINITION.
- **DR-205** (p9) Asia-fakeout trap: wick above Asia high + **no body close above** + lower low =
  trap confirmed; short the retracement; SL above failed high. FORMAL_RULE (the Asia-trap alert's
  documented logic).
- **DR-206** (p10–11) MTF stack 5m structure → 3m MSS/BOS → 1m trigger; **6-question checklist; 6/6 =
  A+++, 5/6 = A, 4/6 = watch, <4 skip** (p11); trigger candle must be CLOSED. FORMAL_RULE with
  numeric thresholds. *(p21 variant: 8-box list, ≥6/8 = A+++, 5/8 = half size-class, <5 skip.)*
- **DR-207** (p12) **THE DOCUMENTED GRADE TABLE**: C = lone pattern (skip) · B = FVG-only or pattern
  at S/R (watch) · A = FVG + pattern at the FVG · A+ = BPR + pattern + trend alignment · A+++ = BPR +
  OB + liquidity sweep + reversal candle + trend / Asia-fakeout + LL + engulfing / bottom + FVG +
  close-above + claim → OB. FORMAL_RULE (document formula). **CRITICAL CAVEAT: whether the
  indicator's "A+ or better"/"A+++ setup" alerts implement exactly this table is UNVERIFIED — the
  Pine remains hidden. Status: DOCUMENT_FORMULA_KNOWN / INDICATOR_EQUIVALENCE_UNKNOWN.**
- **DR-208** (p8, p19) Engulfing: body must fully cover prior body AND be **≥2× prior body**; entry
  next-candle open; SL beyond engulfing wick; **after a liquidity sweep = A+++**. FORMAL_RULE.
- (p13/15–19) checklists repeat SL-beyond-structure, R:R ≥1:2 (1:3 for continuation), candle-must-close,
  and **2%-risk / lot-size items — sizing content EXCLUDED by policy** (recorded as present only).

**FP-EDU-003 Trading Guide (visual, page-cited):**
- **DR-301** (p3) **BE definition with worked example: +50 pips (= $5; BUY 4500 → 4505 → SL to
  4500)**. DEFINITION — the doctrinal +50 BE arm, now page-anchored. *(p5 fixes the conversion:
  **1 pip = $0.10 on XAU** — locks all pip-claim arithmetic.)*
- **DR-302** (p3) Layering (LP): add at −150 pips ($15) drawdown; both BE at the **mid-level**
  (worked example 4492.50). DEFINITION/WORKED_EXAMPLE.
- **DR-303** (p4) Signal anatomy (PAIR/BUY-SELL/ENTRY zone/SL/TP1-2-3) + **"Enter as soon as the
  signal is published when you can"** — the lane-3 canonical follower rule, now page-cited (p4 tip).
- **DR-304** (p8) **Exact tranche schedules: Conservative TP1 50% / TP2 30% / TP3 20%; Advanced
  TP1 30% / TP2 30% / move SL to entry (+50) / leave remainder running.** FORMAL_RULE — the
  documented source of `source_exact_tranche_schedules`.
- **DR-305** (p9) Stop-loss placement algorithm: find key S/R → **place beyond that level** → check
  risk → adjust size → **NEVER move the stop further away / never remove or widen** (best-practices
  row). FORMAL_RULE — the doc-side never-widen provenance.
- **DR-306** (p10) **3-Point Entry: three layered entries, ONE shared stop, BE = +50 pips from the
  AVERAGE, "NEVER add a 4th entry to a loser"** (worked example 4500/4490/4480, avg 4490, SL 4460,
  TP 4500/4510/4525). FORMAL_RULE — documented source of `be_at_average_for_layered` +
  `layering_cap_max3`.
- (p6–7, p11–12) leverage/risk-%/lot-table/compounding (+25%/week target, "projection only"
  disclaimer) — **PERFORMANCE_CLAIM + sizing content, EXCLUDED by policy** (presence recorded).

**FP-EDU-004 OB Strong-vs-Weak (visual, 2pp):**
- **DR-401** (p1) **STRONG OB checklist**: sweep of liquidity first → big displacement leaving it →
  **drops an FVG right after** → fresh/unmitigated ("**the first tap is the strongest**") → aligned
  with bias (**"Above the Trend EMA for longs, below for shorts"**) → bonus: **overlaps a BPR =
  strongest confluence**; annotation "STAYS FRESH". FORMAL_RULE — the documented origin of
  `strong_ob_rubric_v0_1` (all 5 components) and of `displacement_fvg_artifact_test`'s design.
- **DR-402** (p2) **WEAK OB**: small/lazy impulse (no displacement, no FVG) · **"already tapped
  several times — each retest drains it; a mitigated block is spent"** (chart annotation **"TAPPED
  3×"**) · against trend/in chop · sitting alone (zero confluence). FORMAL_RULE — the documented
  origin of the F2 spent-zone thresholds (the 3-tap visual) and `mitigated_level_exclusion`'s doctrine.

**Candlestick guide (text, 7pp):** DR-501 pattern definitions (Doji/Gravestone/Dragonfly/Hammer/
Shooting Star ≥2× wick-to-body; Morning/Evening Star close-past-midpoint-of-candle-1; Tweezers
matching highs/lows) + **DR-502 golden rules (p7): patterns are confirmation not standalone; context
(S/R) > pattern; HTF > LTF; wait for close; pattern in the middle of nowhere = noise.** DEFINITIONS —
these are the objects behind the indicator's TZ/ST/engulfing marks and MR-016's confirmation posture.

## 3. Cross-source comparison (verdicts)
- **SUPPORTS_EXISTING_RULE:** DR-401/402 → MR-001/MR-012/MR-013 + FC-DISPLACEMENT (now doc+video+loss
  triangulated); DR-304/305/306 → MR-007/MR-008 + never-widen ratification; DR-303 → MR-005 (lane-3);
  DR-204 liquidity map → MR-004 magnets + session-level lore; DR-205 → Asia-trap alert logic; DR-206
  1m/3m/5m → the "3 and 1 minutes" low-TF confirmation from the Jul-5 video (MR-003 family); DR-301
  → the +50-60p anticipatory BE (video) — doc says +50 exactly.
- **QUALIFIES_EXISTING_RULE:** DR-207 grade table qualifies the "A-grade formula UNKNOWN" posture →
  now **document-formula-known / indicator-equivalence-unknown**; DR-206's 6/6-vs-8-box variants are
  internally inconsistent granularity (p11 vs p21) — recorded, not merged.
- **CONTRADICTS/TENSION (recorded in the contradiction register, not merged):** (1) **R:R ≥1:2/1:3
  doc rule vs no-2R ratification** (practice shows tranche-1 exits far below 2R) — the standing
  R-RR-2R tension, now page-cited (pp. 13/15–19); (2) **Trend-EMA bias in DR-401 vs his spoken "I
  never use EMAs"** (Dec-2025 video) — doc-vs-practice tension #2; (3) compounding/lot content vs
  Orange policy — excluded, not a methodology contradiction.
- **NEW_CANDIDATE_RULE:** DR-207 grade table as a **testable A-grade hypothesis** (offline: correlate
  documented tiers against captured A+/A+++ alert events — replay-test backlog); DR-202's
  body-close-above-FVG confirmation as a capture flag.
- **DUPLICATE:** all four files vs registered assets (hash-identical) — no re-registration.

## 4. Knowledge retention (where everything went)
Register addendum `knowledge/orange_knowledge_register_v1_1_docs_addendum.json` (rules DR-201…DR-502,
contradiction register, A-grade status change, replay-backlog addition); page texts under
`education_batches/_pdf_text/`; this report. The v1 register file was version-bumped to reference the
addendum. **Nothing entered v0.3**; the A-grade hypothesis goes to the replay-test backlog only;
grade/indicator equivalence stays guarded (F5 + formula-unknown controls).

## 5. Mechanical vs discretionary (per the docs)
**Mechanical (reproducible from the documents):** FVG 3-candle construction + fill-invalidation;
BPR overlap; OB last-opposing-candle; strong-OB checklist (sweep+displacement+FVG+fresh+bias);
weak-OB disqualifiers incl. 3-tap spent; Asia-fakeout trap sequence; MTF checklist with 6/6 or 6/8
grade thresholds; engulfing 2× rule; BE +50 from average; tranche percentages; stop-beyond-structure
+ never-widen. **Discretionary/unknown left:** which qualifying zone to pick when several exist;
exact zone boundary drawing; "strong impulse" magnitude (no numeric displacement threshold anywhere —
FVG-presence design re-confirmed); Trend-EMA parameters (doc names no length); indicator internals +
repaint; his personal deviations from the doc rules (the documented central caveat).

## 6. Integrity test
`tools/test_knowledge_register_integrity.py` extended to validate the addendum (provenance/pages on
every DR rule; A-grade status wording; no live-eligibility). **Result: ALL CHECKS PASSED** (see run
log below the register update). v0.3/v0.2 artifact hashes unchanged; gates re-verified from source.

## Next validation step
Offline (queued behind Cycle-006 live priority): **A-grade hypothesis test** — replay the DR-207
table against the captured Gate-G/H A+/A+++ alert events and future forward captures; plus the
standing queue (Feb 15m export for A/B rows; May six-trade match).
