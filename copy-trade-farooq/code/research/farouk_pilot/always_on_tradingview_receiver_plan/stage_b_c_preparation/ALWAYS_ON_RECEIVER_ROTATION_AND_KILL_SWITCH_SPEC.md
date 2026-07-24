# Always-On Receiver — Rotation & Kill-Switch Spec

**Mode: PREPARATION / DESIGN ONLY.** How to stop capture instantly and how to rotate the secret path.
No deployment exists yet; this specifies behaviour for the future Worker.

## Kill switch (defence in depth — any ONE stops capture)

1. **Soft flag:** set `TV_WEBHOOK_ENABLED = "0"` (Worker secret/var) → the Worker returns **503** to
   every request and logs that it was hit, but accepts nothing. Fastest, reversible in seconds.
2. **Delete/disable the Worker:** the endpoint stops existing → all requests fail at the edge.
3. **Rotate the secret path:** set a new `TV_WEBHOOK_SECRET_PATH` → the old URL now **404s**.
4. **Revoke the R2 binding / bucket:** the Worker can no longer write → fails closed (it should return
   5xx rather than accept-without-store; see below).

**Ordering for an emergency:** flip `TV_WEBHOOK_ENABLED=0` first (instant, reversible), then decide
whether to rotate the path or delete the Worker.

## Fail-closed on storage error

- If the R2 write fails, the Worker must **not** return 200. It returns a 5xx so TradingView records a
  failed webhook status (visible), rather than silently dropping. No accept-without-store.

## Secret-path rotation (planned + on-leak)

**Planned rotation** (hygiene, periodic):
1. Generate a new long random path (CSPRNG).
2. Set `TV_WEBHOOK_SECRET_PATH` to the new value in the Worker secret store.
3. Update the webhook URL on the (few) mirrored TradingView alerts to the new path.
4. The old path now 404s. Done — no code change, just a URL swap.

**On suspected leak** (URL in a screenshot, shared alert export, etc.):
1. **Rotate immediately** (steps above); old path 404s at once.
2. **Assess blast radius — bounded by design:** the endpoint is logging-only. A leaker can at most
   POST junk that lands as `ACCEPTED` noise (dedupe + `parse_status` flag it). **No execution, no
   broker/QST reach, no credential exposure, no data exfiltration** is possible through it.
3. **Review the audit log/metrics** for unexpected POSTs during the exposure window; annotate them in
   the store (append-only note, never delete the raw).
4. Body cap + rate limit bound any flooding.

## Audit trail

- Accepted, DUPLICATE, and rejected (404/405/413/503) requests each leave a record or metric so the
  endpoint's exposure and any probing are observable. Rejections carry no body/secret.

## What rotation does NOT require

- No broker/QST/execution involvement (none exists here).
- No change to Farouk production alerts unless/until they are mirrored (a later, gated stage) — and
  even then, rotation only swaps the webhook URL, nothing else.

## Reversibility summary

Every control is reversible: re-enable the flag, redeploy the Worker, restore the old path (if not yet
retired), or re-bind R2. The append-only evidence is always preserved.
