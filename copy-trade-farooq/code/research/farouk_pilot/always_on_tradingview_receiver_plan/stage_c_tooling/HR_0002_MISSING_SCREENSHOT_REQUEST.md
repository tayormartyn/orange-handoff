# HR-0002 — Missing Screenshot Request

> **⚠️ UPDATE (2026-07-10) — 4 screenshots received, but the 1m and 3m are the WRONG NIGHT.**
> The **15m (true TF=15)** and **1h (true TF=60, UTC+1 confirmed)** are valid and cover the anchor date —
> keep them. But the **1m** (`HR-0002_1m.png`, axis "Fri 10 Jul '26 00:03", price ~4122) and **3m**
> (`HR-0002_3m.png`, price ~4100–4140, Asia High/Low of the current session) show the **Jul 9→10** Asia
> session — roughly **24 hours after** the HR-0002 anchor. The anchor is **Jul 9 00:03 UTC = 01:03 chart
> time (UTC+1)**, in the **Jul 8→9** overnight at price **~4080**. Please **re-capture the 1m and 3m only**,
> scrolled back to the anchor. Everything else below still applies. Review stays `NEEDS_MORE_DATA`.

The HR-0002 review is **held open at `NEEDS_MORE_DATA`**. The provisional label `SHADOW_CANDIDATE_LOW` is
**observation-only — not trade-ready, not demo-ready, not permission to trade.** `NOT_INTEGRATION_READY`
unchanged.

## Anchor

- **2026-07-09 00:03 UTC** (CHoCH_UP; the sweep that precedes it is at ~23:45Z on 2026-07-08).
- If your chart clock is **UTC+1**, the anchor appears around **01:03 chart time** — centre captures there.
- Review window: roughly **2026-07-08 22:03Z → 2026-07-09 02:03Z**.

## Please capture (XAUUSD · Pepperstone)

1. **1m chart** around the anchor — show the **23:45Z sweep low**, the **00:03Z CHoCH up**, and the region
   just below entry (~4076–4081). Save as `HR-0002_1m.png`.
2. **3m chart** around the anchor for structure context. Save as `HR-0002_3m.png`.
3. **True 15m chart** (timeframe selector on **15m**, not 1m) covering the anchor. Save as `HR-0002_15m.png`.
4. **1h chart covering Jul 9** (timeframe **1h**, scrolled so **2026-07-09** is in view, ~Jul 7 → Jul 10)
   for HTF bias. Save as `HR-0002_1h.png`.

### Each screenshot must show
- **Price scale visible** and **time axis / clock visible**.
- **State the chart timezone** (confirm the footer, e.g. "… UTC+1").
- **No account / balance / order tickets / positions / P&L / login / personal info** — crop them out.

### Save to
`stage_c_tooling/human_review_screenshots/HR-0002/`

## What the review will test
- Was the **23:45Z sweep** a real liquidity sweep or mid-range noise?
- Was the **00:03Z CHoCH** a meaningful structural break?
- Was there a **visually credible bullish order block** near 4076.28–4076.89, and did it look fresh?
- Machine note to verify: the follow-through **broke below that OB zone** (MAE ≈ low 4062), i.e. the OB
  appears to have **failed** — does the chart agree?
- Did **HTF (1h)** support or oppose the LONG? (1h proxy was insufficient-data; needs a real Jul-9 1h.)

## Optional (strengthens the record, not required to close)
- Telegram/Discord confirmation that the Farouk channel flagged this sweep→CHoCH context (integrity check
  only — not a trade signal).

## After you provide them
Tell me and I'll finish the HR-0002 review: confirm/deny the sweep, CHoCH and OB, resolve HTF bias, finalise
the label (holds at `SHADOW_CANDIDATE_LOW`, or reverts toward `WATCH` / `CONTEXT_ONLY` if the setup is not
visually credible), and set status to `REVIEWED`. Still observation-only — no trade, no order, no broker.
