# FP-LIVE-OBSERVATION-001 — DUPLICATE / CLUSTER ANALYSIS (first set)

Question (item 8): for same-timestamp messages, are they **duplicates**, **separate primitives**, or **composite
qualification** messages?

## 06:33:00 cluster (4 log lines)
| Message | Mechanism | Classification |
|---|---|---|
| "Sweep low" | named | PRIMITIVE (sweep low) |
| "Farouks Playbook: Sweep low (bullish) on XAUUSD" | Any alert() | **Cross-mechanism ECHO** of the same primitive |
| "Farouks Playbook: Bullish Engulfing on XAUUSD 3" | Any alert() | **Separate PRIMITIVE** |
| "Farouks Playbook: A LONG on XAUUSD 3" | Any alert() | **COMPOSITE qualification** (directional) |

→ **Not duplicates.** One sweep-low primitive is reported by two mechanisms (an echo, dedupable by
`(event, bar_close_time)`), plus a distinct Bullish-Engulfing primitive, plus a distinct "A LONG" composite.
3 semantic events, 4 lines.

## 06:57:00 cluster (2 log lines)
| Message | Mechanism | Classification |
|---|---|---|
| "Farouks Playbook: Bearish Engulfing on XAUUSD 3" | Any alert() | PRIMITIVE |
| "Farouks Playbook: A SHORT on XAUUSD 3" | Any alert() | COMPOSITE qualification (directional) |

→ 2 distinct events; no echo (no named condition matched); not duplicates.

## Cross-bar (06:24 vs 06:33 named Sweep low)
Two firings of the **same** named alert on **different** candles (06:24 and 06:33) — **distinct events**, not a
duplicate. The alert is condition-gated (did not fire on 06:27/06:30).

## Composite vs primitive — evidence
"A LONG" / "A SHORT" always appear **alongside** a same-direction primitive on the same bar (Bullish Engulfing +
Sweep-low → A LONG; Bearish Engulfing → A SHORT). They read as a **directional setup/qualification** emitted in
addition to the primitives. **The "A" is NOT proven to be an A+/A+++ grade** (the grade formula remains unknown);
recorded as a directional composite, semantics unresolved.

## Dedup rule implication (for the state machine ALERT_INTAKE — reference only)
A deduper keyed on `(event_type, direction, bar_close_time, symbol, tf)` collapses the named+Any Sweep-low echo
into one, keeps Bullish Engulfing and A LONG as separate records → matches EVENT_DEDUPLICATED design.


---
# CONTINUATION SET 002 — clustering
- 08:15 cluster = named Sweep low + Any-alert Sweep low = **cross-mechanism echo** (dedupable by
  event/direction/bar_close_time), same pattern as the 06:33 set-1 cluster.
- "BPR tapped" ×3 are **separate primitives on separate bars** (07:57/08:03/08:18), NOT same-bar duplicates.
- "A LONG" (07:45) = **composite**, standalone here (no same-bar primitive captured in the screenshot) — the
  composite can appear without a paired primitive in view.
- No same (event, direction, bar_close_time) duplicate observed in either set.


---
# CONTINUATION SET 003 — grade clusters
- 08:24 = named "A+ or better" + Any-alert "A+ SHORT" (complementary, same bar, dedupable).
- 08:27 = named "A+ or better" + Any-alert "A+ SHORT" + Any-alert "Bearish Engulfing" (grade+composite+primitive).
- 08:42 = named "CHoCH up" + Any-alert "CHoCH UP" (cross-mechanism echo).
- A+ fired on 2 bars (08:24, 08:27) = distinct events; no same (event,direction,bar_close_time) duplicate.
