# Preview URLs Disabled — Record

**Gate C-ENDPOINT-HYGIENE. 2026-07-07.**

## Change

| Field | Value |
|---|---|
| Setting | `preview_urls = false` (in `cloud_worker_dark/wrangler.toml`, line 14) |
| Effect | Per-version Preview URLs are **no longer generated** for this Worker |
| Worker | `farouk-tv-webhook-logger-v1` |
| Version after change | `c6d17920-16bc-433c-a272-fddb7228751e` |
| Main endpoint | `https://farouk-tv-webhook-logger-v1.taylormartyn70.workers.dev` (unchanged, live) |
| Logic change | **None** (config only) |

## Evidence it took effect

- The Gate C-ENDPOINT deploy had printed: *"…Preview URLs will be enabled for this deployment by
  default… disable by explicitly setting 'preview_urls = false'."*
- After adding `preview_urls = false` and redeploying, that warning **no longer appears**, and the
  deploy prints only the single main workers.dev trigger URL.

## Why this matters

- Preview URLs are additional per-version endpoints (e.g. `<version-alias>-farouk-tv-webhook-logger-v1
  .<subdomain>.workers.dev`). Disabling them **reduces the reachable surface** to just the one main
  URL. (Even preview URLs required the same secret path and are logging-only, so this is
  defence-in-depth, not a fix for an exploit.)

## Surface now

- **One** reachable endpoint: the main workers.dev URL.
- Auth: PATH_ONLY (long random secret path; only in the gitignored local file).
- Behaviour: POST to secret path → capture; everything else → 404/405; disabled/unset → 503.
