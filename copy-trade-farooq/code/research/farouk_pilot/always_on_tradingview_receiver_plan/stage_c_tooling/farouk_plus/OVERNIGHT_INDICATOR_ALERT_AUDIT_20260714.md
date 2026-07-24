# Overnight Indicator Alert Audit — 2026-07-14

**Mode: OBSERVATION/REVIEW ONLY — SINGLE-SESSION.** Indicator alerts are capture / Lane-6 annotation /
hypothesis evidence only. Nothing entered v0.3 (v0.2 comparator-only, v0.4 offline-only untouched).
Machine-readable inventory: `overnight_indicator_alert_audit_20260714.json` (39 rows, full raw payloads).
Gates `PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY` unchanged; all four pre-marks frozen.

## 1. Scope and retrieval provenance

- Last verified R2 state before this audit: **103 objects at 2026-07-10T18:03Z** (Batch-002 extended
  time-box close). Bucket total now **146**. Per-day since: Jul-10 remainder 11 (audited that session's
  window only — the 11 were outside it and are counted, not payload-audited here), **Jul-11: 0,
  Jul-12: 3, Jul-13: 30, Jul-14 (to ~05:20Z): 6**.
- This audit fetched and classified **all 39 objects from Jul-12/13/14** — i.e. the overnight window
  PLUS the unaudited backlog since the travel shutdown; nothing silently dropped.
- Retrieval used the established procedure: temporary **secret-free token-gated read-only list branch**
  (deploy version `b86a19d0…`) → key enumeration → **immediate revert to pure logging-only**
  (version `1f1efa0c…`, src sha256 == baseline `30bdc54d…`) → negative checks
  `GET /__verify_list__?t=…`→405, `GET /`→405, `POST /tv/<wrong>`→404 (all pass) → object payloads
  fetched via wrangler account auth (`r2 object get --remote`), 39/39 OK. **No webhook secret used,
  printed, or stored; token dead with the reverted version; backup removed.**

## 2. Alert inventory (39 events)

| type | count | payload text | parse_status |
|---|---|---|---|
| SWEEP_LOW | 21 | `Liquidity Sweep low` | INVALID_JSON (plain text — expected for these alerts) |
| SWEEP_HIGH | 12 | `Liquidity Sweep high` | INVALID_JSON |
| CHOCH_UP | 6 | `CHoCH up (bullish)` | INVALID_JSON |
| CHoCH down / BPR formed/tapped / Engulfing / Asia trap | 0 | — | — |
| **A+ / A+++ / A+ or better / A LONG / A SHORT / Any-alert composite** | **0** | — | — |

- **Every event is PRIMITIVE** (single-condition mirror alerts LIVE008–LIVE011). No composite fired and
  no composite mirror is armed (LIVE012 remains closed since 2026-07-10; A-grade named conditions have
  no armed mirror).
- **Instrument/timeframe:** payloads carry neither → attributed **XAUUSD 3m by alert-definition
  attestation** (LIVE001-mirror set), payload-level UNKNOWN. Direction is the type's bias
  (sweep-low/CHoCH-up = LONG bias; sweep-high = SHORT bias), not an order instruction.
- **Bar-close:** derived per event by flooring `received_at_utc` to the 3-minute boundary
  (`DERIVED_FROM_RECEIVED_AT`; all stamps land ≤23s after a boundary). No payload `trigger_time` exists.
- **Dedup key** = `type|direction|bar_close`: **0 duplicate groups; 0 same-bar clusters** (no
  primitive-vs-composite same-bar case arose — no composites at all).
- **Chart/panel state evidence: NONE for every alert event** (payload-only capture; no panel screenshot
  lane exists). Nearest contemporaneous chart evidence is the Columbus metals-channel photos
  (msgs 45695–45699, preserved hash-addressed in `prospective_media_v1`) — DIFFERENT SOURCE, guarded
  annotation only, never merged into alert rows.
- **Repaint status: UNKNOWN on all 39 (F5 binding).** The :00–:23s post-close stamps are *consistent
  with* bar-close alignment but static payloads cannot demonstrate non-repainting.

## 3. Overnight window specifically (post listener restart 2026-07-13 22:32Z → 2026-07-14 ~07:15Z)

8 alerts: `23:03Z SWEEP_LOW · 23:48Z SWEEP_LOW · 00:03Z SWEEP_HIGH · 00:36Z CHOCH_UP ·
02:18Z SWEEP_HIGH · 03:33Z SWEEP_HIGH · 04:39Z SWEEP_HIGH · 05:18Z SWEEP_HIGH`
(event_ids `2aff191b · c47bafd5 · f18a8c04 · e2c3c750 · 36774167 · d667b7a8 · 20f9a2d9 · 43113309`).
Observation (annotation only, no inference into any scorer): the 4-sweep-high Asia run 02:18–05:18Z is
contemporaneous with the Columbus gold long/reversal discussion (45697–45699) — recorded as guarded
context, NOT a signal or confluence claim.

## 4. XAU control (Phase 3)

- All events concern XAUUSD (attested) → recorded as **indicator evidence only**.
- **XAU-F001 NOT created** — an indicator alert alone can never create it, and **no genuine prospective
  Farouk Gold post exists** (SCAN_06: zero Farouk messages 45695–45710; the Columbus metals posts are
  XAU_NON_FAROUK and do not satisfy the contract).
- **No pre-mark created or modified.** Guarded annotation vs PM-F001/2/3/4: the payloads carry **no
  price levels**, so no zone comparison is even possible → `PRE_MARK_INSUFFICIENT_CONTEXT` on all 39;
  no formal Farouk-post match exists or is claimed.

## 5. A-grade forward dataset (Phase 4)

**Zero qualifying events (A+ / A+++ / A LONG / A SHORT) → zero forward-test rows created.** Nothing
fabricated; the dataset remains empty pending a real qualifying event.
`DOCUMENT_FORMULA_KNOWN / INDICATOR_EQUIVALENCE_UNKNOWN` unchanged; document grade never inferred;
FVG/BPR/OB/sweep/trend/freshness/session/panel component fields remain UNKNOWN by construction;
F5 repaint guard remains binding.

## 6. Safety confirmations

- Listener PID 13172 running/untouched throughout, single instance; store max 45710 = committed cursor.
- No TradingView alert touched; originals untouched; Worker restored to pure logging-only and verified.
- No broker/QST/cTrader/demo/nano/copy surface; no permit/lease/order/sizing/account/route fields.
- Scorer hashes re-verified (v0.3 `DD1A5A1A…`, v0.2 `F602E2FD…`, v0.4 script `a2984641…`); no Batch
  finding entered v0.3; ORB/stop-width/POC/panel/no-trade fields remain capture-only.
- Gates `MODE=PAPER / LISTENER_MODE=PREVIEW / EXECUTION_ENABLED=False / CTRADER_EXECUTION_ENABLED=False`;
  `NOT_INTEGRATION_READY` unchanged; integrity suite: see run log (ALL PASS expected post-write).

## 7. Next step

Cycle 006 stays OPEN on the Farouk gold post trigger. PM-F001 expires 2026-07-17, PM-F003 2026-07-19 —
expiry resolution watch continues. A-grade forward dataset waits for a real composite event (requires a
re-armed, short, deliberate LIVE012-style window — Martyn's action, not Claude's).
