# Next Gate — D-MANUAL-POST Readiness

**Gate C-ENDPOINT is complete.** Describes **Gate D-MANUAL-POST**. **Gate D is NOT started and NOT
authorised. It is now UNBLOCKED (endpoint live).**

## Prerequisites

- [x] Stage B PASS.
- [x] Gate C-INSTALL / C-LOGIN / C-R2A / C-R2B / C-DEPLOY-DARK.
- [x] **Gate C-ENDPOINT — workers.dev endpoint live**
  (`https://farouk-tv-webhook-logger-v1.taylormartyn70.workers.dev`), negative checks pass.
- [x] **Gate C-ENDPOINT-HYGIENE — Preview URLs disabled** (`preview_urls=false`, version `c6d17920…`);
  main endpoint still live; negative checks re-passed; bucket still empty.
- [ ] Explicit **Gate D-MANUAL-POST** approval ← the only remaining prerequisite.

## What Gate D-MANUAL-POST would do (later, only if approved)

- Send **hand-crafted POSTs** to the endpoint (from us/Martyn — **not** TradingView):
  - **valid JSON** to the correct secret path → 200 ACCEPTED / PARSED → **one** append-only R2 object
    `events/YYYY/MM/DD/<event_id>.jsonl` (this is the **first intentional R2 write**);
  - re-send the same payload → a **second** ACCEPTED object (report-time dedupe: distinct count stays 1
    in a later read-only report; nothing discarded at ingest);
  - wrong path → 404 (no object); non-POST → 405; oversize → 413; `ENABLED=0` → 503.
- Then verify the stored object(s): raw byte-exact, UTC `received_at_utc`, `event_id`, `parse_status`,
  secret path redacted; and confirm report-time dedupe.

## Hard boundaries for Gate D

- Manual POSTs only. **No TradingView config, no Farouk-alert edit, no real webhook traffic** (that's
  Gate E).
- No broker/QST/execution/permit/lease/order; no gate change; no shadow engine; listener untouched.
- Gate D is the first gate that **intentionally writes R2 objects** (from manual test POSTs). To use the
  correct secret path, read it from the gitignored `cloud_worker_dark/LOCAL_SECRET_webhook_path.txt`
  (never printed to chat).

## Gate sequence

`… → C-DEPLOY-DARK ✅ → C-ENDPOINT ✅ (endpoint live) → D-MANUAL-POST (next — unblocked, not authorised)
→ E-TRADINGVIEW-TEST`.

## What Martyn approves next

- **Gate D-MANUAL-POST** — authorise hand-crafted test POSTs to the endpoint (valid + negative) and the
  first intentional R2 writes. Nothing is sent without that explicit approval.

**Until Gate D-MANUAL-POST is explicitly approved, nothing further happens.** `NOT_INTEGRATION_READY`
unchanged; capture-only.
