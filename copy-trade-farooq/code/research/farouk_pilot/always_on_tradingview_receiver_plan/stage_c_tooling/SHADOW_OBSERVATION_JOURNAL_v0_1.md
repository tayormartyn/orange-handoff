# Shadow Observation Journal v0.1

**Append-only, observation-only.** Seeded with the 3 outcome-matched Gate G candidates (2026-07-09,
XAUUSD 1m, PEPPERSTONE_TradingView_export). **Candidate-only; no trade instruction, no execution.**
All price figures are descriptive USD/oz, oriented to the candidate's direction_hint — **not PnL,
not sizing**. `NOT_INTEGRATION_READY` unchanged. Machine copy: `shadow_observation_journal_v0_1.csv`.

**Progress toward evidence review: 3 / 30 outcome-matched candidates** (see
`NO_TRADE_TO_DEMO_EVIDENCE_THRESHOLDS_v0_1.md`).

---

## SOJ-0001 — ALIGNED_CHOCH_TO_A — outcome_label: MIXED

- candidate_id `ALIGNED_CHOCH_TO_A-0000` · hint **LONG** · anchor `2026-07-09T04:12:01Z` · entry **4063.96** · data_quality **FULL**
- classifier `raw_farouk_text_classifier_v0_2` · detector `shadow_candidate_detector_v0_1`
- raw: `Farouks Playbook: CHoCH UP on XAUUSD 3` | `Farouks Playbook: A LONG on XAUUSD 3`
- classified: `CHOCH_UP(LONG_HINT) -> A_LONG(LONG)`

| Horizon | MFE | MAE | final close Δ |
|---|---|---|---|
| 15m | +0.15 | −6.76 | −4.85 |
| 30m | +0.63 | −6.76 | −4.96 |
| 60m | +12.07 | −7.54 | +8.13 |
| 120m | **+35.49** | −7.54 | **+25.56** |

- adverse_heat_note: early adverse ~−6.8 in first 30m (MAE −6.76), then followed through LONG — +8.13
  @60m, +25.56 close / +35.49 peak @120m.
- **human_review: HR-0001 — `SHADOW_CANDIDATE_LOW` / REVIEWED** (2026-07-10). Real Asia-Low sweep→OB/FVG/CHoCH
  cluster the machine under-detected; reverted MEDIUM→LOW as the corrected 1h HTF **opposes the LONG**. Not
  trade-ready.
- flags: candidate_only=true; execution_allowed / broker_execution_allowed / qst_allowed / order_intent
  / risk_sizing_allowed = **false**.

---

## SOJ-0002 — SWEEP_TO_CHOCH_CONTEXT — outcome_label: UNFAVOURABLE

- candidate_id `SWEEP_TO_CHOCH_CONTEXT-0000` · hint **LONG** · anchor `2026-07-09T00:03:01Z` · entry **4080.83** · data_quality **FULL**
- raw: `Farouks Playbook: Sweep low (bullish) on XAUUSD` | `Farouks Playbook: CHoCH UP on XAUUSD 3`
- classified: `SWEEP_LOW(LONG_HINT) -> CHOCH_UP(LONG_HINT)`

| Horizon | MFE | MAE | final close Δ |
|---|---|---|---|
| 15m | +8.87 | −3.50 | +3.94 |
| 30m | +8.87 | −6.87 | −2.29 |
| 60m | +8.87 | −14.28 | −12.81 |
| 120m | +8.87 | **−18.57** | −5.38 |

- adverse_heat_note: brief +3.94 @15m then faded/reversed; −12.81 @60m, −5.38 close @120m, MAE −18.57.
- **human_review: HR-0002 — `WATCH` / REVIEWED** (2026-07-10). Real sweep but entered late; CHoCH minor-in-chop;
  OB 4076.28–4076.89 breached on the fade; 1h HTF does not support the LONG. Reverted LOW→WATCH. Not
  trade-ready.
- flags: all safety flags false (as above).

---

## SOJ-0003 — BPR_TO_A_CONTEXT — outcome_label: UNFAVOURABLE

- candidate_id `BPR_TO_A_CONTEXT-0000` · hint **SHORT** · anchor `2026-07-09T05:42:01Z` · entry **4074.97** · data_quality **FULL**
- raw: `Farouks Playbook: BPR tapped on XAUUSD 3` | `Farouks Playbook: A SHORT on XAUUSD 3`
- classified: `BPR_TAPPED(neutral) -> A_SHORT(SHORT)`

| Horizon | MFE | MAE | final close Δ |
|---|---|---|---|
| 15m | +1.15 | −9.28 | −8.24 |
| 30m | +1.15 | −24.48 | −14.55 |
| 60m | +1.15 | −31.87 | −24.80 |
| 120m | +1.15 | **−36.16** | **−34.75** |

- adverse_heat_note: wrong direction; price rose against the short; MFE only +1.15, −34.75 close @120m,
  MAE −36.16.
- **human_review: HR-0003 — `REJECT` / REVIEWED** (2026-07-10). SHORT at a reversal low into a bullish impulse;
  bearish OB spent/traded-through; displacement bullish against; short thesis invalidated. Not trade-ready.
- flags: all safety flags false (as above).

---

## Roll-up (n=3 — NOT significant)

| outcome_label | count |
|---|---|
| FAVOURABLE | 0 |
| MIXED | 1 |
| UNFAVOURABLE | 2 |
| INCONCLUSIVE | 0 |

Directional agreement at 120m close: **1 / 3**. Adverse excursion material on all three. **Nothing
trade-ready** — n=3, single session. This journal exists to accumulate many more before any aggregate
means anything.

### Human review outcome (batch 001 — 3/3 REVIEWED, 2026-07-10)

| observation | candidate | human_review_id | final_label | review_status |
|---|---|---|---|---|
| SOJ-0001 | ALIGNED_CHOCH_TO_A | HR-0001 | **SHADOW_CANDIDATE_LOW** | REVIEWED |
| SOJ-0002 | SWEEP_TO_CHOCH_CONTEXT | HR-0002 | **WATCH** | REVIEWED |
| SOJ-0003 | BPR_TO_A_CONTEXT | HR-0003 | **REJECT** | REVIEWED |

**Zero trade-ready.** Common thread: **HTF was against the direction in all three.** See
`HUMAN_REVIEW_BATCH_001_SUMMARY.md`. Evidence bar **3 / 30 across ≥5 sessions — NOT MET** (a REJECT does not
count). `NOT_INTEGRATION_READY` unchanged.
