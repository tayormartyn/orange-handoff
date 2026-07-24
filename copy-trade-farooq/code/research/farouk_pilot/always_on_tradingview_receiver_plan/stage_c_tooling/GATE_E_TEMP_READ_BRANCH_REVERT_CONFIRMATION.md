# Gate E — Temporary Read Branch: Revert Confirmation (retry)

**2026-07-08.** Temp read branch **removed**; Worker back to **pure logging-only**.

| Step | Detail |
|---|---|
| Source | TEMP list branch removed (no `TEMP`, no `EVIDENCE.list` in `src/index.js`) |
| Redeploy | version **`87b34d69-c070-42d4-b2d4-ab00a220486c`** (pure logging-only) |
| `GET /tv/<secret>?list=events/` | **405** — list branch GONE |
| `POST /tv/<wrong-path>` | **404** |
| `GET /` | **405** |
| R2 objects | unchanged (Gate D intact; nothing deleted/modified) |
| R2/S3 credentials | none created |

Note: an earlier revert redeploy was interrupted, leaving version `ed8d8ff2…` (with the branch) briefly
deployed; this redeploy (`87b34d69…`) removes it. **The Worker is confirmed back to pure logging-only.**
