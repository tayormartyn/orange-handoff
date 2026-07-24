# Visual Batch 4 — current-panel audit + gold management + POC/VP selection

**Mode: APPROVED VISUAL PASSES ×3, ONE AT A TIME — REVIEW-ONLY.** 2026-07-13 (~07:10Z). Live gates
before each item and before findings: store max 45657 throughout; listener PID 30268 single-instance;
cursor 45657. Sources hash-verified (video-005 942dc4af…; Zoom full mp4 5635e60e…). Originals
untouched. Frames: `derived/visual_batch4/<ID>/`. Gates `PAPER/PREVIEW/False/False`;
`NOT_INTEGRATION_READY` unchanged; pre-marks frozen; ORB/stop-width schemas capture-only.

## VE-CURRENT-PANEL-VISUAL-01 (video-005; frames t01230/t04270 + cross-ref t01500 from Batch 3)
- **VR-17 CURRENT_PANEL_STATE (Jul-12):** title "Farouk's Playbook — Smart Money Suite" (indicator
  list, t01500); panel rows on 5m (t04270 @01:11:10): **TF 5 · CHoCH 4105.5 (green) · Asia break LOW ·
  OB retest 4107.50 · Current OB 4093.40 · Fresh OB ✗** — same six-field surface as the Jul-5 audit;
  **NO internal-structure-break row → the announced change (add ISB, remove something; announcement
  @01:09:46–01:11:26 of this same video) is NOT yet implemented → ANNOUNCED_FUTURE_CHANGE, pending;
  FC-PANELWATCH stays active.**
- **VR-18 TF-aware panel recomputation (DIRECT_VISUAL_EVIDENCE):** 1h panel (t01500) shows CHoCH ✗ /
  OB retest 4084.57 / Current OB 4065.86 while the 5m panel (t04270) shows CHoCH 4105.5 / OB retest
  4107.50 / Current OB 4093.40 — per-TF independent states; also red/green value colouring = state
  flags. On-chart current-suite objects labeled: session Asia H/L per day, London H/L (blue), US
  H/L (orange), CHoCH tags, OB/FVG bands.
- Legacy-vs-current: the Dec-21 stack ([kyle] v1/v2 + POC + Smart Zones PRO) has NO such panel —
  differences recorded; legacy objects never equated to current ones. Repaint: static frames cannot
  establish stability → **REPAINT_UNKNOWN maintained (F5 binding)**; no A+/A+++/LONG/SHORT panel
  rows exist on the current surface (grades arrive via alerts only) — grade-formula separation
  (DOCUMENT_FORMULA_KNOWN / INDICATOR_EQUIVALENCE_UNKNOWN) preserved.

## VE-GOLD-MANAGEMENT-VISUAL-01 (video-005 @00:22:25–00:22:50; frames t01345/t01370)
- **VR-19 RETROSPECTIVE_MANAGEMENT + VISUAL_AUDIO_MATCH (gold, 5m Pepperstone, REPLAY controls
  visible):** the Friday-trade recap replayed on chart — drawn black entry line ~4105, the mitigated
  pink zone above, the drop to ~4085 (~190–200 pips) and the spike back through entry visible;
  audio: "we took a sell… stop loss to entry… got stopped out at entry after we had 200 pips or so…
  this huge candle mitigated that zone". **FOLLOWER_TRADE_EVIDENCE ("we"), retrospective; no widget;
  entry/BE lines chart-visible; sequencing within the spike bar = AMBIGUOUS_SEQUENCE** (fine
  ordering unresolved — consistent with the deterministic S-series handling). Personal-stop values:
  not shown (lanes kept separate).

## VE-LEVEL-SELECTION-VISUAL-02 (Z2 @00:06:20–00:07:20; frames t00380/t00440)
- **VR-20 DIRECT_AUDIO_AND_VISUAL (gold 1h FXCM):** volume-profile histograms (dual distributions),
  **red POC line ~4330, VAH ~4347 / VAL ~4310 purple boundaries**, precise level cluster labels
  (4335.03/4326.90/4324.93/4322.08), BOS tag, trendline. Audio: "failed to break [VAH], came back to
  POC… failed to hold the POC, came back to VAL… if they fail to break VAH **we're gonna take a
  short to at least the POC**." → **VP/POC role: constructs reference levels (VAH/POC/VAL), frames
  the range trade, and supplies the TARGET FLOOR ("at least the POC" = mechanical target rule
  candidate); zone candidates themselves remain manually drawn.** PARTLY_MECHANICAL_SELECTION.
  (Multi-window POC labels [1DT/2DT/…] documented in Batch 2 VR-12; not re-processed.)

## Classifications summary
CURRENT_PANEL_STATE (VR-17/18) · ANNOUNCED_FUTURE_CHANGE (ISB pending) · REPAINT_UNKNOWN ·
FOLLOWER_TRADE_EVIDENCE + RETROSPECTIVE_MANAGEMENT + VISUAL_AUDIO_MATCH + AMBIGUOUS_SEQUENCE (VR-19)
· DIRECT_AUDIO_AND_VISUAL + PARTLY_MECHANICAL_SELECTION (VR-20). No cross-asset content used as gold
evidence; no mismatches found this batch.

## Knowledge updates
Register addendum: VR-17…VR-20 + panel-state table + "at-least-the-POC" target-rule candidate
(FC-POCTARGET, capture-first) + management-evidence entry. Indicator audit cross-linked (current
surface re-confirmed Jul-12; change pending). Nothing enters v0.3.
