# Endpoint Hygiene — Negative Checks

**Gate C-ENDPOINT-HYGIENE. 2026-07-07.** Post-redeploy negative checks. **No valid POST; real secret
path not used; no R2 write.**

Endpoint: `https://farouk-tv-webhook-logger-v1.taylormartyn70.workers.dev` (version `c6d17920…`)

## Checks (all passed)

| # | Request | Expected | Result | R2 write? |
|---|---|---|---|---|
| 1 | `GET /` | 405 | ✅ `405 {"ok":false,"error":"method_not_allowed","allow":"POST"}` | no |
| 2 | `POST /tv/WRONG-SECRET-hygiene-0000` | 404 | ✅ `404 {"ok":false,"error":"not_found"}` | no |
| 3 | `PUT /` | 405 | ✅ `405 method_not_allowed` | no |
| 4 | `GET /tv/some-wrong-path` | 405 | ✅ `405 method_not_allowed` | no |

## No accepted request reached R2

- Non-POST → 405 at the method gate (before path check / body read / R2 put).
- Wrong path → 404 at the path gate (before body read / R2 put).
- Only a correct-secret-path POST with a valid body reaches `EVIDENCE.put` (200). That did not happen.
- Bucket `farouk-tv-webhook-evidence-v1` confirmed present and **empty by construction** (0 objects).

## Confirmations

- Preview URLs disabled; **main endpoint still live and rejecting correctly**.
- Same PATH_ONLY logging-only behaviour as before the hygiene change (no logic change).
- No TradingView traffic/config; no valid POST; no R2 object.
