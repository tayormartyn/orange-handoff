# ORANGE — START HERE (read this first, every session)

**Built 2026-07-20 (ORANGE BRAIN v0.1).** This directory is Orange's persistent memory. It is DERIVED — it never overrides the forward ledger, freeze ledgers, campaign cards, raw Telegram capture, market data, constitutions or live config. Where the brain and those files disagree, THOSE FILES WIN. Refresh state with `python brain_refresh.py` (or repo-root `ORANGE_BRAIN_REFRESH.ps1`).

## Objective
Reverse-engineer Farouk's XAUUSD selection + management method into deterministic, prospectively-validated rules by read-only observation of his Telegram/Discord signals, his TradingView indicator, and live market data. No execution. Evidence first; fail closed on ambiguity; never manufacture, backdate or repair campaigns/freezes.

## Lanes
- **Lane A** — STRICT_FOLLOWER: what a disciplined follower of the *published* signals would bank under the ratified constitution. The ONLY headline numbers.
- **Lane B** — POLICY_SENSITIVITY: research variants (touch-fill, avg-BE, keep-unfilled…). Never labeled as Farouk's or headline results.
- **Lane C** — future controlled-execution route. DOES NOT EXIST yet; gated behind NOT_INTEGRATION_READY + explicit Martyn approval. (Distinct from "lane6" = the indicator alert/pre-mark lane.)

## Hard gates (any change = stop)
`MODE=PAPER` · `LISTENER_MODE=PREVIEW` · `EXECUTION_ENABLED=False` · `CTRADER_EXECUTION_ENABLED=False` · `NOT_INTEGRATION_READY` · cTrader scope `accounts` (view-only) · no credentials · no broker · no sizing · **no model fitting without explicit governance sign-off** (a research-proposed floor of ≥15 forward campaigns / ≥5 sessions exists in code — `ranking_harness.py` — but is `PROPOSED_RESEARCH_GATE_NOT_AUTHORISED`, decision D-009; never cite the number as established law; currently 2 genuine prospective campaigns and NOT_FITTED).

## Live stack (7 read-only processes — do not restart casually; never two listeners)
listener · tracker (live_tv_bars/R2) · live wire · evidence watcher · outcome companion · shadow simulator · intake observer. Locks store PIDs with NO stale detection — delete a lock only after proving its PID dead. Restart recipe + conventions: `project_state_v0_1.json` + user-memory conventions.

## Campaigns (authority: forward ledger 63 lines + freeze ledgers + cards)
| ID | Class | Lifecycle | Lane A |
|---|---|---|---|
| F001 | backfill, NOT prospective | CLOSED/FROZEN | +4.42 |
| F002 | backfill, NOT prospective | CLOSED/FROZEN | +9.95 |
| F003 | authentic, NOT prospective (watcher race; NO freeze) | CLOSED (adjudicated) | 0.00 NO_FILL |
| F004 | **GENUINE PROSPECTIVE** (freeze 6047bde5) | CLOSED/FROZEN | +15.18 |
| F005 | **GENUINE PROSPECTIVE** (freeze f7557245) | CLOSED (late-recovery) | 0.00 NO_FILL (Lane B +94.17 research) |

**Genuine prospective count = 2 (F004, F005). Genuine freeze ledger = exactly those 2. F003 must never gain a freeze.**

## Latest accepted corrections
- **CORRECTION_001 (2026-07-20):** the Sunday-video claim that "Farouk's Playbook — Smart Money Suite" was a new discovery is RESCINDED — indicator existence, panel, alert catalogue and live payloads were prior art (FP-INDICATOR-005/006, ORANGE_INDICATOR_KNOWLEDGE_AUDIT.md, FP-LIVE-OBSERVATION-001). Sunday verdict superseded to **LIMITED_INCREMENTAL_VALUE**. Genuine survivors: continuity-frame corpus (K-016), "no FVG, no OB" attestation (K-015), H-FPL-05 pre-open plan (K-017), unposted-trades blind spot (K-018), BPR-substitution nuance (K-019), version-drift risk (K-020).
- Standing rule: **run `novelty_gate.py` before calling any finding new/first/major.**

## Known defects
**Open code defects: NONE.** Open risks/limitations (see `known_defects_v0_1.json`): indicator version drift · Discord video links uncaptured · unposted-trades blind spot · repaint not fully verified / A-grade formula invisible · 6-message operator review queue · unplanned host reboots (OQ-7). Resolved-with-evidence (do NOT reopen without new evidence): quantity_base guard (guards sha `213b4463bda22707`), watcher race, close-100% gap, F004 leg-cancellation (constitutional per ratified Q3).

## Current evidence priority
**Prospective evidence above everything.** Priority 1 = score H-FPL-05 (pre-registered Sunday weekly plan) against this week's live bars — zero leakage, expires with the week.

## Authoritative files (consult, never summarize-and-trust)
`farouk_plus/forward_validation_ledger_v0_2.jsonl` · `follower_assistant/evidence_layer/router_freeze_v0_1.jsonl` (+`_backfill_`) · `follower_assistant/cards/*.json` · `follower_assistant/follower_constitution_v0_1.json` (sha 7bce618f) · `follower_assistant/guards.py` (sha 213b4463) · `ORANGE_MASTER_SOURCE_OF_TRUTH_vNEXT.md` · `ORANGE_INDICATOR_KNOWLEDGE_AUDIT.md` · `derived/live_video_20260719/CORRECTION_001_INDICATOR_PRIOR_ART.md` · this brain's registers.

## AUTHORITATIVE WORK ORDER (operator, 2026-07-20, **D-015** — supersedes D-010/D-014 ordering; may not be reshuffled without an operator decision)
1. **H-FPL-05 FINAL** (Friday post-21:00Z; harness live at `derived/live_video_20260719/h_fpl_05/`)
2. **TASK 1B corpus ingest** (`work_orders/TASK_1B_CORPUS_SPEC.md`)
3. **PARSER COVERAGE REPLAY** (read-only prerequisite; `work_orders/PARSER_COVERAGE_REPLAY_SPEC.md`)
4. **ALERT_LANE_MONITOR build** (prerequisite; named defect ALERT_LANE_SILENCE_UNMONITORED)
5. **DEMO COPY-TRADE LANE** (gated; requires 3+4 proven — live fill/spread/latency evidence is perishable)
6. **H-FPL-02** offline event study (params frozen) · 7. **Stage 2 rule mining** · 8. back-data replay / hypothesis screening
Martyn meanwhile: quarantine queue review; optional directional-A time-box (`work_orders/DIRECTIONAL_A_TIMEBOX_CHECKLIST.md`).

## Autonomy split (v0.1)
Fable MAY autonomously: inspect state, refresh derived summaries, reconcile evidence, check novelty, flag contradictions, update claim confidence append-only, produce operator briefs, rank next actions, prepare bounded proposed work orders.
Fable may NOT autonomously: change strategy, alter the constitution, rewrite frozen evidence, mutate campaign outcomes, fit/promote models, activate broker/demo/live execution, change risk/sizing, or execute a proposed work order without Martyn's approval.
