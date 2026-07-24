# Visual Batch 5 — FINAL retrospective gap-closure (feed comparison + no-trade spec; item 3 unavailable)

**Mode: APPROVED FINAL RETROSPECTIVE PASS — REVIEW-ONLY.** 2026-07-13 (~07:20Z). Live gates: store max
45659 = cursor throughout; listener PID 30268 single-instance. No new frames were required — both
completed items are composed from already-extracted, hash-verified frames (mandate: no duplication,
no filler); reference indices written to `derived/visual_batch5/<ID>/REFERENCES.md`. Originals
untouched. Gates `PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY` unchanged; pre-marks frozen;
ORB/stop-width/POC evidence capture-only; F5 binding.

## VE-FEED-COMPARISON-VISUAL-01 (existing frames, same sessions, near-same times)

| comparison | feeds | evidence | divergence | class |
|---|---|---|---|---|
| **Panel values, gold 1D, ~17 min apart (video-001 00:33:30 vs 00:50:40)** | Eightcap vs Pepperstone | `pmseed_reaudit/t02010s.jpg` vs `t03040s.jpg` | OB retest **4302.29 vs 4299.98 (Δ$2.31)** · Current OB **4512.34 vs 4515.25 (Δ$2.91)** · Fresh OB 1871.61 vs 1871.73 (Δ$0.12) — same structural objects, indicator-computed boundaries shift by feed | SAME_STRUCTURE_BOUNDARY_SHIFT (panel-level) |
| Same instant, tab-bar prices (video-005 @00:25:00) | Vantage chart + 3 other XAUUSD tabs | `visual_batch3/VE-LEVEL-SELECTION-VISUAL-01/t01500s.jpg` tab bar | 4119.06 / 4119.87 / 4120.670 (**Δ up to ~$1.6**) + one 4111.51 outlier (likely different instrument variant → HUMAN_REVIEW, not counted) | SAME_STRUCTURE_SMALL_PRICE_SHIFT |
| Same session ~16 min apart, gold 1h (Dec-21 Zoom 00:06:20 vs 00:21:50) | FXCM vs OANDA | `visual_batch4/VE-LEVEL-SELECTION-VISUAL-02/t00380s.jpg` vs `visual_batch1/VE-Z2-VISUAL-02/t01310s.jpg` | same structure (channel, 4245–4248 zone); manual drawings identical across tabs; quotes 4337.75 vs 4337.22 (Δ$0.53) | SAME_STRUCTURE_SMALL_PRICE_SHIFT |

**Reachability implications (VR-21):** the **Δ$2–3 panel-boundary shifts by feed exceed the S2
($0.52) and 27-03 ($0.97) stop-graze margins** — i.e., documented feed divergence alone is large
enough to flip a marginal stop-touch or entry-fill verdict between feeds. This **SUPPORTS
FC-FEEDDIV** and **QUALIFIES** the deterministic-matching caveats (graze cases must stay
feed-annotated). Mitigation/freshness classification did NOT visibly change by feed in these pairs
(same structure states). **No universal feed-tolerance threshold was invented** — n=3 comparisons;
limitation stated. It does NOT permit disregarding stops.

## VE-GOLD-NOTRADE-VISUAL-01 (existing gold frames + transcript stamps)

| example | evidence (ts, source, frame) | reason | class |
|---|---|---|---|
| "You don't want to long the 4135" | video-005 00:23:49, `t01500s.jpg` chart context | level already mitigated (15m) | **MECHANICAL_VETO** |
| 4020 level discarded | video-005 00:25:46–58 | "already tested, broke it, lost it" — spent | **MECHANICAL_VETO** |
| "Inside of this orb I will do nothing" | Z2 01:10:50 (4250s), `visual_batch2/VE-Z2-VISUAL-03/t04260s.jpg` | price inside ORB — no-trade-inside rule | **MECHANICAL_VETO** |
| "I don't want to be here now inside of this range… at this rejection of the 1h OB" | video-001 00:20:08–18 | mid-range position + level not yet claimed (no body close above the 1h OB, 00:18:13) | MECHANICAL (no-close) + **DISCRETIONARY_VETO** (positioning) |
| "I better wait for a high-probability level even if it looks like a sell or a long" | Jul-5 01:06:47 | insufficient confluence / patience doctrine | **DISCRETIONARY_VETO** |
| "This is too big stop loss of course" | Jul-3 00:31:50, `visual_batch3/…/t01910s.jpg` | stop infeasible | **MECHANICAL_VETO** (feasibility) |

**No-trade candidate specification (offline only, PROHIBITED from v0.3):**
A. **Mechanical vetoes:** level mitigated (15m+) · level spent (tested-broke-lost / ≥3 taps) ·
   price inside ORB · no body close beyond the level · no structure break · stop infeasible ("too
   big") · no re-entry after range (R2b) · no FVG left by the move (weak break).
B. **Discretionary vetoes:** mid-range positioning · insufficient confluence · "wait for the market
   to show its hand" patience · session-opportunity-passed judgement · HTF-bias conflict weighing.
C. **Missing parameters:** the mitigated-on-which-TF precedence rule (15m-mitigated vetoed a long
   while 5m still had a fresh OB — TF hierarchy of the veto is implicit); exact tap-count threshold
   per TF; chase-distance limit.
D. **Forward-test evidence needed:** per-setup capture of considered-but-rejected zones with stated
   reason (extends the Cycle-006 contract's evidence fields; capture-only). Hindsight was NOT used to
   relabel any decision; later outcomes ignored.

## Item 3 — NO ITEM 3 — HISTORICAL ALERT-TO-CHART STATE NOT AVAILABLE
Exhaustive prior audits already established: alert payloads are plain condition names (no chart
state); the only contemporaneous artifact — the phone frame near the Jul-6 18:33Z A+ LONG — shows
price only ("the panel does not render a grade"), with no readable FVG/BPR/OB/sweep state at bar
resolution; the alert-conditions screenshots show the dialog, not a chart bar. No reconstruction was
forced from unrelated screenshots. The alert-to-chart pairing is exactly what the forward capture
contract collects (each future A-grade event with chart state = one clean row).

## RESIDUAL-GAP MATRIX (what retrospective batches can and cannot solve)

| unknown | class |
|---|---|
| A-grade indicator formula | REQUIRES_FAROUK_DISCLOSURE (or long forward correlation; not solvable retrospectively) |
| Panel repaint behaviour | REQUIRES_NEW_FORWARD_CAPTURE (live alert-lane across bar closes) |
| Exact zone-selection discretion (acceptance stage) | PROBABLY_NOT_IDENTIFIABLE (judgement; only boundable by forward accept/reject logs) |
| Exact stop-width mapping (context → $) | REQUIRES_NEW_FORWARD_CAPTURE + REQUIRES_1M_OHLC (outcome-verified widths) |
| Feed-tolerance policy | REQUIRES_NEW_FORWARD_CAPTURE (dual-feed observations; n=3 visual pairs insufficient) |
| ORB retest depth | REQUIRES_NEW_FORWARD_CAPTURE + REQUIRES_1M_OHLC |
| ORB validity horizon | REQUIRES_NEW_FORWARD_CAPTURE (possibly REQUIRES_FAROUK_DISCLOSURE) |
| Internal-structure-break panel change | REQUIRES_UPDATED_PANEL_RELEASE (announced, pending) |
| Farouk's personal fills/stops | REQUIRES_FAROUK_DISCLOSURE (widgets appear sporadically; else unknowable) |
| Alert-to-chart feature state | REQUIRES_NEW_FORWARD_CAPTURE (contract already wired) |
| Feb–Mar recap A/B rows | SOLVABLE_FROM_EXISTING_ARCHIVE + one 15m export (Feb window) |
| May six-trade deterministic match | SOLVABLE_FROM_EXISTING_ARCHIVE (local ticks; shovel-ready) |
| Recap entry times (anchor ambiguity) | REQUIRES_ENTRY_TIME_EVIDENCE (old Telegram history fetch) |

**Questions no further retrospective visual batch can resolve:** the A-grade formula, repaint,
personal fills/stops, acceptance-stage discretion, ORB missing parameters, feed tolerance — all
gated on forward capture, a panel release, or disclosure. **The retrospective visual program has
reached diminishing returns; the archive's remaining solvable items are the two OHLC tasks + the
entry-time hunt, none of which are visual.**

## Knowledge updates
Register addendum: VR-21 (feed-divergence table + reachability implication), no-trade spec (A–D,
FC-NOTRADE capture-first), item-3 disposition, residual-gap matrix pointer. Nothing enters v0.3.
