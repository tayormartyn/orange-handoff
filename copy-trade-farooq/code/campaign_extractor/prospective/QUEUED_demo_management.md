# QUEUED — campaign-management fixture (XAUUSD 4027.37) + demo-management behaviour

STATUS: **QUEUED / NOT IMPLEMENTED.** This is a backlog note for the separately-approved
demo-management + future-regression phase. Nothing here is wired, validated, scored, or
executed now. No code or schema change was made by recording this. The live PREVIEW listener
was not touched.

## Campaign framing
**First complete managed-position lifecycle documented end to end.**
NOT "live-captured end to end" — MIXED provenance. LIVE_CAPTURED is asserted ONLY where a
verified row exists (matching channel id + message id + raw-text row + posted ts +
listener-received ts + hash verification + automatic capture). A manually supplied screenshot
stays MANUAL_SCREENSHOT_FIXTURE even if its visible time is after the listener started —
visible time alone does not prove automatic capture. No missed screenshot was inserted into
the DB; no listener timestamp/latency was fabricated.

## Per-event provenance (checked read-only 2026-06-29)
| Campaign component | Provenance | Evidence |
|---|---|---|
| Entry / surviving leg @ 4027.37 | MANUAL_SCREENSHOT_FIXTURE / NOT_LIVE_CAPTURED | no DB row; image-only |
| "take 50% off" instruction | MANUAL_SCREENSHOT_FIXTURE / NOT_LIVE_CAPTURED | no matching DB row |
| Volume progression 1.0 -> 0.5 -> 0.25 | MANUAL_SCREENSHOT_FIXTURE / NOT_LIVE_CAPTURED | image-only snapshot values; not captured text rows |
| Provider "I'm out 75% (risk free)" | **LIVE_CAPTURED** | msg 45285, ch -1001902136163, posted 2026-06-29T13:21:18Z, recv 13:21:18.387941Z, hash d60777eb1257 verifies; photo + 60-char caption ("out 75%"). Entry/vol/cash inside the image stay IMAGE-ONLY -> NULL. |
| Closure "SL entry hit out of the trade" | **LIVE_CAPTURED** | msg 45287, ch -1001902136163, posted 2026-06-29T14:04:58Z, recv 14:04:58.705453Z, hash dd2b6d720940 verifies; text 79 chars. Adjacent live closure row msg 45286 (14:04:38Z, hash dc2dcce71cf2 verifies). |

All LIVE_CAPTURED rows preserved UNCHANGED; quotes NULL / BROKER_NOT_CONNECTED. The
MANUAL_SCREENSHOT_FIXTURE components are NOT inserted into prospective_evidence_v1.db.
Per-event provenance needs NO code/schema change: LIVE_CAPTURED events carry provenance in
their own DB rows; manual/unverified events are recorded in this fixture note.

### Text-supported vs image-only (anti-hallucination)
- TEXT-SUPPORTED (in caption): the "out 75%" wording.
- **IMAGE-ONLY (NOT in caption → NULL/unconfirmed):** entry 4027.37, volume 0.25, displayed
  price 4048.27, floating amount 522.50. The recorder does not OCR images; these remain NULL
  unless an image-derived value is separately, manually confirmed. They must NOT be treated
  as text-literal.

## Supplied safe interpretation (as provided, to be applied in the demo-mgmt phase)
- Same instrument / direction / entry price (4027.37); same surviving child leg/campaign,
  subject to normal same-leg fingerprint validation.
- Original volume 1.0; observed remaining 0.25; cumulative provider-confirmed reduction 75%;
  remaining_fraction = 0.25.
- Exact partial-close fill prices remain NULL. Exact execution timestamps NULL or strictly
  evidence-bounded (no fabricated listener receipt/latency).
- Displayed cash figures are floating snapshot values — never accumulated as separate wins.
- "trade is risk free" = PROVIDER_CLAIMED only; does NOT prove stop moved to entry; NO
  automatic MOVE_STOP_TO_ENTRY from "risk free" wording alone.

### Open ruling flagged for the demo-mgmt phase (do NOT decide now)
- remaining_fraction = 0.25 from "I'm out 75%": the allowlist phrase is "take 75% off" →0.25;
  "out 75%" is a MORPHOLOGY variant (cf. June 25 "hold 25%"→NULL). Whether "out 75%" converts
  to 0.25 (PROVIDER_CONFIRMED) or stays NULL is a queued ruling, not improvised here.

## Required FUTURE regression behaviour (queued tests — not implemented)
1. Keep all 4027.37 snapshots on ONE campaign/leg where the same-leg evidence threshold holds.
2. Repeated snapshots create NO additional trades or wins.
3. First 50% reduction = PROVIDER_CONFIRMED, 1.0 → 0.5.
4. Later cumulative 75% reduction = PROVIDER_CONFIRMED, original 1.0 → remaining 0.25.
5. Preserve remaining_fraction = 0.25.
6. Unknown partial-close fill prices stay NULL.
7. Exact execution times unknown unless defensible timestamp endpoints exist.
8. "risk free" = PROVIDER_CLAIMED, not BROKER_CONFIRMED.
9. Do NOT move a future Martyn broker stop based solely on "risk free".
10. No realised demo/account-level R without Martyn's own broker records.
11. Provider, shadow and Pepperstone-demo outcomes remain SEPARATE.
12. Historical +0.17R signal-level baseline remains UNCHANGED.

## Execution boundary (this fixture authorises NONE of the following now)
live candidate extraction; broker connection; trade-scope OAuth; order placement; partial
position closing; stop modification; scoring or R calculation.

## Future demo-management interpretation (DESIGN INTENT — queued, do NOT implement now)
"Cumulative 75% closed" → advisory target of 25% of Martyn's ORIGINAL broker volume
remaining, ONLY after confident campaign/position association and using Martyn's ACTUAL
broker volume. Advisory only; gated behind the separately-approved demo-management phase
and a live broker connection (Gate 2, not given).
