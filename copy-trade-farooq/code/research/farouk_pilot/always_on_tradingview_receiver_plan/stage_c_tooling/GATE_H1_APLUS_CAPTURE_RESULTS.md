# Gate H1 — APLUS Mirror Capture Results

**Status (2026-07-09 10:58 local): ARMED, pending re-URL after secret rotation, then one natural A+ trigger.**

## Context

- Candidate: real Farouk alert `LIVE001_APLUS_XAUUSD_3M` (lower-volume, ~4/day) — chosen after the
  Gate G ANY_ALERT volume lesson.
- Mirror (duplicate-first): `LIVE004_APLUS_MIRROR_GATE_H1`. Original **not touched**.
- R2 baseline: **73** objects (list-verified at Gate G close). A successful H1 capture → >73.

## Secret rotation (mid-arming incident)

- The full webhook URL (incl. secret path) was pasted into chat → **secret rotated** (new fingerprint
  `a569a5ad6277`; old `e1c56bbe1346` retired → old path 404s). See
  `H1_WEBHOOK_SECRET_ROTATION_INCIDENT.md`.
- **Consequence:** the H1 duplicate's webhook must be **updated to the new URL** before it can capture
  (the old URL now 404s).

## Manual steps for Martyn (update the DUPLICATE only)

1. Open **`LIVE004_APLUS_MIRROR_GATE_H1`** only. **Do not open/edit `LIVE001_APLUS_XAUUSD_3M`.**
2. **Replace the old Webhook URL** with the new bare URL line from the open Notepad file
   `LOCAL_ONLY_GATE_F_WEBHOOK_URL.txt` (copy the line between the markers only).
   - ✅ starts with `https://farouk-tv-webhook-logger-v1.taylormartyn70.workers.dev/tv/`
   - ❌ not the old trycloudflare URL.
3. Keep **Notify in app ON**, **Condition unchanged**, **Message as-is** (indicator `alert()` text).
4. **Save / re-arm** the duplicate; confirm the original `LIVE001_APLUS_XAUUSD_3M` remains present +
   unchanged.
5. Wait for one natural A+ trigger; tell Claude "fired".

## Verification (when it fires — later)

R2-as-source-of-truth: temp read-only list branch → count > 73 → fetch new object(s) → confirm raw
preserved, `received_at_utc` UTC, JSON/PARSED vs raw-text/INVALID_JSON, **A+ / "A+ or better" text**,
secret absent → revert to pure logging-only → delete the duplicate.

## Safety (this step)

Capture-only; original untouched; no broker/QST/execution; no permit/lease/order; gates
`PAPER/PREVIEW/False/False`; Telegram listener PID 40416 untouched; `NOT_INTEGRATION_READY` unchanged.
