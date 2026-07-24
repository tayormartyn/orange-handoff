# Orange Pre-Marked Level Lane v0.1 (Expectancy Lane 6 — Research-Only Design)

**Mode: STEP 7B PRE-MARKED LEVEL RESEARCH LANE ONLY.** Observation-only. Date 2026-07-11.
This lane is an **analytic hypothesis generator**, never an order, limit order, copy-trade, broker/nano
connection, or execution instruction of any kind. It extends the R6 expectancy model with a sixth lane;
lanes 1–5 are unchanged. Deterministic OHLC remains the authority for every price fact; all records pass
the ai_review fail-closed validator + extended forbidden-token guard. Listener PID 87988 untouched; gates
`PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY` unchanged.

## 1. The question this lane answers

> *"Could Orange, using Farouk-style evidence available BEFORE the Telegram post, have marked a realistic
> level that produced a better hypothetical follower fill than waiting for the post?"*

Positioning against the existing lanes:

| lane | fill basis | limitation |
|---|---|---|
| dumb follower (lanes 2–4) | posted zone / post-time market, after the post | structurally late; J24-class scratches; worse fills than his |
| Farouk private fill (lane 1) | his market entry at decision time | unobservable in advance; only known from widgets afterwards |
| **Orange pre-mark (lane 6)** | a level constructed from pre-post evidence (his own published method) | hypothetical; must prove it matches his zones often enough to matter |

If Farouk's method is as mechanical as his own education content claims (OB/FVG/BPR + session liquidity +
CHoCH), then the levels are *constructible before he posts* — which would recover most of the
his-vs-follower fill gap. If the pre-marks don't match his posts, that is itself a finding (the edge is in
his discretion, not the published method).

## 2. Allowed pre-mark evidence sources (all must be timestamped BEFORE the pre-mark)

TradingView alert lane captures (CHoCH/Sweep/A sequences) · Asia high/low sweep context · CHoCH/BOS
structure · BPR/FVG/OB constructions per his education material · session high/low liquidity ·
prior-day plan posts (e.g. the 44877 "4,250–4,260 sell zone" chart — pre-marked levels he himself
publishes in advance) · Farouk-style level-construction rules from `FAROUK_METHODOLOGY_FACTOR_MAP_v0_1` /
`FAROUK_ORDER_BLOCK_PROXY_POLICY_v0_1` / the education corpus. **Never future outcome data.**

## 3. Anti-leakage contract (hard)

A pre-mark record is VALID only if every evidence item it cites has
`evidence_timestamp < pre_mark_time_utc <= farouk_post_time_utc`. Explicitly forbidden as inputs:
Farouk's later post itself · post-result screenshots · later TP/SL touches · headline claims · any OHLC
after `pre_mark_time_utc`. Retrospective studies must **freeze the evidence window first** (messages +
alerts + bars strictly before the pre-mark time), construct the level from that frozen window only, and
log the frozen-window hash alongside the record. A pre-mark citing any post-dated evidence is
auto-invalidated (`PRE_MARK_INSUFFICIENT_CONTEXT`, leak flag set) — enforcement in the builder script, not
reviewer discipline.

## 4. Record fields

`setup_id · pre_mark_time_utc · pre_mark_source (evidence list with timestamps + frozen-window hash) ·
pre_mark_direction · pre_mark_level_or_zone · farouk_post_time_utc · time_before_post_seconds ·
distance_from_farouk_posted_zone · distance_from_farouk_private_fill_if_known ·
was_pre_mark_touched_before_post · was_pre_mark_touched_after_post · hypothetical_pre_mark_mfe ·
hypothetical_pre_mark_mae · would_r2_r4_r6_pass (the pre-mark inherits the same scoring predicates) ·
pre_mark_outcome_status · confidence`

**Allowed labels:** `PRE_MARK_OBSERVED` · `PRE_MARK_MATCHED_FAROUK` · `PRE_MARK_DID_NOT_MATCH` ·
`PRE_MARK_INSUFFICIENT_CONTEXT` · `PRE_MARK_EXPIRED`.
**Forbidden (keys or labels):** TRADE_READY · EXECUTE · ORDER · COPY_TRADE · NANO · LIVE · DEMO_EXECUTE
(+ the full extended-guard superset: LOT_SIZE, BROKER_ROUTE, ACCOUNT_ID, RISK_SIZE, …).

## 5. Retrospective test protocol (per known setup)

1. Freeze the evidence window at `farouk_post_time_utc − ε` (all captured messages/alerts/bars before it).
2. Ask: did pre-post evidence exist for a Farouk-style level? If no → `PRE_MARK_INSUFFICIENT_CONTEXT`
   (honest expected outcome for most June setups — the TV alert lane only started Jul-7, and intraday
   structure data before the post is limited to OHLC).
3. If yes: construct the hypothetical level mechanically (documented rule, e.g. "prior-day plan post
   named 4250–4260" or "Asia low + 5m FVG per his stated recipe"), then compute touch times and
   hypothetical MFE/MAE deterministically.
4. Compare: distance to his posted zone and to his private fill (when widgets exist); label
   `PRE_MARK_MATCHED_FAROUK` (within a stated tolerance, e.g. ≤ $3) or `PRE_MARK_DID_NOT_MATCH`.
5. Aggregate: match rate, fill improvement vs lanes 2/3, and whether lane-6 expectancy > lane-4 expectancy.
   Known seed case: **44877** — his own Jun-18 22:13Z evening chart pre-marked a "4,250–4,260 sell zone"
   (Asia low + BPR + weekly resistance) **for the following session**. Note the correction: it was posted
   AFTER that day's J21 trade, so it seeds the Jun-19 session — where price never returned to 4250s (the
   day's trade was J23, a 4154–4164 BUY far below). First honest data point: pre-marked level VALID but
   UNTOUCHED — illustrating both that he does publish advance levels and that the match-rate question is
   completely open (n≈1).

## 6. Forward test protocol (Cycle 002+)

Before/at the earliest alert context of a session, Orange may write `PRE_MARK_CANDIDATE` records
(review-only, validator-passed, labelled `PRE_MARK_OBSERVED`, expiring to `PRE_MARK_EXPIRED` at session
end). When Farouk later posts, the comparison is computed and the label updates to
`PRE_MARK_MATCHED_FAROUK` / `PRE_MARK_DID_NOT_MATCH`; when OHLC arrives, hypothetical outcomes are matched
deterministically alongside the XAU-F record. Pre-marks are never routed anywhere except the ledger and
human review — **they cannot become orders and there is no execution path for them to reach**.

## 7. Theoretical fill-improvement potential (honest statement)

Yes in principle: J24/J30-class divergences (−65 to −267p per trade vs his fills) are exactly the gap a
correct pre-mark would close, because his own fills ARE pre-post decisions. But the lane's value is
entirely conditional on the match rate, which is unknown (n=1 seed observation). If forward match rate is
low, the correct conclusion is that the published method under-determines his levels — equally valuable,
because it caps what any follower system can ever capture.

## 8. Safety confirmation

Design only; no code run against live systems. No broker/QST/cTrader/nano/copy/demo/live execution; no
permits/leases/orders; no limit orders or order intent of any kind; gates unchanged; listener PID 87988
running (start 2026-07-10 21:54:45 unchanged); no TradingView-alert changes (the alert lane is read as
evidence only); no Worker/R2/secret action. `NOT_INTEGRATION_READY` unchanged.

## Next step

Implement lane-4 (follower expectancy) + the lane-6 retrospective protocol in one offline pass over the 34
matched setups — expect mostly `PRE_MARK_INSUFFICIENT_CONTEXT` for June (honest), with the 44877→J21 seed
case and any Jul-7+ alert-aligned setups as the first real lane-6 data — then forward Cycle 002.
