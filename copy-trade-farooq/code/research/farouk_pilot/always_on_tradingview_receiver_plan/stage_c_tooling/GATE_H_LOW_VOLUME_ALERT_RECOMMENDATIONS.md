# Gate H — Low-Volume Alert Recommendations (for H2/H3)

**Planning only — do NOT start H2/H3.** Based on the Gate G frequency analysis (74 events/11.6 h).
H1 is already testing the **APLUS (A+ / "A+ or better")** alert.

## Recommended next candidates (after H1 passes)

| Gate | Candidate dedicated alert | Expected volume | Evidence value | Why |
|---|---|---|---|---|
| **H2** | **CHoCH** (`LIVE001_CHOCH_UP_XAUUSD_3M` + `LIVE001_CHOCH_DOWN_XAUUSD_3M`) | **Low** (~5 / 12 h) | High | Structure shifts (change of character) — meaningful, infrequent, clean `event_type` |
| **H3** | **Sweep** (`LIVE001_SWEEP_HIGH_XAUUSD_3M` + `LIVE001_SWEEP_LOW_XAUUSD_3M`) | Moderate (~10 / 12 h) | Medium–High | Liquidity sweeps — the setup context that often precedes CHoCH/A+ |
| (later / optional) | **BPR formed** (if a dedicated alert exists) | Very low (0 seen) | High if it fires | A *formed* BPR is rarer/stronger than a *tapped* one |

- Each is **duplicate-first** (original never edited), **one at a time**, **disable-after-proof**.
- If CHoCH is two separate alerts (up/down), mirror them as two duplicates or pick the more relevant
  direction first — Martyn's choice.

## Do NOT mirror continuously (from Gate G noise)

- **ANY_ALERT composite** (floods — 74/night), **Engulfing**, **A LONG/SHORT**, **BPR tapped**. These are
  context-only; use one-shot at most.

## Volume guardrail for the first batch

- Keep the concurrent mirrored set small (**≤3**, per `GATE_H_SMALL_SET_CAPTURE_PLAN.md`), favour the
  low-volume high-signal alerts above, and disable each after its capture is proven unless ongoing
  capture is explicitly wanted.

**Not started. Awaiting H1 pass + explicit approval per gate.**
