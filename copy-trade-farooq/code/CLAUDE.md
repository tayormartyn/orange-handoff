# signal-terminal — project instructions for Claude Code (Fable)

## ORANGE BRAIN — mandatory session start (added 2026-07-20, ORANGE BRAIN v0.1)

This repository hosts ORANGE: read-only reverse-engineering of Farouk's XAUUSD method. A persistent project brain lives at `research/farouk_pilot/orange_brain/`. **Do not ask Martyn to re-explain the project — the brain answers it.**

At the start of EVERY session in this repository:
1. Read `research/farouk_pilot/orange_brain/START_HERE.md` (objective, lanes, gates, campaigns, corrections, priority).
2. Refresh state: `python research/farouk_pilot/orange_brain/brain_refresh.py` (writes only inside orange_brain/). Use `--status` for print-only.
3. Read `research/farouk_pilot/orange_brain/operator_brief.md` and `next_actions.md`.
4. Check `known_defects_v0_1.json` and `open_questions_v0_1.json`.
5. Before declaring ANY research finding new/first/major, run:
   `python research/farouk_pilot/orange_brain/novelty_gate.py --claim "<statement>"`
   and consult the `orange-brain-reviewer` agent for prior-art/novelty/campaign-provenance review.
6. Classify the user's request before working: does it (a) advance the project, (b) duplicate completed work (say so and point to the artifact), (c) require new evidence, or (d) conflict with a hard gate (refuse and cite the gate)?

## Hard gates (never change; any change = stop and report)
`MODE=PAPER` · `LISTENER_MODE=PREVIEW` · `EXECUTION_ENABLED=False` · `CTRADER_EXECUTION_ENABLED=False` · `NOT_INTEGRATION_READY` · no broker connection, credentials, sizing or order code · **no model fitting without explicit governance sign-off** (the "≥15 campaigns / ≥5 sessions" floor in ranking_harness.py is PROPOSED_RESEARCH_GATE_NOT_AUTHORISED — decision D-009 — never cite it as established law) · never manufacture/backdate/repair campaigns or freezes · fail closed on ambiguity.

## Authority order
Forward ledger, freeze ledgers, campaign cards, raw Telegram evidence DB, constitutions and live config are AUTHORITATIVE. The brain (`orange_brain/`) is DERIVED — when they disagree, the ledgers win and the brain must be refreshed/corrected append-only.

## Live stack rules
Seven read-only python services run detached (listener, tracker, wire, watcher, companion, shadow, observer). Never start a second listener. Instance locks store PIDs with NO stale detection — delete a lock only after proving its PID dead. Do not restart services without cause; follow the established Start-Process detached recipe with per-service logs.

## Known non-negotiables (see brain for citations)
- The Playbook indicator (FP-INDICATOR-005/006), its panel and alert catalogue are PRIOR ART — never present them as new discoveries (see `derived/live_video_20260719/CORRECTION_001_INDICATOR_PRIOR_ART.md`).
- Pip-count/result messages are never terminal exits (interpreter doctrine).
- Lane A numbers are the only headline numbers; Lane B is research.
- Genuine prospective campaigns = exactly the genuine freeze ledger's records (currently F004, F005).
- NEVER automate or interact with the TradingView alert dialog (alert-mutation risk) — below-fold/settings screenshots are supplied manually by Martyn (D-011).
- Crypto material is instrument-scope-tagged and hard-isolated: no crypto-derived rule, parameter or observation enters XAUUSD rules, features or hypotheses (K-047).

## Fable autonomy split (v0.1)
MAY autonomously: inspect state, refresh brain summaries, reconcile evidence, novelty-check, flag contradictions, update claim confidence append-only, write operator briefs, rank next actions, prepare bounded proposed work orders.
May NOT autonomously: change strategy/constitution, rewrite frozen evidence, mutate campaign outcomes, fit/promote models, activate broker/demo/live execution, change risk/sizing, or execute proposed work orders without Martyn's approval.
