# AI Evidence Reviewer — Architecture (v0.1)

**Mode: architecture + isolated lane build. Observation-only.** No AI API called; no secrets; no
broker/execution surface. Deterministic validators are the authority. `NOT_INTEGRATION_READY` unchanged.
Date 2026-07-11.

## Purpose

Let an AI model (Fable 5 preferred, but provider-neutral) **assist the validation sprint** by extracting and
reviewing evidence packs — Telegram trade text, screenshots (by reference), OHLC summaries, TV-alert context —
and flagging contradictions/missing evidence. The AI **reviews evidence; it never trades, sizes, routes, or
promotes anything to trade-ready.**

## Location + isolation

- Code: **`signal-terminal/ai_review/`** — isolated top-level lane: `schema.py` (schemas + fail-closed
  validator), `stub_reviewer.py` (provider seam + mock backend), `fixtures/`, `tests/`.
- It imports **nothing** from broker/execution/order/permit/lease/module_b code (asserted by test).
- Docs: this file + `AI_EVIDENCE_REVIEWER_SAFETY_CONTRACT.md` (stage_c_tooling).

## Provider-neutral design

A **reviewer** is any callable `review(pack: dict) -> dict` registered in `stub_reviewer.REVIEWERS`.
Every backend's raw output must pass `schema.validate_reviewer_output()` — the deterministic authority.

| provider | status | how it attaches later |
|---|---|---|
| `stub` | **implemented** (rule-based mock; no network) | already registered |
| Fable 5 | planned | via the active Claude Code session (this tool) or the Claude API (`claude-fable-5`); no gate change needed — it only fills the same `review()` seam |
| Claude/Sonnet | planned | same seam, different model id |
| Gemini | planned | same seam via its own adapter |
| ChatGPT / manual human | planned | human pastes structured JSON; same validator applies |

No provider is mandatory; the validator treats all identically. **Model/config note:** `~/.claude/settings.json`
now sets `"model": "claude-fable-5[1m]"` (the old Opus 4.8 pin was overwritten by `/model`); new Claude Code
sessions start on Fable 5 — the current session still runs Opus 4.8 until restart.

## Input schema — one evidence pack (`validate_evidence_pack`)

Required: `pack_id`, `instrument`, `source_channel`, `messages[]` (each: `message_id`, `timestamp_utc`,
`raw_text`). Optional: `media[]` (each: `message_id`, `sha256`, `path`), `ohlc_summary`, `tv_alert_context`,
`notes`. Fixture: `ai_review/fixtures/fp_live_trade_obs_003_xauusd.json` (the Jul-10 XAU SELL pack — msgs
45625–45635 + the 4 recovered screenshot sha256s).

## Output schema — reviewer result (`validate_reviewer_output`)

Required: `pack_id`, `extracted_instrument`, `direction`, `entry_zone`, `sl`, `tp_levels[]`, `result_claim`,
`evidence_used[]`, `confidence` (0–1), `contradictions[]`, `missing_evidence[]`, `ohlc_required` (bool),
`verdict` ∈ **EXTRACTED / UNCLEAR / CONTRADICTORY / NEEDS_HUMAN_REVIEW** (review-only; no trade verdict
exists). Every accepted output is **stamped** `review_only=True, executable=False, trade_ready=False,
observation_only=True` — by the validator, overriding anything a provider sends.

## Fail-closed safety validation

- Any key containing a forbidden execution substring — `order, order_type, lot(_size), risk, account(_id),
  broker, ctrader, qst, permit, lease, execute/execution, trade_now, route, position_size, qty` — anywhere
  (recursively) in a reviewer output → **ReviewerOutputRejected**.
- Invalid verdict / missing fields / out-of-range confidence → rejected.
- A provider claiming `trade_ready=true` or `review_only=false` is silently overridden by the stamp.

## Where it plugs into the sprint

Day 1+: each reconstructed XAU discretionary trade becomes one evidence pack → AI reviewer extracts
entry/SL/TP/result-claim + flags contradictions → **deterministic outcome-matcher (OHLC) computes the actual
result** → human review where AI/deterministic disagree. SOL/BTC packs stay in the side lane. AI output is
never fed to the campaign state machine as a signal — only as extraction assistance for building packs.

## Tests — 11/11 PASS

fixture validates; stub extracts the XAU pack (SHORT, 4102–4115, SL 4152, TP 4077/4055, ohlc_required=True);
every forbidden field rejected (flat + nested); provider cannot self-declare executable; invalid
verdict/missing field/confidence bounds rejected; contradiction flagging works; unknown provider rejected;
no forbidden imports in the lane.
