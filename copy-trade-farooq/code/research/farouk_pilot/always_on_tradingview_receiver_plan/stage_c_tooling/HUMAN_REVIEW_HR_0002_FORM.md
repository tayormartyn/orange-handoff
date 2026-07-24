# Human Review Form — HR-0002 (FINAL — corrected 1m/3m validated)

**Observation-only. Confirms EVIDENCE, not a trade.** `candidate_only=true`; execution / broker / qst /
order_intent / risk_sizing = **false**. `NOT_INTEGRATION_READY` unchanged.

- review_id: **HR-0002**
- candidate_id: SWEEP_TO_CHOCH_CONTEXT-0000
- anchor_time_utc: 2026-07-09T00:03:01Z  (chart tz **UTC+1** → anchor = **01:03 chart time**, Jul 9)
- direction_hint: LONG
- sequence: **SWEEP_LOW 23:45Z → CHoCH_UP 00:03Z** (anchor = the CHoCH_UP)
- entry_reference_price (descriptive): 4080.83
- outcome_label: **UNFAVOURABLE**

---

- **reviewer:** assistant-assisted visual review (Claude) — **awaiting Martyn countersign**
- **review date (UTC):** 2026-07-10 (finalised after corrected 1m/3m)
- **screenshots captured (yes/no):** **YES — all four valid and on the correct session:**

| File | Actual content | Valid TF | Correct window (Jul 8→9, anchor ~4080)? |
|---|---|---|---|
| HR-0002_1m.png | **TF=1**, midnight axis "**Thu 09 Jul '26 00:04**", price ~4050–4090 | ✅ true 1m | ✅ **YES — corrected** |
| HR-0002_3m.png | **TF=3**, window ~4020–4140, crosshair/anchor region ~4050–4085, swept low ~4030 | ✅ true 3m | ✅ **YES — corrected** |
| HR-0002_15m.png | **TF=15**, ~Jul 8 → Jul 14 | ✅ true 15m | ✅ covers anchor date |
| HR-0002_1h.png | **TF=60**, footer **UTC+1**, ~Jul 3 → Jul 9 | ✅ true 1h | ✅ covers Jul 9 |

- **chart timezone used:** **UTC+1** (confirmed). OHLC export is Unix-epoch = true UTC, so the 00:03Z anchor
  / entry 4080.83 remain correct.

### Per-factor verdicts

- **Sweep review:** `CONFIRMED (moderate)` — a real liquidity sweep of the Jul 8 late-session low (~4030)
  with reversal, plus a smaller intraday sweep (ST labels ~4065) near the anchor. **Caveat:** the anchor
  entry 4080.83 is ~45 pts **above** the major swept low — the LONG is taken **late**, well after the
  reversal, not at the sweep.
- **CHoCH review:** `CONFIRMED but WEAK` — a CHoCH-up prints near the anchor, but inside a **cluster of
  repeated CHoCH up/down labels in a 4070–4085 chop** → a minor, low-conviction structure break, not a
  decisive one.
- **OB review:** `PRESENT but BREACHED/WEAK` — the machine "fresh" bullish OB (4076.28–4076.89) is visible
  but sits **inside congestion**, and the fade drove price to ~4062 (MAE −18.57), i.e. **through and below
  the OB zone → the OB was breached and failed as support.** Not a clean, respected OB.
- **FVG / BPR review:** `PRESENT (low specificity)` — FVG and BPR boxes are drawn around the anchor
  (~4050–4090), but many/overlapping, reducing specificity.
- **displacement review:** `MODERATE` — the strong displacement was the earlier 4030→4090 rally; the
  **anchor CHoCH move itself was only moderate**, not a violent impulse. Consistent with machine ~2.79–4.18×.
- **HTF / session review:** **HTF does NOT support the LONG** — the valid 1h shows a **multi-day downtrend
  into Jul 9** (~4200 Jul 3 → ~4090–4120 Jul 9); the LONG is counter-HTF. Session ASIA; tz **UTC+1
  confirmed** but corpus TZ unresolved → `SESSION_UNCONFIRMED`.
- **contradiction review:** the chop around the anchor shows **repeated opposite CHoCHs** — a mild
  contradictory/indecisive backdrop, consistent with a weak setup.
- **Telegram/Discord context:** `NOT_CHECKED`.

### Decision

- **final_review_label:** **`WATCH`** — **reverted down** from the machine's provisional
  `SHADOW_CANDIDATE_LOW`. The corrected charts show a **structurally-present but weak, counter-HTF setup that
  failed**: sweep real but entered late, CHoCH minor-in-chop, OB breached, displacement only moderate, HTF
  against, outcome UNFAVOURABLE. Structure exists (so not a hard `REJECT` and more than pure `CONTEXT_ONLY`
  noise), but it is **below a shadow candidate**. **NOT trade-ready, NOT demo-ready, NOT permission to trade.**
- **review_status:** **`REVIEWED`** — all four screenshots valid and on the correct Jul 8→9 session; anchor
  structure and HTF assessed; review **closed.** (Grade, Telegram/Discord, larger sample remain standing
  non-blocking evidence.)

### Notes

- **reviewer_notes:** The corrected 1m confirms the date (midnight "Thu 09 Jul '26 00:04") and price (~4080)
  beyond doubt; the 3m gives the structure (swept low ~4030 → rally → chop 4070–4085 at the anchor). The
  setup is a late, counter-HTF long into congestion with a weak/breached OB; it briefly popped (+8.87 by
  15m) then faded through the OB to −18.57 MAE, closing −5.38 at 120m. Price did rise later on Jul 9
  daytime (beyond the 120m window), but the tracked outcome window is the fade.
- **missing_evidence (standing, non-blocking):** grade (ungraded); Telegram/Discord confirmation; larger
  sample (n=1).
- **disqualifiers:** none hard, but HTF-against + breached OB + unfavourable outcome are the strong
  negatives that drove the revert to `WATCH`.

---

## Reminder (decision rules)

`WATCH` is **observation-only** — not permission to trade, below even a shadow candidate. Demo discussion
stays blocked (evidence threshold **3/30 — NOT MET**). All outputs candidate-only; all execution flags false.
