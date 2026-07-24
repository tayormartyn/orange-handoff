# H1 — Webhook Secret Rotation Incident

**Date:** 2026-07-09 10:58 local (Italy). **Type:** exposed-secret rotation (capture-only).

## What happened

The **full workers.dev webhook URL, including its secret path, was pasted into chat** during Gate H1
arming. Treated as **exposed** → rotated per the incident checklist.

## Blast radius (assessed)

**Bounded / low.** The endpoint is **logging-only**: the worst an attacker with the URL could do is POST
junk that lands as noise in R2. **No** execution, broker/QST reach, object read/list, or credential
exfiltration is possible through it. No evidence of misuse; rotation is precautionary + hygiene.

## Actions taken

1. Generated a **fresh random secret path** (CSPRNG; never printed).
2. **Rotated** the Worker secret: `wrangler secret put TV_WEBHOOK_SECRET_PATH` (value via stdin, not
   shown) → new Worker version live. **No code change** (Worker stays pure logging-only).
3. Updated all gitignored local files to the new URL in **copy-proof** format (bare URL between markers,
   no `webhook_url:` label): `LOCAL_SECRET_webhook_path.txt`, `LOCAL_ONLY_GATE_F_WEBHOOK_URL.txt`,
   `LOCAL_ONLY_GATE_E_WEBHOOK_URL.txt`.
4. **Old path retired:** old fingerprint `e1c56bbe1346` → new fingerprint `a569a5ad6277`. The old
   exposed path `/tv/<REDACTED_OLD>` is now a non-current path → **404** (verified by the same reject
   behavior as a generic wrong path; the old secret was not re-sent/printed).

## Verification

- POST wrong path → **404**; GET → **405**; Worker source **pure logging-only** (no temp branch).
- New/old fingerprints differ → rotation effective.

## Follow-ups

- **Do not paste secrets/URLs into chat.** Copy the bare line from the local Notepad file straight into
  TradingView.
- Reports/chat show only **redacted** paths + **fingerprints** — never the secret value or full URL.
- Martyn must update the H1 duplicate's webhook to the new URL (see results doc).

## Safety confirmations

No broker/cTrader/QST; no permit/lease/order; gates `PAPER/PREVIEW/False/False`; risk + 1.0% cap
unchanged; Telegram listener PID 40416 untouched; `NOT_INTEGRATION_READY` unchanged.

---

## UPDATE — SECOND exposure + rotation (2026-07-09)

The **rotated (2nd) URL was ALSO pasted into chat** immediately after the first rotation. Rotated
**again** to a 3rd secret.

- Retired fingerprints: `e1c56bbe1346` (1st), `a569a5ad6277` (2nd, exposed). Current: **`835a236c0bd1`** (3rd).
- Both prior exposed paths now **404**. POST wrong path → 404; GET → 405; Worker still pure logging-only.
- Local files updated to the new URL, with a stronger header: **"PASTE ONLY INTO TRADINGVIEW'S WEBHOOK
  URL FIELD — NEVER INTO CHAT."**

### Root cause = workflow, not the Worker

The repeated exposure is a **paste-destination error** (URL going into the chat instead of the
TradingView Webhook URL field). **Fix is behavioral:** copy the bare line from the local file and paste
it **into TradingView only**; **never send the URL to Claude** (Claude already has it). If it is pasted
into chat again, another rotation is required — so the loop only ends when the URL is pasted solely into
TradingView.
