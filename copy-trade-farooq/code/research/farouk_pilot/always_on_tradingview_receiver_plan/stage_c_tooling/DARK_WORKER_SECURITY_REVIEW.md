# Dark Worker — Security Review

**Gate C-DEPLOY-DARK. Review of `cloud_worker_dark/src/index.js` + `wrangler.toml`.**

## Isolation / no execution surface

| Control | Status |
|---|---|
| Imports | **None** — the Worker imports nothing (no broker/cTrader/QST/execution/permit/lease/order). |
| Outbound requests | **None** except the single R2 `EVIDENCE.put`. No `fetch()` to any host; no trading call. |
| Trade logic | **None** — no sizing, no decision that acts; parser writes metadata only. |
| Bindings | **Only** `EVIDENCE` (one R2 bucket) + two non-secret vars. No other cloud resource. |

## Auth

- **PATH_ONLY** — exact long random secret path required (constant-time-ish compare); wrong path → 404;
  non-POST → 405. Secret is 43 chars of CSPRNG (`randomBytes(32)` base64url).
- **Fail-closed** — if `TV_WEBHOOK_SECRET_PATH` is unset → 503 (`not_configured`); if
  `TV_WEBHOOK_ENABLED != "1"` → 503 (`disabled`). So the pre-secret window was safe (refused all).

## Secret handling

- Secret set via `wrangler secret put` (stdin) → stored as Worker `secret_text`, **not** in the repo.
- Value never printed to chat; only a fingerprint (`e1c56bbe1346`) + length (43) recorded.
- Local copy in **gitignored** `LOCAL_SECRET_webhook_path.txt` (marked DO NOT COMMIT / DO NOT PASTE).
- **The stored R2 record redacts the path** (`"/tv/<redacted>"`) → the secret never lands in evidence
  objects (prevents leaking it via a later export/share).

## Data handling

- **Raw-first**: `request.text()` stored byte-exact in `raw_payload`.
- **Append-only**: one object per accepted POST, key `events/YYYY/MM/DD/<event_id>.jsonl` on a **unique**
  `event_id` (`crypto.randomUUID()`) → `put` never overwrites a distinct object.
- **Report-time dedupe**: every accepted POST stored as `ACCEPTED`; `dedupe_key` computed but **never**
  used to discard/flag at ingest → lossless.
- **Safe headers only**: content-type/length/user-agent whitelist; no authorization/cookies stored.
- **Body cap**: 64 KB → 413.

## Limits / kill switch

- `TV_WEBHOOK_ENABLED=0` → 503; delete Worker → gone; rotate secret → old path 404s; delete bucket →
  storage gone.

## Residual notes

- **No public endpoint** currently (dark) → attack surface is effectively nil right now.
- Length-based early-out in the path compare leaks path *length* only (negligible; the secret is long
  random). Full timing-safe compare could be added if ever desired.
- When an endpoint is enabled later, the security basis is the secret path + logging-only + bounded
  blast radius (worst case = junk log entries; no execution, no broker reach, no credential exposure).

## Verdict

**PASS.** The Worker is logging-only with no execution surface, fail-closed auth, secret kept out of
the repo and out of stored evidence, append-only lossless storage, and a working kill switch.
