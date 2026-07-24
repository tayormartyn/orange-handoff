# FAROUK_DOCUMENTED_DETECTOR_SPEC_v0_1 (readable)

**RESEARCH-ONLY / OFFLINE / NOT_LIVE / NOT_AUTHORITATIVE.** Authoritative version = the companion
JSON (no PDF). Built strictly from documented DR/VR rules; UNKNOWN preserved where undocumented; no
numeric threshold invented. 7 setup families specified; deterministic code implemented for **2**
(FVG_CONTINUATION_5M, ASIA_SESSION_FAKEOUT) + the shared 5m→3m→1m trigger stack.

## Shared trigger stack (DR-206)
`5m STRUCTURE → 3m MSS/BOS + FVG → 1m CLOSED TRIGGER` — completed candles only, derived from the
existing 1m Pepperstone feed (no new 3m/5m webhook).

## Grade systems (kept SEPARATE — do not merge)
- Confluence ladder **C/B/A/A+/A+++** (DR-207) — DOCUMENT_FORMULA_KNOWN
- Six-factor **6/6=A+++, 5/6=A, 4/6=watch, <4 skip** (DR-206 p11) — DOCUMENT_FORMULA_KNOWN
- Eight-box **≥6/8=A+++, 5/8=half, <5 skip** (DR-206 p21) — DOCUMENT_FORMULA_KNOWN
- Setup-family all-boxes — per family below
- TradingView indicator grade — **INDICATOR_EQUIVALENCE_UNKNOWN**
- Relationship between them — **GRADE_VERSION_RELATIONSHIP_UNKNOWN**

## The 7 families (each: context → objects → liquidity → structure → trigger → entry/stop/target → grade → invalidation → no-trade → provenance → UNKNOWN)
1. **FVG_CONTINUATION_5M** *(implemented)* — bottoming → bullish 5m FVG → body close above → retrace-fill + bullish confirmation → target next bearish OB; London/NY; A if FVG+pattern (DR-202/201/207). UNKNOWN: displacement threshold; bearish mirror stays UNKNOWN unless evidenced.
2. **ASIA_SESSION_FAKEOUT** *(implemented, bearish + bullish mirror)* — Asia H/L frozen → wick beyond extreme with NO body close → reversal → first LL below Asia low (bearish) → short retrace; SL above failed high; target next liquidity (DR-205/207). UNKNOWN: exact Asia window; LL extension.
3. **BPR_REVERSAL** *(spec only)* — overlap of opposing FVGs + reversal = A+++ (DR-203). UNKNOWN: overlap tolerance.
4. **OB_RETEST** *(spec only)* — OB = last opposing candle; sweep = wick-through+close-back; reversal entry (DR-204). UNKNOWN: OB anchor tolerance, displacement.
5. **ENGULFING_SWEEP** *(spec only)* — engulfing (body ≥2× prior) after sweep = A+++ (DR-208). UNKNOWN: sweep-to-engulfing gap.
6. **CANDLESTICK_REVERSAL_AT_LEVEL** *(spec only)* — hammer/star/tweezers AT a level (DR-501/502). UNKNOWN: which level qualifies.
7. **MTF_STACK_A_GRADE** *(spec only)* — 5m→3m→1m checklist 6/6 or ≥6/8 (DR-206). UNKNOWN: exact factor detectors; indicator equivalence.

Full field-by-field contracts are in the JSON. Predicates for families 3–7 are intentionally
incomplete (marked `implemented:false`) rather than guessed.
