# Human Review Form — HR-0001 (FILLED)

**Observation-only. Confirms EVIDENCE, not a trade.** `candidate_only=true`; execution / broker / qst /
order_intent / risk_sizing = **false**. `NOT_INTEGRATION_READY` unchanged.

- review_id: **HR-0001**
- candidate_id: ALIGNED_CHOCH_TO_A-0000
- anchor_time_utc: 2026-07-09T04:12:01Z
- direction_hint: LONG

---

- **reviewer:** assistant-assisted visual review (Claude) — **awaiting Martyn countersign**
- **review date (UTC):** 2026-07-09 (finalised after corrected screenshots)
- **screenshots captured (yes/no):** yes — 1m ✅ / 3m ✅ / **15m ✅ (true 15m, TF=15)** / **1h ✅ (correct, covers Jul 9, TF=60)**
- **chart timezone used:** **UTC+1** (observed). Underlying OHLC export is Unix-epoch = true UTC, so the
  04:12Z outcome match is correct.

### Per-factor verdicts

- **OB review:** `CONFIRMED_FRESH` — the indicator draws an order block at the Asia-Low sweep around the
  anchor; appears fresh at entry. _(Machine OB proxy found NONE — human review overturns: the crude
  displacement-gated proxy under-detected it.)_
- **FVG review:** `CONFIRMED` — indicator-drawn FVGs drive the post-anchor rally (not micro-noise).
- **displacement review:** `CONFIRMED` (moderate) — the reversal created FVGs; machine ratio 1.91× sat
  just under the 2.0× proxy threshold, so the proxy missed it.
- **structure review:** `CONFIRMED` — CHoCH UP at Asia Low with a sweep-reversal structure.
- **HTF / session review:** session **UTC+1 observed**. **HTF bias = BEARISH — OPPOSES the LONG
  (CONFIRMED).** The corrected 1h shows a multi-day **downtrend into the anchor** (~4200 on Jul 3 → ~4050
  on Jul 9); the true 15m confirms an Asia-Low sweep-reversal cluster. So the A LONG was **counter-trend**
  vs the 1h — matching the machine's bearish HTF proxy.
- **contradiction review:** `ABSENT` — no opposite-direction A cluster at the anchor.
- **Telegram/Discord context:** `NOT_CHECKED`.

### Decision

- **final_review_label:** **`SHADOW_CANDIDATE_LOW`** — **reverted** from the provisional MEDIUM. The
  corrected 1h confirms **HTF opposes the LONG (counter-trend)**; combined with the **MIXED** outcome,
  ungraded setup and n=1, the confirmed anchor structure is not enough to hold MEDIUM. **NOT trade-ready,
  NOT demo-ready, NOT permission to trade.**
- **review_status:** **`REVIEWED`** — all four valid screenshots now present (1m/3m/true-15m/Jul-9 1h);
  HTF question resolved. Review closed. (Telegram/Discord + larger sample remain standing missing evidence,
  not blockers.)

### Notes

- **reviewer_notes:** With chart tz = UTC+1, the CHoCH UP (04:00Z) and A LONG (04:12Z) coincide with an
  Asia-Low sweep + OB + BPR + FVG cluster; the −6.76 early heat = the sweep of Asia Low just before the
  reversal, then a grind up (+12 @60m, +25.56 @120m). This is a plausible Farouk POI/OB sweep-reversal —
  **but** the favourable follow-through was moderate/grindy, HTF is unconfirmed, and this is one instance.
- **missing_evidence (standing, non-blocking):** **grade** (ungraded); **Telegram/Discord** confirmation
  (not checked); **larger sample** (n=1). _(The 15m and Jul-9 1h are now supplied and validated.)_
- **disqualifiers:** none (HTF-opposes is a strong negative that caps the label, not a hard disqualifier).

---

## Reminder (decision rules)

`SHADOW_CANDIDATE_LOW` is **observation-only** — not permission to trade. The corrected 1h confirmed HTF
**opposes** the LONG (counter-trend), which — with the MIXED outcome — reverted the provisional MEDIUM to
LOW, exactly as the earlier note anticipated. Demo discussion stays blocked (evidence threshold **3/30 —
NOT MET**).
