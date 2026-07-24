# FP-INDICATOR-006 — ALERT & TIMING FINDINGS

## What the session shows
- Chat asked twice: "how to use the alarms of the indicator, do you use them?" (~25:05 / 33:12).
- Farouk (~23:20): "how do you use the alarm indicator? **You can use them, yes, for sure.** When they break
  Asia high, then you get alarm. Okay, they broke Asia high." → confirms the indicator **emits alarms on events**
  (e.g. Asia-high break) and that he uses them.

## What it does NOT resolve (still UNKNOWN)
- **Bar-close vs intrabar timing** of the alarms — not stated.
- **Repaint / post-close mutation** — not addressed.
- **Alert message content / payload** — not shown (no alert dialog opened in this session).
- **Duplicate-alert behaviour** — not addressed.
- **Once-per-bar-close vs script-controlled** — not discussed.

## Conclusion
This video **corroborates that alarms exist and fire on named events**, consistent with the FP-INDICATOR-005
alert-interface evidence (Sweep/CHoCH/Asia-Trap/A+++/… conditions). It provides **no** new evidence on timing,
repaint, payload or duplicates. **All alert-integration blockers remain open** and still require the controlled
forward test **FP-LIVE-OBSERVATION-001**. A TradingView alarm remains an **untrusted observation**, never a
trade signal. Verdict unchanged: **NOT_INTEGRATION_READY.**
