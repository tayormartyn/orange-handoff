# Human Review Queue v0.1

Seeded from the 3 outcome-matched Gate G candidates. All **PENDING**. **Observation-only; candidate-only;
reviewing evidence, not trades.** Machine copy: `human_review_queue_v0_1.csv`.
`NOT_INTEGRATION_READY` unchanged.

## Queue (3 REVIEWED / 0 PENDING — all reviewed)

### HR-0001 — ALIGNED_CHOCH_TO_A-0000 — priority 1 (HIGH) — ✅ REVIEWED (closed)
- anchor `2026-07-09T04:12:01Z` · hint **LONG** · machine score **0.375** / `SHADOW_CANDIDATE_LOW` · outcome **MIXED**
- proxies (machine): OB **none**, FVG **bullish**, displacement **no (1.91×)**, session **ASIA_UTC_PROXY (UNCONFIRMED)**, HTF **CONFIRMED bearish — opposes LONG** (corrected Jul-9 1h)
- **review_status: REVIEWED (2026-07-09) — closed**. All four valid screenshots present (1m / 3m / true-15m TF=15 / Jul-9 1h TF=60). See `HUMAN_REVIEW_HR_0001_RESULT.md`, `HUMAN_REVIEW_HR_0001_FORM.md`, `HR_0001_MISSING_SCREENSHOT_REQUEST.md` (now resolved).
- **Final human label: `SHADOW_CANDIDATE_LOW`** (**reverted** from provisional MEDIUM) — **observation-only; NOT trade-ready, NOT demo-ready, NOT permission to trade.**
- Visual finding: real Asia-Low **sweep → OB + BPR + FVG + CHoCH** cluster at the anchor that the crude machine proxies **under-detected** (confirmed by human review); chart tz observed **UTC+1**. Reverted to LOW because the corrected Jul-9 1h confirms a **multi-day downtrend into the anchor → HTF BEARISH, opposes the LONG (counter-trend)**; combined with the MIXED outcome, ungraded setup and n=1.
- **Standing missing evidence (non-blocking, not required to close):** grade (ungraded), Telegram/Discord confirmation, larger sample.

### HR-0002 — SWEEP_TO_CHOCH_CONTEXT-0000 — priority 2 (MED) — ✅ REVIEWED (closed)
- anchor `2026-07-09T00:03:01Z` · hint **LONG** · machine score **0.690** / `SHADOW_CANDIDATE_LOW` · outcome **UNFAVOURABLE**
- sequence: **SWEEP_LOW 23:45Z → CHoCH_UP 00:03Z**; entry ref 4080.83
- **review_status: REVIEWED (2026-07-10) — closed.** All four screenshots valid on the correct **Jul 8→9** session (corrected 1m "Thu 09 Jul '26 00:04" ~4080 + 3m ~4020–4140 anchor ~4080; 15m TF=15; 1h TF=60 UTC+1). See `HUMAN_REVIEW_HR_0002_RESULT.md`, `HUMAN_REVIEW_HR_0002_FORM.md`.
- **Final human label: `WATCH`** (**reverted down** from provisional `SHADOW_CANDIDATE_LOW`) — **observation-only; NOT trade-ready, NOT demo-ready, NOT permission to trade.**
- Visual finding: real sweep of the ~4030 low but **entered late** (4080.83); **CHoCH minor-in-chop**; **OB (4076.28–4076.89) breached** on the fade (low ≈ 4062); displacement only moderate; **HTF (valid 1h) does NOT support the LONG** (multi-day downtrend into Jul 9). Brief +8.87 MFE then faded to −5.38 close, MAE −18.57 → **failed weak-context setup**.
- **Standing missing evidence (non-blocking):** grade (ungraded), Telegram/Discord confirmation, larger sample.

### HR-0003 — BPR_TO_A_CONTEXT-0000 — priority 3 (LOW) — ✅ REVIEWED (closed)
- anchor `2026-07-09T05:42:01Z` · hint **SHORT** · machine score **0.500** / `SHADOW_CANDIDATE_LOW` · outcome **UNFAVOURABLE**
- entry ref 4074.97; screenshot window `2026-07-09T03:42:01Z .. 07:42:01Z`
- **review_status: REVIEWED (2026-07-10) — closed.** All four screenshots valid on the correct **Jul 9** session (1m "Thu 09 Jul '26 05:41" ~4075; 3m swept low ~4055 → Asia High ~4133; 15m TF=15; 1h TF=60 crosshair "Thu 09 Jul '26 06:00"). See `HUMAN_REVIEW_HR_0003_RESULT.md`, `HUMAN_REVIEW_HR_0003_FORM.md`.
- **Final human label: `REJECT`** — **observation-only; NOT trade-ready, NOT demo-ready, NOT permission to trade.** (A REJECT does not count toward the 3/30 evidence bar.)
- Visual finding: A SHORT fired at ~4075 **at a reversal low into a bullish impulse**; **bearish OB (4071.48–4072.05) spent/mitigated** and traded straight through; displacement **bullish (against the short)**; FVGs bullish; 1h multi-day down but anchor bounced off Asia Low → **immediate bias opposed the SHORT**. Ran ~36 against (MFE +1.15, MAE −36.16, close −34.75) → **failed / invalidated short thesis**.
- Standing missing evidence (non-blocking): grade, Telegram/Discord, larger sample.

## How to work the queue

For each row: build the packet (`HUMAN_REVIEW_PACKET_TEMPLATE_v0_1.md`), capture screenshots, answer the
checklist (`FAROUK_HUMAN_REVIEW_CHECKLIST_v0_1.md`), fill a review record
(`HUMAN_REVIEW_SCHEMA_v0_1.md`), set `review_status`. Apply the decision rules
(`HUMAN_REVIEW_DECISION_RULES_v0_1.md`).

## Reminder

Evidence threshold is **3/30 — NOT MET**. No candidate is trade-ready; reviewing these three cannot make
any of them trade-ready. It only sharpens the shadow evidence and tests the proxies.
