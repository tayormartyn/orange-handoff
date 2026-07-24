# Daily Monitoring Report Generator — Spec v0.1

**DESIGN / SPEC ONLY — do NOT build or schedule yet.** A future **read-only, offline** script that
produces the daily report (see `DAILY_MONITORING_REPORT_v0_SAMPLE.md`) from R2 evidence + local safety
checks. **No execution surface; observation only.**

## Purpose

Each morning, summarise the prior 24 h of TradingView captures + lane/safety status into one markdown
file Martyn can skim.

## Inputs (read-only)

1. **R2 objects** in `farouk-tv-webhook-evidence-v1` under `events/YYYY/MM/DD/…` for the target day(s).
   - **Access method (choose one, both read-only):**
     - **R2 read-only S3 token** (preferred for a scheduled script) — an R2 API token scoped
       read-only to this one bucket; list + get via an S3 client. *(Creating that token is a separate,
       approved step.)*
     - **Temporary secret-gated list branch** (interactive only) — the Worker's read-only `?list`
       branch, added then reverted. Not suitable for an unattended schedule (leaves a read surface).
2. **Local safety state:** `config.py` (`MODE`, `LISTENER_MODE`, `EXECUTION_ENABLED`),
   `ctrader_config.py` (`CTRADER_EXECUTION_ENABLED`); Telegram listener process (PID/name); Worker
   version + negative-check spot results.

## Processing

1. **List** object keys for the day (prefix `events/YYYY/MM/DD/`).
2. **Fetch** each object (`--remote` if via wrangler; S3 get otherwise); parse the JSON record.
3. **Classify** each `raw_payload` per `RAW_TEXT_NORMALISATION_RULES_v0_1.md`
   (candidate `event_family` + `direction`; raw is source of truth; **no execution interpretation**).
4. **Aggregate:** counts by family (A LONG/SHORT, CHoCH up/down, Sweep high/low, Engulfing bull/bear,
   BPR tapped/formed, A+/A+++/A+ or better, unknown); direction splits; hourly frequency.
5. **Dedup (report-time only):** on `(event_time, event_family, direction)` — never discard raw.
6. **Most-recent-20** chronological rows.
7. **Noise flag:** mark families over a volume threshold (e.g. >20% of the day) as context/noise.
8. **Watchlist:** list the low-volume high-signal families and their counts.

## Output

- `DAILY_MONITORING_REPORT_<YYYY-MM-DD>.md` with the sections shown in the v0 sample:
  window, total, counts-by-type, grouped, recent-20, noisy warning, low-volume watchlist, H1/H2 status,
  listener status, Worker status, gates status, `NOT_INTEGRATION_READY` status.
- Also update/append a one-line index in `MONITORING_RESUME_STATUS.md` (optional).

## Hard constraints (must be enforced in code)

- **Read-only:** no writes to R2, no alert changes, no Worker deploy (unless the interactive temp-branch
  path is used, which must revert immediately).
- **No execution meaning:** the report never emits an actionable/order/broker/route/lot/account/risk
  field, and never a permit/lease/order.
- **Secret hygiene:** never print the webhook URL / secret path; redact any path to `/tv/<redacted>`;
  the R2/S3 token (if used) lives in a gitignored file, never committed/printed.
- **Import firewall:** the script imports no broker/cTrader/QST/execution/permit module.
- **UTC:** all times UTC; provider times stored verbatim, reconciled to UTC for comparison only.

## Scheduling (LATER — not now)

- Could run via the existing scheduling mechanism (cron/routine) once the script exists and is reviewed.
- **Not scheduled now.** This spec only describes it. Scheduling is a separate, explicitly-approved step.

## Open decisions (for Martyn, later)

1. Access method: R2 read-only S3 token (best for unattended) vs temp branch (interactive only).
2. Retention/window: 24 h vs multi-day rollup.
3. Where to store the daily files (a `daily_reports/` folder under the plan dir).

## Status

Spec v0.1 — **not implemented, not scheduled.** The v0 sample was produced by hand from existing Gate G
captures to validate the format.
