# FP-LIVE-OBSERVATION-001 — TIMING ANALYSIS (first set)

## Firing times (from the alert log)
06:24:00 · 06:33:00 · 06:57:00 — **every firing is on an exact 3-minute boundary** (each is divisible by 3).

## 3-minute candle boundary check
On a 3m chart the candle opening at 06:30 **closes at 06:33:00**. A firing stamped 06:33:00 therefore coincides
with the **bar close** of the 06:30 candle. Same for 06:24:00 (close of the 06:21 candle) and 06:57:00 (close of
the 06:54 candle). → **All events fired on 3-minute candle boundaries, consistent with bar-close firing.**

## Named vs Any alert() timing
- The named condition was configured **Once per bar close** and fired at 06:24:00 and 06:33:00 (bar closes).
- The **Any alert()** messages fired at **06:33:00 and 06:57:00 — the same boundaries** as the named mechanism.
  → In this session the **script's alert() calls also fire at bar close**, not intrabar (no off-boundary
  timestamps were observed).

## Not-every-bar (condition-gated)
Sweep low fired at 06:24 and 06:33 but **not** at 06:27 or 06:30 (the intervening bar closes). → The alert is
**condition-gated**, not a per-bar repeater — supporting acceptable-duplicate behaviour.

## Caveats
- These are **alert-engine log timestamps**, captured post-hoc. They show firing ON the boundary but do **not**
  prove the marker/zone was stable intrabar before the close (that needs a frame-at-firing capture).
- Sample is small (3 boundaries, 7 log lines, one session). Bar-close timing is **strongly indicated but not yet
  proven across many events**.
- Clock note: local machine ≈ UTC+1; the indicator's internal timezone field is Europe/Berlin (UTC+2 DST) — the
  session-drawing timezone and the alert-log clock are different reference frames; both recorded.


---
# CONTINUATION SET 002 — timing (video-confirmed)
- **Direct video proof of at-close firing:** in Recording 1 the named Sweep-low **toast appeared at 06:24:00
  UTC+1** (the 06:21-candle close), with the chart clock reading 06:24:00 at that instant.
- All 7 new log events fired on exact 3-minute boundaries: 07:45, 07:57, 08:03, 08:12, 08:15, 08:18.
- BPR tapped fired on 3 non-adjacent bars (07:57/08:03/08:18) → condition-gated, not a per-bar repeater.
- Chart clock = **UTC+1** (confirmed on video); indicator timezone field = Europe/Berlin (UTC+2 DST) — two
  distinct reference frames, both recorded.
- Caveat: still one trading session/day; cross-session repetition outstanding.


---
# CONTINUATION SET 003 — timing
- Firings 08:24 / 08:27 / 08:42 — all exact 3-minute boundaries (bar close). Consistent with prior sets + the
  set-2 video-confirmed 06:24:00 toast.
- Named and Any alert() share the same close (A+: 08:24/08:27; CHoCH up: 08:42). Still one trading day.
