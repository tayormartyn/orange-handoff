# Human Review Packet — HR-0001

**Observation-only. Reviewing EVIDENCE, not a trade.** No order/entry/size/broker anywhere.
`NOT_INTEGRATION_READY` unchanged.

## Candidate summary

| Field | Value |
|---|---|
| review_id | **HR-0001** |
| candidate_id | ALIGNED_CHOCH_TO_A-0000 |
| candidate_type | ALIGNED_CHOCH_TO_A |
| **anchor_time_utc** | **2026-07-09T04:12:01Z** |
| direction_hint | **LONG** (bias descriptor, not an order side) |
| symbol / timeframe | XAUUSD / 3m (Pepperstone) |
| current methodology score | **0.375** → `SHADOW_CANDIDATE_LOW` |
| priority | **1 — HIGH** |

### Event sequence (raw — source of truth)
1. `Farouks Playbook: CHoCH UP on XAUUSD 3`  (04:00:00Z)
2. `Farouks Playbook: A LONG on XAUUSD 3`     (04:12:01Z ← anchor)

Classified: `CHOCH_UP(LONG_HINT) → A_LONG(LONG)`.

### Outcome summary (descriptive price stats, USD/oz — NOT PnL)
Entry reference (close at/after anchor): **4063.96**

| Horizon | MFE | MAE | final close Δ |
|---|---|---|---|
| 15m | +0.15 | −6.76 | −4.85 |
| 30m | +0.63 | −6.76 | −4.96 |
| 60m | +12.07 | −7.54 | +8.13 |
| 120m | **+35.49** | −7.54 | **+25.56** |

Outcome label: **MIXED** — early adverse heat (~−6.8 in the first 30m), then followed through LONG to
+25.56 close / +35.49 peak by 120m.

### Known positives
- Structure + signal **aligned LONG** (CHoCH_UP → A_LONG), same instrument/timeframe, 12 min apart.
- **Bullish FVG proxy** present near the anchor (`NEEDS_HUMAN_REVIEW`).
- The **only favourable-ish outcome** of the three candidates (eventual LONG follow-through).

### Known negatives / cautions
- **No order-block proxy** found (no qualifying displacement before the anchor).
- **Displacement proxy just under threshold** (ratio 1.91× vs 2.0× ATR) — i.e. *not* an obvious impulse.
- **HTF bias proxy is BEARISH** (15m), i.e. **opposes** the LONG hint (1h insufficient data).
- **Early adverse excursion ~−6.8** before it worked — a real position would have sat in drawdown.
- Local swing context: swing high 4064.59 / swing low 4054.16 around the window.

### Missing evidence (to resolve on review)
- Real displacement? (proxy sub-threshold) · Meaningful FVG or micro-noise? · Any credible OB? ·
  Session (timezone **UNCONFIRMED**) · HTF read (proxy says bearish) · Telegram/Discord confirmation
  (not checked) · Grade (ungraded).

---

## Screenshots to capture (save locally; do NOT paste large images into chat)

Anchor = **2026-07-09 04:12Z**. Capture window: **at least 60 min before → at least 120 min after** the
anchor, i.e. roughly **03:10Z → 06:15Z** (wider is fine).

| # | Chart | Timeframe | Window | Save as |
|---|---|---|---|---|
| 1 | XAUUSD · Pepperstone | **1m** | 03:10Z–06:15Z (≥60m before, ≥120m after) | `HR-0001_1m.png` |
| 2 | XAUUSD · Pepperstone | **3m** | 03:00Z–06:30Z | `HR-0001_3m.png` |
| 3 | XAUUSD · Pepperstone | **15m** | ~a few hours around 04:12Z | `HR-0001_15m.png` |
| 4 | XAUUSD · Pepperstone | **1h** (if available) | ~1–2 days around 04:12Z | `HR-0001_1h.png` |

On each image, mark: the **anchor candle (04:12Z)**, the **CHoCH UP** point (~04:00Z), the **bullish FVG**
proxy zone, and any **displacement** / **order-block** you see (or note their absence).

### Capture rules
- **Price scale visible** and **time axis / clock visible**.
- **UTC preferred** — if your chart clock isn't UTC, write down which timezone it is (do **not** guess an
  offset; the timezone is currently unresolved).
- **No account/broker/personal info:** crop out balance, positions, P&L, order tickets, account numbers,
  login. Chart + scales only.
- Save all four in: `stage_c_tooling/human_review_screenshots/HR-0001/`

---

## Review checklist (answer while looking at the charts)

1. **Real structure shift?** Was the CHoCH UP a genuine break of structure, or noise?
2. **Displacement obvious?** Was there a clear impulsive move, or only ordinary volatility? (proxy was
   sub-threshold at 1.91×.)
3. **Meaningful FVG?** Is the bullish FVG a real imbalance, or tiny/noisy?
4. **Credible order block?** Is there a real OB (the detector found none) — fresh or already spent?
5. **Direction contradicted?** Does HTF / structure fight the LONG hint? (HTF proxy said bearish.)
6. **Just delayed noise?** Did price only work *after* sitting adverse — i.e. luck vs setup?
7. **Adverse excursion too large?** Was the ~−6.8 early heat beyond what the setup should tolerate?
8. **Looks like Farouk training or not?** Does this resemble a taught A-LONG-after-CHoCH setup, or a
   coincidental alert pairing?

---

## After capture

Fill `HUMAN_REVIEW_HR_0001_FORM.md`, apply `HUMAN_REVIEW_DECISION_RULES_v0_1.md`, set the review status.
Reviewing evidence only — **no trade, no order, no broker action.** Reaching any label (even
`METHODOLOGY_ALIGNED_SHADOW`) is still observation-only and does not lift `NOT_INTEGRATION_READY`.
