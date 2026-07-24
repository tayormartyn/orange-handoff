# PHONE_ALERT_BATCH_001 — Limitations & Unresolved Items

Read-only processing. The following are recorded rather than guessed.

## Timezone

- **Alert-log CSV `Time` is UTC** — trailing `Z`, unambiguous. All 111 timestamps are treated as UTC.
- **Laptop chart clock = UTC+1** (per `SOURCE_MANIFEST.json`). Cross-check confirms it: the two A+
  SHORT firings at 07:24Z/07:27Z correspond to the checkpoint's "A+ observed at 08:24/08:27 local".
- **Indicator internal TZ field = `Europe/Berlin`** (UTC+2 in July DST) — visible in the landscape
  screenshot settings string. This is the indicator's own setting, not necessarily the chart axis.
- **Phone status-bar clock ≈ UTC (not resolved):** the 18:30 phone frame precedes the 18:33:01Z A+
  LONG, which is consistent with the phone clock being ~UTC. But the phone chart's own axis timezone
  was not independently confirmed. **Do not assume a single global offset** across laptop, phone, and
  indicator — three different references are in play (UTC+1 chart, Europe/Berlin indicator, phone).

## SWEEP_LOW dedicated vs composite mismatch

- `SWEEP_LOW` dedicated fired **7×**; the composite "Sweep low (bullish)" message appears **6×**.
- One sweep-low bar close has a dedicated firing without a matching composite line (or an extra
  dedicated retrigger). Not reconciled from the data alone — flagged, not guessed.

## Scope of evidence

- All alert evidence is a **single trading day (2026-07-06, 05:24Z–21:00Z)**. No multi-day sample.
- The alert log is **server-side firings only**. It does **not** establish trades, entries, fills,
  outcomes, or P&L — none inferred (per hard rules).
- Screenshots corroborate symbol/feed/timeframe, price, and panel structure fields (CHoCH / Asia
  break / OB levels). They do **not** show an A+/A+++ grade (the panel has no grade field), so grade
  is evidenced only by the CSV.

## Repaint / C4 (unchanged from checkpoint)

- No unobstructed single-candle form→close capture is present in this batch. Intrabar repaint at the
  firing instant remains **not fully verified** → C4 stays **PARTIAL**.

## C7 grade (unchanged)

- A+++ never fired; grade formula and grade stability (re-check at +1/+5 bars) are **untested**. C7
  remains **INSUFFICIENT**.

## Gallery-file timestamp

- `Screenshot_20260706_190323_Gallery.jpg` (filename 19:03) shows an 18:43 phone status bar — a
  Gallery re-save of the 18:43 frame, not a distinct 19:03 capture. Counted as evidence of the 18:43
  state, not a separate observation time.

## Provenance shortcut (disclosed)

- The 1.9 GB recording was matched to the manifest by **name + exact byte size**, not re-hashed, to
  avoid a 1.9 GB re-read. All other 40 pre-existing files were SHA256-verified against the manifest.

## Integration verdict

- Unchanged: **NOT_INTEGRATION_READY.** New A+ LONG, Sweep high and CHoCH down firings expand
  coverage, but A+++ absence, C4 (repaint), C7 (grade), the SWEEP_LOW mismatch, and single-day scope
  remain open.
