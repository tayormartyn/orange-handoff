# OCR QA REPORT — Education Corpus (FP-EDU-008…027)

Controlled transcription-QA. **Visually verified** (100% of the explicitly high-impact set): FP-EDU-008
(Mitigation), 015 (Inducement), 016 (BOS), 021 (Checklist), 024 (Confluence Ranking), 026 (Volume Profile),
018 (Quiz answer) + 019 boundary, and the BTC example (115434/115445). Plus definition/number-bearing content.
Deterministic sample: RapidOCR was cross-checked against the visual reads on the above (10+ posts) and matched
verbatim on text-only posts; the corrections below are the cases where OCR was **truncated or missed numbers**.
Unclear text preserved as `[unclear]`; no wording invented.

## Material corrections (see TRANSCRIPTION_CORRECTIONS.jsonl)
1. **FP-EDU-024 Confluence Ranking** — OCR truncated after item 1. **Full ordered list recovered:**
   **1. Break of Structure · 2. FVG Inversion · 3. Level Reclaim · 4. SFP ("Burj Khalifa" pattern).** (HIGH)
2. **FP-EDU-016 BOS** — recovered the operational tips incl. **"Wait for a Candle Close — confirmed by a solid
   candle close beyond the key level; wicks alone can be fakeouts"**, displacement/volume/retest tips, and the
   timestamp **27/06/2025 22:44**. (HIGH)
3. **FP-EDU-026 Volume Profile** — recovered the **numeric definition: Value Area = 68% of total volume (first
   standard deviation)**; VAH→short-on-rejection, VAL→long-on-rejection, POC = most-traded magnet. Timestamp
   **20/02/2025 23:49**. (HIGH)
4. **FP-EDU-021 Checklist** — recovered the **Structure Break Requirements** with explicit modals: price
   **MUST** break the most recent high; break **SHOULD** show strength (FVG); candle close **PREFERRED but NOT
   MANDATORY**; + an "Invalid Break of Structure" example. (HIGH)
5. **FP-EDU-018 Quiz** — **confirmed answer = DOWN** (stalling + shooting-star deviation + no acceptance above
   50% of cluster + lost 50% of parallel channel → down); image also contains the START of FP-EDU-019. (HIGH)
6. **115434** — identified as a **near-duplicate crop** of the BTC worked example (115445), not the ranking. (MED)

## Cross-source CONTRADICTION found
**Candle-close requirement for BOS is internally inconsistent:** FP-EDU-016 says a **candle close is required**
("wicks alone can be fakeouts"); FP-EDU-021 says a candle close is **"preferred but not mandatory."** Recorded
in CONTRADICTIONS + the blocker matrix (intrabar vs candle-close).

## Terminology recovered/verified
- **FVG Inversion, Level Reclaim, SFP="Burj Khalifa" pattern** (024) — new/clarified.
- **Deviation** (018) = a false push beyond a level (e.g. shooting-star) that fails to gain acceptance.
- **Value Area = 68% / 1 std-dev** (026); **acceptance above 50% of a cluster / 50% of parallel channel** (018).
- **displacement** = strong, fast move breaking key levels with momentum, on a candle close (016/010).
- Still **UNDEFINED in-corpus:** nBOS (used in C004), OTE, RTO, EQH/EQL (appear as labels only).

## Confidence
Author identity HIGH across headered posts (SeaScalper-Farouk / WR). Per-post timestamps HIGH where in-frame,
else MEDIUM. Numeric/checklist/definition content = visually verified HIGH.
