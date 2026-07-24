# Always-On Receiver — Security Model (§4)

**DESIGN ONLY.** Security controls for an internet-reachable, 24/7 logging-only endpoint.

## Authentication

- **Long random secret path** is the primary (and only required) auth — proven against real
  TradingView in Stage 2 (TradingView sends no custom header). Use ≥ 32 bytes of URL-safe randomness
  (e.g. `secrets.token_urlsafe(32+)`), e.g. `/tv/<48+ chars>`.
- **Any other path → 404.** **Any non-POST → 405.** Both are logged/metered as probes.
- Guessing a sufficiently long random path is computationally infeasible; that is the security basis.

## What must never appear anywhere

- **No secret in the query string** (it lands in provider logs/referrers) — secret is the path segment.
- **No credentials in the alert body.**
- **No broker/account credentials anywhere** — the receiver holds none by design.
- **No account IDs, no lot/risk sizing** in the payload (see hard vetoes).

## Transport & limits

- **HTTPS only** (provider TLS).
- **POST only**, exact secret path only.
- **Body size cap** (e.g. 64 KB → 413).
- **Rate limiting** where the platform offers it (per-IP / per-path burst caps); excess logged +
  dropped, never queued downstream.

## Storage integrity

- **Append-only logs** — inserts only; keyed on `event_id`; no update/delete path.
- **Least-privilege storage credential** — append to its own store only; no other cloud permission.
- **Audit trail** — accepted + rejected requests leave a record/metric (probes, auth-path misses,
  oversize, disabled-mode hits) so the endpoint's exposure is observable.

## Kill switch (defence in depth)

1. **`ENABLED=false` flag** → function returns 503 (still logs it was hit).
2. **Delete/disable the function** → endpoint gone entirely.
3. **Rotate the secret path** → old URL 404s immediately.
4. **Revoke the storage credential** → capture stops writing (fails closed).

Any one halts capture; together they cover config-, deploy-, URL-, and storage-level stops.

## Secret / key rotation

- **Planned rotation:** treat the secret path as a rotating credential. Rotation = generate a new
  secret path, update the (few) mirrored TradingView alerts' webhook URLs, retire the old path (it
  then 404s). Because the secret lives only in the path + the alert configs, rotation is a
  URL-swap, not a code change.
- **If the URL leaks** (e.g. a screenshot, a shared alert export):
  1. **Immediately rotate** the secret path (new URL) and retire the old one → old URL 404s.
  2. The exposure risk is limited anyway — the endpoint is **logging-only**: a leaker can at most
     POST junk that gets stored as `ACCEPTED` noise (dedupe + parse_status flag it). **No execution,
     no broker, no data exfiltration** is possible through it.
  3. Review the audit log for unexpected POSTs during the exposure window; annotate them in-store.
  4. Body cap + rate limit bound any flooding.
- **No standing long-lived secrets beyond the path** — there is no API key/broker token in this lane
  to leak.

## Threat model summary

- **Worst case if fully compromised (URL known):** an attacker can write junk log entries to an
  append-only store. That is the *entire* blast radius — because the receiver cannot trade, cannot
  reach a broker/QST, holds no credentials, and has no execution path. Rotate the path and move on.
- This bounded blast radius is the reason a logging-only always-on endpoint is acceptable to run 24/7,
  where an execution-capable one never would be.
