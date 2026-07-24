# Brick 5C + two-gate model + BTC/wazwithazed + Discord (OFFLINE; nothing live activated)

STATUS: Brick 5C built and tested OFFLINE only. Live media downloading NOT activated. Running
PREVIEW listener and live allowlist NOT modified. No broker/OAuth/vision/scoring/execution.

## Investigation (read-only, required before any allowlist expansion)
- **Configured live channel allowlist:** a single channel id **`-1001902136163`** (the Whale
  Room supergroup). Safe identifier; no expansion performed.
- **quant-flow within the allowlist?** The configured chat is a multi-sender supergroup: the
  live recorder has already captured **`seascalperfarouk` AND `kyledoops`** (Kyle Dukes) — so
  capture is **channel-level and pulls all senders/topics in that supergroup**. quant-flow
  (wazwithazed's topic) is therefore likely within the same chat_id; I did NOT add or change
  anything. No wazwithazed row has appeared yet in the captured window.
- **Was the supplied BTC post auto-captured or manual?** **MANUAL.** No `wazwithazed`/quant-flow
  row exists in prospective_evidence_v1.db → the BTC chart post was **manually supplied** →
  provenance **MANUAL_TELEGRAM_SCREENSHOT_FIXTURE**, automatic_capture = FALSE. Not inserted
  into the DB; no listener timestamp/latency fabricated.
- **Sender-level filtering in the live capture path?** **NO.** Capture filters by CHANNEL only
  (`events.NewMessage(chats=...)` + chat_id allowlist). There is no `from_users`/sender filter
  at capture. (`--sender` exists only in the offline history/archive tooling, not live capture.)
  Trade-state mutation is sender-gated to Farouk DOWNSTREAM (sender_gate / validator).

## Two SEPARATE permission gates (`prospective/gates.py`)
1. **EVIDENCE CAPTURE GATE** — `capture_allowed(channel_id, allowlist)`: may raw text/media be
   PRESERVED. Channel-level.
2. **TRADE-STATE MUTATION GATE** — `mutation_allowed(sender_handle)`: may this sender CREATE/
   ALTER tracked trade plans/campaigns/legs/outcomes. Farouk only (or a sender Martyn explicitly
   approves as tracked).
**Passing capture NEVER implies passing mutation.** kyledoops/wazwithazed messages may be
preserved as evidence while remaining **CONTEXT_ONLY** — they can never mutate trade state.

## BTC / wazwithazed classification (CONTEXT_ONLY)
- TRADE_PLAN_POSTED; asset = BTC; direction = LONG; execution_status = NOT_ENTERED.
- entry/stop = image-supported CANDIDATES only, not accepted facts; 10/20/30/40% meaning = UNKNOWN.
- no campaign leg; no order; no scoring.
- sender_status(wazwithazed) = **CONTEXT_ONLY** until Martyn explicitly approves the trader as
  tracked. No message from this sender may create/mutate a campaign, plan, leg or outcome.

## Brick 5C — immutable image preservation (`prospective/media_cache.py`)
Current media capability (inspected): the recorder stores only a media REFERENCE marker
(`media:MessageMediaPhoto:<id>`) — no bytes, no content hash. Brick 5C ADDS byte preservation:
- raw text preserved FIRST (recorder); media handled separately so a media failure never rolls
  back raw text;
- image bytes (approved OFFLINE fixtures) → SHA-256 over EXACT bytes → stored content-addressed
  in a SEPARATE immutable cache (`prospective/media_cache/`, index `media_index_v1.db`, append-
  only); linked to channel/message/revision/evidence_id; album/multi-image supported;
- image types only; file-size limit (default 10 MB); path-traversal-proof (on-disk name is the
  content hash, never a supplied name); named statuses (MEDIA_CACHED / REJECTED_NOT_IMAGE /
  REJECTED_TOO_LARGE / REJECTED_PATH / EMPTY); no raw bytes or captions in logs;
- NO OCR / vision / chart interpretation / scoring / broker / execution.
Tested offline (13 tests) with synthetic image bytes. Canonical empty cache created (0 rows).

### Activation (NOT done — separate approval required)
Live image downloading is OFF. To go live it would require a **controlled listener restart**
(wire a download step that, after raw-text capture, fetches bytes via the existing session and
calls `MediaCache.preserve(...)`), plus an **allowlist review** (the supergroup already captures
multiple senders/topics — decide capture scope vs sender CONTEXT_ONLY tagging). Until then,
preserved manual screenshots keep MANUAL_TELEGRAM_SCREENSHOT_FIXTURE provenance.

## Brick 5D — automated vision/image-number extraction: NOT APPROVED
Not built, not prototyped, no dependencies added. Reason: vision extraction would create a new
high-risk hallucination surface (mis-read chart prices/stops/targets/percentages). Preserved
images are examined MANUALLY for now; any manually confirmed fact retains human-reviewed
provenance. Reconsider 5D only after: volume exceeds manual review; a separately approved
anti-hallucination design; independent validation beyond one vision reading; human confirmation
before any image-derived field affects trade state; permanent regression fixtures.

## Discord
Any Discord message/screenshot manually forwarded by Martyn must retain: source_provenance =
**MANUAL_DISCORD_FORWARD**; automatic_capture = FALSE; manual_received_at = actual receipt time;
original Discord timestamp only where visibly supported. Never masquerades as auto-captured.
(No automatic Discord capture exists.)
