# Detector v0.4 — Offline Replay Report (IN-SAMPLE ONLY, NO LIVE PROMOTION)

**Mode: OFFLINE REPLAY ONLY — SINGLE-SESSION.** Observation-only. Date 2026-07-12 (~12:05Z).
**v0.3 remains the active forward scorer, completely unchanged** (its replay files untouched; Cycle 006
behaviour unmodified except the note that v0.4 stays offline). Listener **PID 23012 running/untouched**;
live-priority gate checked first: store unchanged at msg 45648, **no XAU trigger → replay proceeded**.
Gates `PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY` unchanged. Data:
`detector_v0_4_offline_replay_results.json` + `detector_v0_4_feature_effects.json`; generator:
`tools/detector_v0_4_offline_replay.py`.

## 1. What was tested (v0.4 = v0.3 base + candidates, variants side-by-side)

Replay-testable candidates: **mitigated_level_exclusion** in three operationalisations —
**V4-LIT** (literal: ≥1 prior touch episode → hard cap of promoted labels at WATCH), **V4-SP**
(spent-aligned: ≥3 episodes, F2's existing "spent" threshold, → cap), **V4-SPX** (V4-SP with
candle-close-confirmed exemption, mirroring v0.3's ratified offset behaviour) — and **V4-TF**
(TF-hierarchy grading of bos_candle_close_confirmed: multi-TF stack +1, single-TF close +0).
All use the **same 24h touch-episode PROXY as v0.3's F2** (formation times not retrospectively
recoverable). **mitigated_level_exclusion stays RATIFICATION-GATED: tested in replay, cannot reach live
scoring without a human ratification record.**

Assessed but not scored (see `detector_v0_4_feature_effects.json`): **displacement_fvg_artifact_test —
UNTESTABLE in-sample** (needs FVG presence in the zone-FORMING leg; formation times unrecoverable —
no proxy was fabricated); **limit-at-zone / posted-vs-actual SL gap / indicator semantics /
claim-convention notes — confirmed capture-only** (no variance, ~3 evidence cases, 0 indicator-sourced
records, and claim-derived respectively).

## 2. Label × outcome, all variants (34 setups; v0.3 = baseline, unchanged)

| variant | MEDIUM | LOW | WATCH | REJECT | HR | promoted losses | promoted winners |
|---|---|---|---|---|---|---|---|
| **v0.3 (live)** | 14 = 11W/0L/3P | 8 = 5W/2L/1P | 6 = 4W/2L | 3 = 0W/1L/2P | 3 | **2** (J23, S2 at LOW) | **16** |
| V4-LIT | 1 = 0W/0L/1P | 0 | 27 = 20W/4L/3P | 3 | 3 | 0 | **0** |
| V4-SP | 7 = 5W/0L/2P | 0 | 21 = 15W/4L/2P | 3 | 3 | 0 | 5 |
| V4-SPX | 9 = 6W/0L/3P | 0 | 19 = 14W/4L/1P | 3 | 3 | 0 | 6 |
| V4-TF | 14 = 11W/0L/3P | 8 = 5W/2L/1P | 6 = 4W/2L | 3 | 3 | 2 | 16 |

Label moves vs v0.3: V4-LIT **21**, V4-SP **15**, V4-SPX **13**, V4-TF **0**.

## 3. Findings, stated plainly

- **V4-LIT is rejected.** The literal reading of "already mitigated = do not re-enter" under the 24h
  proxy destroys the detector: promoted winners 16 → **0**; only J28 (0 touches) survives in MEDIUM.
  The proxy marks nearly every zone touched≥1 — the doctrine cannot be operationalised this way.
- **V4-SP / V4-SPX are mixed and NOT recommended for promotion.** They do demote both residual
  promoted-tier losses (J23, S2 → WATCH; promoted losses 2 → 0) — but at the cost of **10–11 demoted
  winners and a completely empty LOW tier**, and they carry two structural objections: (a) they convert
  F2 from a confidence input into a **gate**, contradicting ratification #2 (graded stack, no
  all-boxes veto); (b) the ≥3 threshold was chosen on this same sample and J23 sits exactly on the
  boundary — this is selection on the target, not evidence.
- **V4-TF is exactly neutral in-sample** (0 label changes: S3 drops its +1 but stays MEDIUM; S4's
  multi-TF stack keeps it). Harmless, unevaluable at 2/34 evidence density — it needs forward records.
- **Displacement enrichment could not be scored** and no fake proxy was invented; its loss-backed
  doctrine support is unchanged and it keeps its designed test (forward formation-timestamp + 8D leg
  capture → deterministic FVG-presence check on the forming leg, frozen windows).
- **Losses demoted / winners over-filtered:** v0.3's residual promoted losses ARE removable (V4-SP/SPX
  prove it in-sample) but only by over-filtering winners; nothing tested improves on v0.3's
  stratification at acceptable winner retention.

## 4. Overfit risk (do-not-overclaim block)

**HIGH and structural.** n=34, few loss rows; the F2 proxy's thresholds were themselves chosen
in-sample; the 0-promoted-loss results of V4-SP/SPX are threshold-selection artefacts until reproduced
out-of-sample; four variants were evaluated against one sample (forking paths). **Nothing in this replay
justifies touching v0.3.** The only decisive data is forward: ≥15 XAU-F records with TRUE formation-time
touch counts.

## 5. Verdicts

- **v0.4: remains an OFFLINE candidate — review-only, further testing recommended on forward data
  only.** Not promoted. No live behaviour changed.
- **Rejected outright:** V4-LIT (literal mitigated-exclusion under the proxy).
- **Ratification-gated (unchanged, reaffirmed):** mitigated_level_exclusion in ANY scoring form — it is
  additionally a gate-type feature, so promotion needs BOTH forward evidence and an explicit
  ratification record. **claim_convention_notes flagged as too claim-derived to ever score without the
  002B policy ratification.**
- **Capture-only confirmed:** limit-at-zone, SL-gap, indicator semantics, claim conventions.
- Promotion conditions codified in **`DETECTOR_V0_4_PROMOTION_GATE.md`**.

## 6. Safety confirmation

Offline only; v0.2/v0.3 artefacts untouched (new files only); no execution built
(broker/QST/cTrader/nano/copy/demo/live absent); no permits/leases/orders; gates unchanged; listener
PID 23012 running/untouched; no TradingView/Worker/R2/secret action; no lot/risk/account/route/ticket/
order fields; labels confined to the allowed five. `NOT_INTEGRATION_READY` unchanged.

## Next step

**Cycle 006 at the next market activity (gold reopens tonight ~22:00Z)** — v0.3 live with v0.2 parallel,
v0.4 nowhere in the loop. v0.4's next event: re-replay on forward XAU-F records once ≥15 exist with true
formation times. Offline queue: optional Feb–Mar 2026 + May OHLC matching.
