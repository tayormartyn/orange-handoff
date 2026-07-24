# Daily Monitoring Report — TEMPLATE

**Purpose:** a read-only daily snapshot of the observation lanes. Fill in each day (or per session).
**Observation only — no execution, no changes.** Copy this template to a dated file when used.

---

## Daily Capture-Lane Status — <YYYY-MM-DD>

**Prepared (UTC):** __________  **By:** __________

### 1. TradingView → cloud capture (Worker + R2)

- Worker: `farouk-tv-webhook-logger-v1` — mode: **LOGGING_ONLY** (confirm version: ______)
- Endpoint negative checks (spot): `GET /`→405 [ ] · `POST /tv/<wrong>`→404 [ ] · `GET ?list`→405 (branch absent) [ ]
- **R2 object count:** start-of-day ______ → end-of-day ______ (Δ = ______ new)
- **New raw events today:** ______
  - `parse_status`: PARSED ____ / INVALID_JSON (raw text) ____ / UNRESOLVED_PLACEHOLDER ____
  - unresolved `{{...}}` placeholders seen: ______ (list keys/fields)
  - notable `event_type` seen (observational): ______
- Any delivery failures / non-200 (from tail or TradingView webhook status): ______

### 2. Telegram PREVIEW listener

- Status: RUNNING / NOT RUNNING — **PID:** ______ (expected 40416 unless restarted)
- `prospective_evidence_v1.db` new rows today (if checked): ______
- Notes: ______

### 3. Mirrored alerts in play (duplicate-first)

- Active mirrors: ______ (names `*_GATE_G/H`)
- Originals confirmed untouched: YES / NO
- Any duplicate accidentally left running that should be disabled: ______

### 4. Safety gates (read-only confirmation)

- `MODE=PAPER` [ ] · `LISTENER_MODE=PREVIEW` [ ] · `EXECUTION_ENABLED=False` [ ] · `CTRADER_EXECUTION_ENABLED=False` [ ]
- Broker/cTrader/QST connection: **absent** [ ]
- Permits/leases/orders: **none** [ ]
- 1.0% campaign-wide risk cap: **unchanged** [ ]
- Shadow engine: not started [ ]

### 5. Secret hygiene

- Secret path exposed anywhere today? **NO** [ ] (redacted in logs/reports; only in gitignored files)
- Any URL/secret leak concern? ______ (if yes → see incident checklist, rotate)

### 6. Verdict

- **`NOT_INTEGRATION_READY`:** unchanged [ ] / changed → explain: ______
- Capture-lane health: OK / DEGRADED / INCIDENT (→ incident checklist)
- Next action for Martyn: ______

---
*This is measurement only. It never enables execution and never modifies alerts or gates.*
