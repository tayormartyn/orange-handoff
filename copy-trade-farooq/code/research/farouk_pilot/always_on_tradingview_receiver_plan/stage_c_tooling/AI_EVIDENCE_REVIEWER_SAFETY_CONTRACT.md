# AI Evidence Reviewer — Safety Contract (v0.1)

**Binding on every AI/human/stub reviewer backend. Enforced in code by
`ai_review/schema.validate_reviewer_output` (fail-closed) — deterministic validators are the authority.**
`NOT_INTEGRATION_READY` unchanged. Date 2026-07-11.

## The AI may (review-only)

- **Extract** instrument / direction / entry zone / SL / TP levels / result claims from evidence packs.
- **Review & explain** what the evidence shows, message by message.
- **Compare** claims against supplied OHLC summaries or TV-alert context.
- **Flag contradictions** (e.g. long+short language, claim vs data mismatch) and **missing evidence**.
- Emit only the four review verdicts: `EXTRACTED`, `UNCLEAR`, `CONTRADICTORY`, `NEEDS_HUMAN_REVIEW`.

## The AI may NEVER (rejected in code)

- Emit **broker orders** or anything order-like (`order`, `order_type`, `trade_now`, `execute`, `route`).
- Emit **lot sizes / position sizes / quantities** (`lot`, `lot_size`, `position_size`, `qty`) or **risk
  sizing** (`risk`).
- Emit **account identifiers** (`account`, `account_id`) or **broker/platform hooks** (`broker`, `ctrader`,
  `qst`).
- Create or reference **permits/leases** (`permit`, `lease`).
- **Change gates** — the lane has no access to `config` gates; gates stay
  `MODE=PAPER / LISTENER_MODE=PREVIEW / EXECUTION_ENABLED=False / CTRADER_EXECUTION_ENABLED=False`.
- **Promote anything to trade-ready** — there is no trade-ready verdict; the validator stamps
  `review_only=True, executable=False, trade_ready=False, observation_only=True` on every accepted output,
  overriding any provider claim.

## Enforcement (fail-closed)

1. **Forbidden-key sweep** over every nested key of the reviewer output; any match →
   `ReviewerOutputRejected` (output discarded, nothing downstream sees it).
2. **Schema + verdict enum + confidence bounds** enforced; malformed output rejected.
3. **Safety stamp** applied by the validator, not the provider.
4. **No execution imports** in `ai_review/` (tested).
5. AI output is **advisory extraction only** — it is never fed to the campaign state machine, detector, or
   any downstream pipeline as a signal, and never treated as an instruction to act.

## Authority order

**Deterministic validators > human review > AI output.** Where AI extraction and the deterministic
outcome-matcher disagree, the pack goes to `NEEDS_HUMAN_REVIEW`; the OHLC-computed result stands.

## Verified by tests (11/11 PASS)

`ai_review/tests/test_ai_evidence_reviewer.py` proves: each forbidden field (`order`, `order_type`,
`lot_size`, `risk`, `account_id`, `broker`, `cTrader`, `permit`, `lease`, `execute`, `trade_now`) is rejected
flat **and** nested; a provider cannot self-declare executable/trade-ready; invalid verdicts rejected; the
stub provider round-trips the real XAU fixture; the lane imports no execution code.
