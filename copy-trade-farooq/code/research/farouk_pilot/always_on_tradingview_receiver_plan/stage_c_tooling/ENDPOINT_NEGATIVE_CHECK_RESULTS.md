# Endpoint — Negative Check Results

**Gate C-ENDPOINT. 2026-07-07.** Safe negative checks against the live workers.dev endpoint.
**No valid POST was sent; no R2 object was created.**

Endpoint: `https://farouk-tv-webhook-logger-v1.taylormartyn70.workers.dev`

## Checks (all passed)

| # | Request | Expected | Result | R2 write? |
|---|---|---|---|---|
| 1 | `GET /` | 405 (non-POST rejected) | ✅ **405** | no |
| 2 | `GET /tv/some-wrong-path` | 405 (non-POST; method checked before path) | ✅ **405** | no |
| 3 | `POST /tv/DEFINITELY-WRONG-SECRET-0000` | 404 (wrong secret path) | ✅ **404** | no |
| 4 | `PUT /` | 405 (non-POST) | ✅ **405** | no |
| 5 | `POST /` (root, wrong path) | 404 (wrong path) | ✅ **404** | no |

## Why no R2 object was created

In the Worker's request handler, responses for these cases return **before** the R2 `put`:
- non-POST → 405 at the method gate (before the path check and before reading the body);
- wrong path → 404 at the path gate (before the body read and before `EVIDENCE.put`).

Only a **correct-secret-path POST with a valid body** reaches `EVIDENCE.put` (a 200 response). That did
not happen — the real secret path was never used (it is not present in the shell; only in the gitignored
local file). Therefore the R2 bucket `farouk-tv-webhook-evidence-v1` remains **empty by construction**.

## What was deliberately NOT done

- ❌ No POST to the real secret path (no valid POST).
- ❌ No R2 object uploaded.
- ❌ No TradingView traffic / config.

## Interpretation

The endpoint is **live and correctly rejecting** everything except a properly-authenticated POST — which
is exactly the PATH_ONLY, logging-only behaviour proven locally by the Stage B oracle (10/10). The
endpoint is ready for a **future, separately-authorised** Gate D manual POST.
