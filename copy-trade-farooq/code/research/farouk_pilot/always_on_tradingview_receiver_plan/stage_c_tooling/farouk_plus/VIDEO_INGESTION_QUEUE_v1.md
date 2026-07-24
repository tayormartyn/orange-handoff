# Downloads video inventory + training ingestion queue v1 (INVENTORY-ONLY; Batch 1 pending approval)

**Mode: INVENTORY-ONLY — READ-ONLY. SINGLE-SESSION.** Date 2026-07-13 (~04:45Z). Raw inventory (53
files, full paths/hashes/durations): `downloads_video_inventory_20260713.json`. Live gates clean
(store max 45657; listener PID 30268; Cycle 006 open). **Nothing moved/renamed/altered; no
transcription started.** Gates `PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY` unchanged.

## 1. Headline counts
53 video files in Downloads (top level; no relevant subfolders found) → **17 UNRELATED** (personal
Ember/cinematic projects — not inspected further, not ingested) · **36 Farouk/Whale-Room-related** →
of those: **19 ALREADY_INGESTED originals or hash-identical duplicates** · **11 video-variants of
already-transcribed audio** (Zoom mp4 full ×2 dupes + 9 PART files + Z1 mp4 ×2 dupes) · **4
Exochart/Delta guest-series** (excluded by standing policy) · **2 already-reviewed via durable
transcripts** (Live Jul-3, Live Jul-5). **NEW unheard Farouk material: ZERO.** Rights: all
Farouk-related items are member-recorded/member-distributed WhaleRoom content under the standing
private-research register; 0 items need a new rights review.

## 2. Ingestion status (hash-verified against durable records)

| group | files | status |
|---|---|---|
| FP-B003-01..06 sources + 4 byte-identical copies | 10 | ALREADY_INGESTED / DUPLICATE (sha256 match to `_source_meta.json`s) |
| FP-LIVE-VIDEO-EXPLAINER-001 (f1200fed…) / -002 (f061b23c…) / -003 (e576af86…) / -004 ("10 min stream", dadb6e54…) / -005 (942dc4af…) | 5 | ALREADY_INGESTED (hash prefixes match durable reviews) |
| Live with Farouk **Friday Jul-3** (110.3 min, 944789f9…) | 1 | ALREADY_INGESTED as FP-EDU-001-B (batch-002 transcript, rescued durable) — **visual channel unmined** |
| Live with Farouk **Sunday Jul-5** (128.5 min, 4328a875…) | 1 | ALREADY_INGESTED as FP-EDU-001 (durable transcript; batch-004 Fable review) — **visual channel unmined** |
| Schermopname 2026-07-05 12.53.09 (e8a33802… = `sa-e8a33802a013d74f`) | 1 | ALREADY_INGESTED as the FP-INDICATOR-005 source (frames + audio done) |
| **GMT20251221 Zoom (Dec-21, 165.4 min): full mp4 ×2 (byte-identical) + PART_01..09 splits** | 11 | AUDIO ALREADY_INGESTED (FP-B004-Z2, complete transcript); mp4s = **video variants — VISUAL channel unmined** (he draws gold levels live) |
| GMT20251012 Zoom video ×2 (byte-identical; Z1) | 2 | audio ingested and **REJECTED off-method** (guest EMA session) — video variants inherit the rejection |
| 1_Welcome / 3_Exochart ×2 / 4_Templates / 6_Delta_OI | 5 | UNRELATED-to-XAU-engine (Exochart/Delta guest series; standing exclusion) |
| Ember / cinematic / personal | 17 | UNRELATED (not inspected beyond filename/hash) |

**Exact byte-identical duplicate sets (sha256):** PROJECT_EMBER (1)=(2), (3)=(4) · B003-01 ×3 ·
B003-03 ×3 · GMT20251221 full mp4 ×2 · GMT20251012 mp4 ×2 · 3_Exochart ×2. (Plus the m4a audio
duplicates already documented in batch 004.)

## 3. Coverage map
**Well covered already:** trade breakdowns w/ entries/stops/management (B003-04/05/06,
explainer-002); indicator/panel explanation (FP-INDICATOR-005 frames + Dec-series B003-01..03);
Sunday/weekly recaps (explainer-001/005); session logic, management doctrine, claim conventions
(docs + audits). **Weak/missing (and NOT closable from Downloads):** repaint evidence (needs live
capture), A-grade formula equivalence (needs forward chart-state pairs), EDU-035 fuller displacement
session (still absent), numeric displacement (doesn't exist). **Closable from Downloads — the only
remaining vein: CHART-VISIBLE level construction** — watching him *draw* the levels (audio already
mined; visuals never extracted).

## 4. Ranked ingestion queue (visual-channel passes; batches ≤3; nothing started)

| # | proposed ID | source | priority | load | frames? | questions to answer |
|---|---|---|---|---|---|---|
| 1 | **VE-Z2-VISUAL-01** | GMT20251221 **PART_01** (0–20 min of the Dec-21 Zoom — the gold TA segment per the Z2 transcript: weekly mitigation levels 4275/4261/4286, box drawing, level selection) | **HIGH** (priority-1 topic: level construction demonstrated live) | no transcription (audio done); ~10–15 sampled frames | YES | how he DRAWS zone boundaries; which objects he picks among candidates; box placement vs wick/body; panel state while marking |
| 2 | **VE-Z2-VISUAL-02** | GMT20251221 **PART_02** (20–40 min — continuation of gold TA into orb/flat-candle demos) | HIGH | same | YES | flat-candle marking; ORB boxes; magnet annotation practice |
| 3 | **VE-EDU001-VISUAL** | Live with Farouk **Sunday Jul-5** (FP-EDU-001) — targeted frames at transcript stamps 00:06–00:36 (indicator update walkthrough: London/US H/L boxes) + 01:19–01:32 (weekly-OB pre-mark drawing) | MEDIUM-HIGH | no transcription; ~12 frames at known stamps | YES | on-chart appearance of the new London/US H/L levels; how the 4430–4480 weekly zone was drawn (PM-F002 provenance detail) |
| (later) | VE-EDU001B-VISUAL | Live Jul-3 stop-width discussion frames | MEDIUM | frames only | YES | wick-relative stop placement visuals |
| (later) | Z2 PART_03..09 | remaining Zoom segments (BTC/oil/silver + Q&A) | LOW | — | maybe | only if gold content appears in the audio map |

**Overlap control:** all three Batch-1 items are visual passes over ALREADY-TRANSCRIBED audio —
zero transcription load, zero new-content risk, pure chart-evidence gain; frame stamps come from the
existing transcripts (no blind scrubbing).

## 5. Proposed Batch 1 (max 3 — NOT STARTED, awaiting explicit approval)
**VE-Z2-VISUAL-01 + VE-Z2-VISUAL-02 + VE-EDU001-VISUAL.** Rationale: they attack the single
highest-value remaining gap (chart-visible level construction — priority 1 in the mandate) using the
smallest possible set; they also add PM-F002 provenance detail and the on-chart form of the Jul-5
panel additions. Retention on ingestion will follow the standing architecture (frames under
`derived/`, review MD/JSON with timestamps, register updates; nothing enters v0.3).

## 6. Safety
Read-only inventory (enumerate/hash/mvhd-parse only); no file moved/renamed/altered; no transcription
launched; no scorer touched; no execution surface. `NOT_INTEGRATION_READY` unchanged.
