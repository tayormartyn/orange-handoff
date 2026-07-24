# Training Batch 003B — Capture-Only Integration (five Batch-003 merges) + master re-issue

**Mode: BATCH 003B — CAPTURE-ONLY MERGE + MASTER SOURCE UPDATE, NO LIVE SCORER CHANGE. SINGLE-SESSION.**
Observation-only. Date 2026-07-12 (~11:40Z). Extends (never edits) the Cycle-002 schema addendum,
Batch-001B/002B integrations, and all prior artefacts. **Detector v0.3 live labels are UNCHANGED for
Cycle 004** — everything here is recorded alongside, never scored. Machine-readable:
`training_batch_003b_capture_only_integration.json`. Gates `PAPER/PREVIEW/False/False`;
`NOT_INTEGRATION_READY` unchanged.

## 0. Live-priority gate (checked first)
Listener **PID 23012 running/untouched** (only python process; started 2026-07-12 11:18:08Z at the
controlled reboot). Read-only store query: max msg id **45648**; the only post-cursor messages remain
**45647 = NON_XAU** (HYPE/Hormuz chatter) and **45648 = IRRELEVANT** (admin newsfeed-channel notice).
**No new XAU/Gold activity → Cycle 004 NOT triggered; Batch 003B proceeded.**

## 1. The five capture-only merges (MERGE_NOW_CAPTURE_ONLY → merged this step)

| # | merge-queue item | what was merged | target |
|---|---|---|---|
| 1 | `stop_width_dataset_extension_feb_mar_2026` | +19 posted-width samples (Feb–Mar 2026, median ~$21, range $8–89; wide tail $55/84/89 on counter-trend "low lot" shorts, claim-context only) — cross-period match with the existing ~$20 median | `stop_width_by_level_type` v0.1 research dataset; `stop_width_dataset_reference` (002B field) now cites: 32 sprint widths + 6 May samples + spoken $30–40 anchor + **19 Feb–Mar recap samples** |
| 2 | `posted_vs_actual_sl_gap_note` | first documented posted-vs-actual stop gap (19-Mar: posted SL 4767, "SL hit at 4762" → ~$5) — direct evidence for the central caveat | Cycle-004 capture spec (8F feed notes) — new fields §3; R6 central-caveat note |
| 3 | `indicator_level_semantics_pack` | panel-level semantics from the Dec-2025 series: session range boxes (top/mid/bottom), VWAP (session/D/W/M), POC/VAH/VAL (D/W), SFP dots, liquidity-sweep marks, ORB top/mid/bottom (mid = hidden liquidity; no-trade-inside-orb; breakout→retest), yellow market-maker candles | Lane-6 builder inputs + `FP_INDICATOR_001_ALERT_MAPPING` documentation; capture enum §3 |
| 4 | `limit_at_zone_doctrine_note` | "limit orders are a cheat code — always be prepared with your entry zone" + day-ahead pre-marking = HIS OWN workflow; limit-at-zone = canonical follower mechanic | R6 lanes 2/3 notes + Lane-6 spec doctrine note; capture fields §3 |
| 5 | `claim_convention_recap_evidence` | claim accounting documented: "85%+" = W/(W+L) with MISSED+REMOVED excluded; +3,000p no-entry "win"; hypothetical missed-trade framing; one impossible-SL data error (27-03, excluded); "paper trade but I took it on my real account" lane-separation quote | R6 lane-5 claim discount + `audit_convention_notes` (002B field) conventions; capture fields §3 |

All five are **documentation/dataset/capture-field merges only** — no weight, threshold, label, or
scoring change anywhere.

## 2. v0.4 backlog (kept offline — NOT merged into live use)

- `displacement_fvg_artifact_test` **enrichment**: now loss-backed (Jul-1 post-mortem: no-FVG one-leg
  move = sweep/"weak break"; sideways-clear-cluster-dump = genuine); FVG-presence design confirmed, no
  pip threshold. **Offline replay required before any use.**
- `mitigated_level_exclusion` (NEW candidate hard filter: "don't enter another long at this OB — already
  mitigated"): **RATIFICATION-GATED — requires offline replay AND a human ratification record before any
  scoring use.** Queued in the ratification queue; not blocking now.
- `confirmation_tf_hierarchy` grading (5m<15m<1H<W close stack): +confidence-only input per the standing
  BOS candle-close ratification. Offline.

Watchlist unchanged: `asia_high_break_session_prior` (78–80% claim — needs offline verification +
ratification before any consideration). Holds unchanged: conviction-size notes (claim-context only, no
sizing fields ever); Feb–Mar 2026 OHLC matching option (recommended later, NOT run).

## 3. New capture-only fields (per XAU-F record, Cycle 004+)

| field | definition |
|---|---|
| `entry_mechanic_evidence` | `LIMIT_AT_ZONE` \| `POST_TIME_MARKET` \| `UNKNOWN` — what the post/evidence shows about how the entry was taken (limit-at-zone doctrine check; lanes 2/3 lens) |
| `pre_planned_evidence` | message ids/timestamps of any day-ahead plan or pre-marked-zone statement ("we made this plan yesterday"); feeds Lane-6 match analysis |
| `posted_sl_price` | the SL price as posted (already captured; restated here as the gap baseline) |
| `actual_stop_evidence` | verbatim later statement/tape of where the stop actually was or was hit (e.g. "SL hit at 4762"); UNKNOWN unless stated |
| `posted_vs_actual_sl_gap_usd` | \|posted − actual\| when both exist; else UNKNOWN — never inferred |
| `indicator_level_source_kind` | `SESSION_RANGE_BOX` \| `VWAP` \| `POC` \| `VAH` \| `VAL` \| `SFP_DOT` \| `LIQUIDITY_SWEEP_MARK` \| `ORB_TOP` \| `ORB_MID` \| `ORB_BOTTOM` \| `YELLOW_CANDLE_CONTEXT` \| `PANEL_PRICE` \| `NON_INDICATOR` \| `UNKNOWN` — semantics per the Batch-003 pack |
| `claim_convention_notes` | which accounting conventions the setup's claims use (flats-excluded; no-entry "win"; hypothetical missed framing; data-error flag) — extends 002B `audit_convention_notes` |
| `claim_has_entry_sl` | bool — whether the claim row carries a checkable entry+SL (recap lesson: some "wins" have neither) |

SL-to-entry / scratch behaviour needs **no new fields** — the required 8C `management_timing` block
(instruction_events, `sl_to_entry_instruction_ts_utc`, `scratch_trigger_ts_utc`, `scratch_mode`,
`tp_banking_timing`) already captures it; Batch-003 adds the doctrine note that "SL to entry at TP1" is
his routine (recap 20-02/24-02/20-03), so `scratch_mode=LITERAL` evidence is expected frequently.
Stop-width context uses the existing 002B fields with the §1.1 extended dataset reference.
All fields are capture-only: **never scored by v0.3, never a gate, no sizing semantics anywhere.**

## 4. Cycle 004 / XAU-F001 readiness (updated)

When the first real XAU post arrives after tonight's ~22:00Z reopen: XAU-F001 under the full
8C+8D+8F+001B+002B spec **plus the §3 fields**; v0.3 labels with v0.2 in parallel (A/B unchanged);
PM-F001/PM-F002 comparison; same-day 1m OHLC request; 48h deterministic match. **Not run in this step.
No v0.4 replay run in this step. No OHLC matching run in this step.**

## 5. Orange master source of truth — re-issued

Wrote **`ORANGE_MASTER_SOURCE_OF_TRUTH_vNEXT.md` + `orange_master_source_of_truth_vnext.json`**
(as-of 2026-07-12): Batch-003 deltas folded in; controlled-reboot status; **listener PID 23012 live
(87988 retired at power-down)**; store max 45648 (45647 NON_XAU, 45648 IRRELEVANT, cursor 45646);
XAU-F001 still pending; PM-F001/PM-F002 active/unchanged. The 2026-07-11 master files are preserved
untouched (extend-not-edit); vNEXT is the current read-first pair.

## 6. Safety confirmation

Documentation/capture-schema only; targets pre-flight-checked (none existed); nothing overwritten.
No execution built (broker/QST/cTrader/nano/copy/demo/live absent); no permits/leases/orders; gates
`PAPER/PREVIEW/False/False` unchanged; listener **PID 23012 running/untouched**; no TradingView/Worker/
R2/secret action; no lot/risk/account/route/ticket/order fields; v0.3 live labels unchanged; v0.4 not
used live. `NOT_INTEGRATION_READY` unchanged.

## Next step

**Cycle 004 / XAU-F001 at the first real XAU post after tonight's ~22:00Z gold reopen** under the full
capture spec including the §3 fields; detector v0.4 offline replay thereafter (displacement enrichment +
mitigated_level_exclusion + TF-hierarchy); optional Feb–Mar 2026 + May OHLC matching later.
