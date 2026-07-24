# FP-EDU-008–015 — PROPOSED STATE-MACHINE EDUCATION DELTA (v0.1 → candidate)

**PROPOSAL ONLY. NOT APPLIED. NO CODE. `FAROUK_STATE_MACHINE_SPEC_v0.1` is NOT modified.**
Candidate refinements to the state machine informed by the written SMC curriculum (FP-EDU-008–015). Each item
notes its evidence strength and why it does **not** yet unblock a coded detector. This batch is the SMC
curriculum behind Campaigns 001–004 — it does **not** apply to Vishal's EMA method (FP-EDU-007).

## A. Definitional refinements (narrow existing elements)
1. **`ZONE_MITIGATED` / `RETURN_TO_VALUE` — add a mitigation definition** (FP-EDU-008): a zone is *mitigated*
   when price returns into the inefficiency/OB/S-D zone that BFI use to rebalance. *Evidence:* STRONGLY_
   SUPPORTED/PARTIAL (no title/author). *Still blocked by:* no numeric "how deep / how many touches" threshold.
2. **`STRUCTURE_FOUND` — fractal major/internal** (FP-EDU-010): distinguish **major** swings from **internal**
   sub-structure; **BOS** = a key swing broken (010-SUPPL). *Evidence:* CONFIRMED (010) / AMBIGUOUS (010-SUPPL).
3. **`displacement_strength` — qualitative definition** (FP-EDU-010-SUPPL): displacement = a strong, fast move
   that breaks key levels with high momentum, on a **candle close**. *Evidence:* AMBIGUOUS provenance;
   **no numeric threshold** → remains non-codeable (documents the concept only).
4. **`fvg_created` — inefficiency TYPES** (FP-EDU-012): Volume imbalance / Fair Value Gap / Opening gap.
   *Evidence:* CONFIRMED. Narrows the object; mitigation/fill rule still qualitative.
5. **`ZONE_REGISTERED` — SCOB sub-type** (FP-EDU-011): a single-candle order block validated by a
   **candle close above the inducement zone** → POI. *Evidence:* STRONGLY_SUPPORTED.

## B. New candidate attributes
6. **Level-quality attribute (strong vs weak)** (FP-EDU-009): strong = manipulated + BOS + RTO; weak = a
   liquidity target that will be broken. Aligns with **C004's preferred-zone quality hierarchy**. Candidate
   input to `ob_fresh`/quality grading. *Evidence:* STRONGLY_SUPPORTED.

## C. New candidate setup families (would need their own branches)
7. **`TREND_CONTINUATION_ENTRY`** (FP-EDU-013): LTF BOS → FVG → fill/mitigate → continue. Analog of
   `ORB_CONTINUATION`. *Evidence:* STRONGLY_SUPPORTED (beginning missing).
8. **`POI_SWEEP_ENTRY`** (FP-EDU-014): strong move breaks pattern → POI origin → liquidity both sides →
   return → **sweep into POI** → **LTF confirmation** → target opposing liquidity. Composes
   `LIQUIDITY_EVENT.SWEEP_CONFIRMED` + `STRUCTURAL_SETUP` + `QUALIFICATION`. *Evidence:* STRONGLY_SUPPORTED.
9. **`INDUCEMENT_FADE`** (FP-EDU-015): inducement = liquidity grab/trap before a major reversal/breakout;
   fade after confirmation (3-Drive / OTE fib). Ties to `VETOED` (don't chase the inducement) + a fade entry.
   *Evidence:* STRONGLY_SUPPORTED (intro only; ending missing).

## D. Blocker status after this batch
- **`F_CONFLUENCE_UNKNOWN` — STILL_BLOCKED.** 011 ("more confluences align = stronger"), 014 (checklist) and
  009 (quality) supply *qualitative* confluence factors but **no minimum count/weighting**.
- **displacement — PARTIALLY_NARROWED** (qualitative candle-close+momentum), but **no numeric threshold** and
  **ambiguous provenance** → not codeable.
- **`F_TZ_UNKNOWN`, `F_REPAINT_UNKNOWN` — UNCHANGED** (static diagrams; no timezone or timing evidence).

## E. Invariants preserved
This delta changes **no** safety invariant: no risk/size/broker/order logic; nothing wired to QST; the Alpha
detector still terminates at `QUALIFIED_CANDIDATE`. Adoption would require: the FP-EDU-008 title/provenance
screenshot, the missing beginnings/ending, a **confluence-count** rule, and **numeric displacement / mitigation
thresholds** — none present here.

## F. Recommended next evidence
Title/author/timestamp screenshots for **008** (and ideally all posts); the **beginnings** of 010/012/013/014
and the **ending** of 015; provenance for the **BTC worked example**; and any post that states a **confluence
count** or **numeric displacement/mitigation** rule.
