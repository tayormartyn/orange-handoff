# Human Review Packet Template v0.1

What to capture for one candidate so it can be reviewed. **Observation-only.** No account/broker/personal
info. `NOT_INTEGRATION_READY` unchanged.

---

## Packet: `<review_id>` — candidate `<candidate_id>`

- **Anchor (UTC):** `<anchor_time_utc>`
- **Direction hint:** `<LONG/SHORT>` (bias descriptor, not an order side)
- **Raw alert sequence:** `<raw texts>`
- **Outcome summary:** `<MFE/MAE/close per horizon; outcome_label>`
- **Machine proxies to verify:** OB `<proxy>`, FVG `<proxy>`, displacement `<yes/no>`, session
  `<proxy/UNCONFIRMED>`, HTF `<proxy>`

## Screenshots to capture (attach to the review)

Capture each with **price scale visible** and **timestamps/clock visible**. Use **UTC** on the chart if
possible (note the chart timezone if not — it is currently unresolved).

1. **1m chart around the candidate** — anchor centred, **~60–120 min before and after** the anchor.
2. **3m chart around the candidate** — same window (matches the Farouk alert timeframe).
3. **15m chart context** — if available, a few hours around the anchor (for structure/HTF read).
4. **1h chart context** — if available, ~1–2 days around the anchor (for HTF bias read).

For each screenshot, mark (arrow/note): the OB proxy zone, the FVG proxy, the displacement candle, the
sweep/CHoCH point, and the anchor candle.

## Capture rules

- **Show the price scale and the time axis / clock.**
- **UTC preferred**; if the chart is in another timezone, write down which one (do not guess an offset).
- **Do NOT include:** account numbers, broker/platform login, P&L/positions panel, balance, order tickets,
  or any personal information. Crop them out.
- Save images with the review_id in the filename (e.g. `HR-0001_1m.png`). Store locally; do not paste
  large images into chat — reference the filenames.

## After capture

Fill the review record per `HUMAN_REVIEW_SCHEMA_v0_1.md` using
`FAROUK_HUMAN_REVIEW_CHECKLIST_v0_1.md`, then set `review_status = REVIEWED` (or `NEEDS_MORE_DATA`).
Reviewing evidence only — **no trade, no order, no broker action.**
