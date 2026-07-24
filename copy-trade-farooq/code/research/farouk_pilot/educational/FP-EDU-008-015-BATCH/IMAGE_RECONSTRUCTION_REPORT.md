# FP-EDU-008–015 — IMAGE RECONSTRUCTION REPORT

Inventory + reconstruction of the manually-captured Discord Education screenshots in
`research/farouk_pilot/evidence_images/`. Filenames are generic Snipping-Tool names and were **not** used as
source identity — grouping is by visible titles/headings, in-diagram labels, and continuity. Originals were
not renamed/moved/modified. Full per-image data in `IMAGE_SOURCE_MAP.csv`.

## Method note — no author/timestamp available
**None** of the 10 screenshots shows the Discord **author** line or the **post timestamp**; every crop is
the message *body* only. So evidence priorities #2 (Farouk author + timestamp) and #3 (overlapping text
between screenshots) were **largely unavailable**; grouping rested on #1 (visible title), #4 (matching
diagrams/headings) and #5 (subject). Filesystem timestamps (all 2026-07-05, the capture session) are **not**
the original Discord posting times and were not used.

## All images found (10)
| # | file (11:xx) | WxH | sha16 | maps to |
|---|---|---|---|---|
| 1 | 112743 | 1242×390 | 731fa5ef | AMBIGUOUS (BFI/fractal fragment) |
| 2 | 113341 | 960×461 | e21eed5c | FP-EDU-009 |
| 3 | 113418 | 1282×480 | 7b5fff39 | FP-EDU-010 |
| 4 | 113500 | 957×395 | a90672af | UNASSIGNED (Structure-Break/BOS) |
| 5 | 113530 | 887×456 | a8d080f3 | FP-EDU-011 |
| 6 | 113614 | 1290×477 | 00d9f81c | FP-EDU-012 |
| 7 | 113701 | 1056×462 | 92362598 | FP-EDU-013 |
| 8 | 113743 | 762×432 | d649e406 | FP-EDU-014 |
| 9 | 113817 | 776×377 | 7f3a7e49 | FP-EDU-015 |
| 10 | 115445 | 822×402 | 7b05fbdf | AMBIGUOUS (BTC example) |

## Images assigned to each FP-EDU source
- **FP-EDU-008 — Mitigation in Trading:** **NO image found (MISSING).** No screenshot has a "Mitigation"
  title or definition. ("mitigation"/"filling the gap" appears only as incidental diagram labels in imgs 5/8.)
- **FP-EDU-009 — Strong/Weak High & Low:** img 2 — STRONGLY_SUPPORTED. Full 4 definitions (Strong High/Low =
  manipulated + BOS + RTO; Weak High/Low = liquidity target / will be broken) + annotated chart. Fairly complete.
- **FP-EDU-010 — Major vs Internal Structure:** img 3 — CONFIRMED (explicit "Major Structure" / "Internal
  Structure" diagram labels). This is the **END** of the post (concluding line + summary diagram + reactions).
- **FP-EDU-011 — Single Candle Order Block / SCOB:** img 5 — STRONGLY_SUPPORTED (in-diagram title "Single
  Candle Order Block (valid)", POI/inducement/candle-close labels + candle-body anatomy).
- **FP-EDU-012 — Types of Price Inefficiencies:** img 6 — CONFIRMED (caption "Types of price inefficiencies";
  Volume imbalance / Fair value gap / Opening gap). **END** of post.
- **FP-EDU-013 — Trend Continuation Entry Model:** img 7 — STRONGLY_SUPPORTED ("Trend continuation setups",
  numbered steps 4–5 + dual LTF-BOS+FVG diagram). **END** of post.
- **FP-EDU-014 — High-Probability POI Entry Model:** img 8 — STRONGLY_SUPPORTED by content + elimination
  (checkmark checklist: confirmation on smaller TF / liquidity / patience + FVG+OB POI diagram). *Residual
  ambiguity: could be a 2nd page of FP-EDU-013.*
- **FP-EDU-015 — Inducement Model:** img 9 — STRONGLY_SUPPORTED ("Inducement happens a lot before major
  reversals or breakouts"; 3-Drive + fib 0.618–0.79 + "Enter short" diagram). **TOP/intro** of post.

## Duplicate or near-duplicate images
**None.** All 10 SHA256 hashes are distinct; no two images are the same post fragment. (Imgs 1, 2, 3 depict
similar underlying price action but are distinct diagrams/messages.)

## Unassigned images
- **img 4 (Structure-Break / BOS):** in-diagram title "STRUCTURE BREAK"; closing line "…understanding BOS and
  waiting for confirmation…". **Not one of the 8 expected titles.** Could be a foundational "Break of
  Structure" post or part of FP-EDU-010, but has no Major/Internal label → left UNASSIGNED (not guessed).

## Ambiguous mappings
- **img 1 (BFI/fractal):** "fractal nature of price — small waves within larger waves — as BFI balances
  positions". Theme fits Major/Internal Structure (010) but no matching title/diagram → **AMBIGUOUS**, not
  assigned to 010 to avoid subject-similarity error.
- **img 10 (BTCUSDT BITGET 1h example):** live BTC chart (Asia/London/EQH/Sweep/Deviation) + "Always wait for
  confirmations" tip. Weak thematic link to Inducement (015) but a different artefact type (live chart, ~17
  min later capture) → **AMBIGUOUS** (possibly end of 015 or a standalone liquidity/session example).
- **img 8 → 014:** assigned STRONGLY_SUPPORTED but flagged (could be a 013 continuation).
- **img 5 top confluence list:** the "Volume Analysis / Previous Session Levels / more confluences align"
  header sits above the SCOB diagram; that confluence list may belong to an entry-model post (013/014)
  rather than SCOB — recorded, not resolved.

## Missing sections
- **FP-EDU-008 (Mitigation): entirely missing** (0 images).
- **Missing beginnings:** FP-EDU-010, 012, 013 are END-fragments (definition/intro text not captured).
- **Missing ending:** FP-EDU-015 has only the intro (img 9); its conclusion is not captured (unless img 10
  is it — ambiguous).
- **Partial:** FP-EDU-011 (img 5) is a mid montage; FP-EDU-014 (img 8) is a closing checklist only.

## Is the batch sufficiently complete to proceed?
**PARTIALLY — NOT sufficient for the full 008–015 ingestion as specified.**
- **6 posts** are reasonably supported for evidence work: **009 (good), 010, 011, 012, 013, 015** (015 intro
  only), plus **014** (supported-with-ambiguity).
- **1 expected post — 008 Mitigation — is entirely absent.**
- **3 images** (1 BFI/fractal, 4 BOS, 10 BTC) do not map to an expected title.
- Most posts are single END-fragments (beginnings missing).

Per the instruction to **stop and report if specific screenshots remain missing or genuinely ambiguous**, the
reconstruction pass is complete but the full ingestion should **not** proceed for 008–015 as a set until the
Mitigation screenshot(s) are supplied and the ambiguous images (1/4/10) are clarified. The 6 well-supported
posts could be ingested individually if desired.

---

## CORRECTION (post-clarification from Martyn)
Mapping updated per operator clarification; `IMAGE_SOURCE_MAP.csv` reflects the final state:
- **112743 → FP-EDU-008 (Mitigation)** — `STRONGLY_SUPPORTED / PARTIAL_FRAGMENT` (fractal/BFI/rebalancing =
  mitigation content). **Not CONFIRMED** — title/author/timestamp absent; beginning/title provenance still missing.
  FP-EDU-008 is now a **partial but usable** source (no longer "entirely missing").
- **113500 → FP-EDU-010-SUPPLEMENTAL-CANDIDATE** — `AMBIGUOUS`. BOS/displacement/candle-close are consistent
  with 010, but **direct continuity (overlapping text / shared title) could NOT be established**, so it is
  preserved as a supplemental candidate, not merged into 010.
- **115445 → UNASSIGNED / STANDALONE** — BTC worked example; not forced into 015 (no title/text/timestamp
  continuity); provenance pending.
- **113743 → FP-EDU-014** — `STRONGLY_SUPPORTED` (distinctive break→POI→liquidity→return→sweep→LTF-confirm→
  opposing-liquidity chain distinguishes it from 013).

**Batch decision:** proceeding with the full batch as a **partial but usable** evidence set (per instruction),
recording all missing beginnings/endings, cropped wording and unresolved provenance rather than inventing text.
Deliverables added: `FP-EDU-008-015_TRANSCRIPTIONS.md`, `_CLAIMS.json`, `_SETUP_FAMILY_MATRIX.json`,
`_CAMPAIGN_CROSS_REFERENCE.json`, `_FINDINGS.md`, `_STATE_MACHINE_DELTA.md`, and
`comparisons/FP-EDU-008-015-vs-STATE-MACHINE-v0.1.json`.
