# Farouk Evidence Pilot

A **controlled, manual** evidence-pilot workspace to reconstruct Farouk's actual XAUUSD methodology
from a **small, representative sample** that Martyn legitimately possesses.

> This workspace does **not** rip channels, bypass access controls, or download a private library. It
> only processes files **supplied manually, one at a time**, and refuses any asset without an approved
> rights record. It contains **no trading detector, no broker action, and no execution change.**

## Pilot sample (supplied manually by Martyn)
- 5 winning trade campaigns · 2 stopped/losing campaigns · 2 rejected/cancelled opportunities (where available)
- 1 ORB, 1 session-liquidity, 1 momentum/reversal educational video
- associated messages, screenshots, native media · corresponding XAUUSD market data · forward-observed
  indicator states where available

## Directory structure
```
research/farouk_pilot/
├── README.md, rights_register.csv, asset_manifest.csv, campaign_register.csv,
│   educational_claims.csv, alignment_records.csv, .gitignore
├── rights_gate.py        # fail-closed processing rule
├── ingest.py             # deterministic local ingestion CLI (no upload)
├── pit_features.py       # point-in-time market features (strictly causal)
├── dossiers/             # TradeDossier per campaign (TEMPLATE_dossier.json)
├── raw/{messages,images,videos,indicator_observations,market_data}/   # gitignored
├── derived/{transcripts,frames,normalized_observations}/              # gitignored
├── schemas/pilot_schemas.py   # 11 versioned schemas + validator
└── tests/
```
Proprietary evidence (`raw/`, `derived/`, filled dossiers, the asset manifest) is **git-ignored**;
only schemas, tests, anonymised fixtures, register headers, and directory markers are committable.

## Rights gate (fail closed)
Every supplied asset needs a `RightsRecord` (in `rights_register.csv`) with: `rights_status`,
`source_owner`, `access_basis`, and the permission flags `permitted_internal_analysis`,
`permitted_transcription`, `permitted_machine_processing`, `permitted_sharing_external`,
`permitted_derivative_implementation`, plus `retention_notes`. **An asset is not processed if the
relevant permission is `false` or unknown, or `rights_status` is not `APPROVED`.** This is a mechanical
record + rule — it makes **no legal conclusions**.

## Processing workflow
```
manually supplied asset
  → rights check              (rights_gate.rights_permit; fail closed)
  → immutable ingestion       (ingest.py: SHA-256, asset id, manifest append, dedup, no upload)
  → transcript / frame extraction   (derived/transcripts, derived/frames)
  → timestamp alignment       (AlignmentRecord)
  → objective observations    (ChartObservation / IndicatorObservation — facts, not claims)
  → human adjudication        (Martyn resolves claim vs evidence)
  → candidate rules           (CandidateRule)
  → trade dossier             (TradeDossier)
```
**Claims vs observations are kept separate.** A statement made in a video is an `EducationalClaim`
with `support_status = SOURCE_CLAIM` until trade evidence **supports** or **contradicts** it.

## Point-in-time rule
At evaluation time **T**, no derived market feature may use information occurring **after T**.
`pit_features.py` filters strictly on `ts_ms <= as_of_ms`, so appending/mutating future candles can
never change an earlier session high/low, feature, observation, or decision (proven by tests).

## Ingestion command
```
python research/farouk_pilot/ingest.py \
    --file <path-to-manually-supplied-file> \
    --kind {message|image|video|market_data|indicator_observation} \
    --rights-record-id <RightsRecord id, already APPROVED in rights_register.csv> \
    [--source-captured-at 2026-07-01T12:00:00Z] [--notes "..."] [--dry-run]
```
It computes SHA-256, mints an immutable `asset_id = sa-<sha16>`, captures filename/MIME/size/timestamps,
appends to `asset_manifest.csv` **without overwriting**, detects duplicates by hash, and **refuses** if
the rights record is missing/unapproved for machine processing. It uploads nothing and never touches
Discord or TradingView.

## Manual steps to add the first asset
1. Place the file locally, e.g. `research/farouk_pilot/raw/videos/orb_lesson.mp4` (never committed).
2. Add a row to `rights_register.csv` with a new `rights_record_id`, `rights_status=APPROVED`, the owner,
   the access basis, and set the permission flags you actually hold to `true` (leave unknowns blank).
3. Dry-run first:
   `python research/farouk_pilot/ingest.py --file raw/videos/orb_lesson.mp4 --kind video --rights-record-id RR-001 --dry-run`
4. If the dry-run reports the correct hash/asset id and is not refused, run it for real (drop `--dry-run`).
5. Create derived records (transcripts, observations, dossier) that cite the returned `asset_id` in their
   `source_asset_ids`.

## Schemas (v1.0.0)
`SourceAsset`, `RightsRecord`, `TradeCampaign`, `TradeEvent`, `TranscriptSegment`, `ChartObservation`,
`IndicatorObservation`, `EducationalClaim`, `AlignmentRecord`, `CandidateRule`, `TradeDossier`.
Every derived record must cite `source_asset_ids` (lineage, enforced by the validator).
