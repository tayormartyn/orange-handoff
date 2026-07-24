# QUEUED — Farouk "missed the long @ 4000" (MISSED_ENTRY) fixture

STATUS: QUEUED backlog note (documentation only). No code/schema/behaviour change; running
PREVIEW listener untouched; no broker/extraction/scoring/execution. Brick 5C remains IMAGE-ONLY
and is NOT live-wired (no media bytes downloaded).

## Provenance (checked read-only 2026-06-29) — all LIVE_CAPTURED
| Component | msg | Provenance | Notes |
|---|---|---|---|
| "I missed the long at 4000 … 200+ pips … shower … thumbs up" | 45290 | **LIVE_CAPTURED** | text; posted 14:32:44Z, recv 14:32:44.372Z, hash 834c98100b67 verifies; media=None |
| "The Queen took it" (follower) | 45291 | **LIVE_CAPTURED** | posted 14:35:18Z, recv 14:35:18.452Z, hash 4c41f5b76d5b verifies; media_reference media:MessageMediaPhoto:45291 (REFERENCE only — image bytes NOT preserved; 5C not live-wired) |
| "Trade Breakdown" + .mov | 45292 | **LIVE_CAPTURED** | text; posted 14:42:14Z, recv 14:42:14.415Z, hash 34ae10acc51b verifies; .mov is a link/reference in text, media=None |

Rows preserved UNCHANGED; quotes NULL/BROKER_NOT_CONNECTED. No manual insertion performed.

## Safe classification
- A prior trade plan may have existed; **provider_execution_status = MISSED_ENTRY**.
- Farouk did NOT open the position → **no provider campaign leg; no provider realised R**.
- "200+ pips" = **retrospective market-path claim only** (not a provider outcome).
- "The Queen took it" = **CONTEXT / UNVERIFIED_FOLLOWER_OUTCOME** (a follower; never provider performance).
- "Trade Breakdown" = **RETROSPECTIVE_ANALYSIS**.
- No new signal, trade, win or fill created.

## Regression requirements (queued — not implemented)
1. "I missed the long" prevents any inferred provider execution.
2. A favourable subsequent market move must NOT become a provider win.
3. A follower taking / described as taking the trade must NOT become provider performance.
4. Retrospective breakdown content must NOT retroactively create an entry.
5. An earlier plan may remain linked as historical context, but status stays
   **NOT_EXECUTED_BY_PROVIDER**.
6. No realised R without an actual supported entry AND exit.
7. Historical +0.17R baseline remains UNCHANGED.

## Media note
- The "Trade Breakdown" uses a **.mov video** (link/reference). **UNSUPPORTED_MEDIA_TYPE** —
  Brick 5C is IMAGE-ONLY. **No video bytes were preserved** (none claimed). The .mov reference
  (as it appears in the captured text) is the only record.
- The "Queen" photo (45291) is an image, but its bytes were NOT preserved either — Brick 5C
  media download is not live-wired; only the media REFERENCE marker exists.
- Do NOT add video download / OCR / transcription / interpretation inside Brick 5C.
- Video preservation = a SEPARATE future scope decision, only if such-evidence volume justifies
  it. Not queued for build now.

## Sender
Farouk (seascalperfarouk) — TRACKED sender. But this evidence is MISSED_ENTRY, so even though
the sender may mutate trade state in general, **here there is nothing to mutate**: no entry,
no leg, no R. The follower ("Queen") is CONTEXT_ONLY.
