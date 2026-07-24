# Multi-Position / Tranche Reconstruction Audit v0.1 (Step 8D)

**Mode: MULTI-POSITION RECONSTRUCTION AUDIT ONLY — SINGLE-SESSION.** Observation-only. Date 2026-07-11.
Listener PID 87988 untouched. Deterministic OHLC remains authority. **Safety:** no lot sizes, account IDs,
broker routes, ticket IDs, or executable order detail are recorded anywhere in this layer — widget volumes
are treated as descriptive evidence text only (or hashed), never as sizing inputs. Gates
`PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY` unchanged.

## 1. Audit verdict: what Models A and B actually modelled

| behaviour | Model A (v0_1) | Model B (v0_1b) |
|---|---|---|
| multiple EXITS (partials/tranches) | ✔ approximated (50% at posted TP1 + runner) | ✔ approximated (50% @+50p, 25% @+100p, 25% runner) |
| SL-to-entry | ✔ scratch when instruction posted | ✔ automatic BE-return scratch |
| re-entries as separate campaigns | ✔ (ledger-level: J14/J29 etc. are own setups) | ✔ |
| **multiple ENTRIES (layered zone fills)** | ✘ single median fill | ✘ single near-edge fill |
| **close-worst / hold-best as a LEG operation** | ✘ (fraction note only) | ✘ |
| intra-setup re-entries (J04 waterfall ×3, J25/J28 re-enters) | ✘ collapsed to one leg | ✘ collapsed |
| adds ("re-enter quarter size") | ✘ | ✘ |

**Both models are single-entry / multi-exit abstractions.** The missing dimension is entry-leg
multiplicity — which is exactly what "close worst entry, hold best entry" operates on.

## 2. Per-setup classification (34)

- **MULTI_POSITION_KNOWN (18)** — explicit leg language or widget evidence: J01 (close worst 44085), J04
  (waterfall ×3), J09/J10 (3-point layered re-entry), J11 (close worst 44511), J13 (close highest/hold
  lowest), J19 (44739), J20 (44769 tp-on-highest/hold-lowest), J21 (tranche exits), J23 (44903 "bad entry
  in loss, good in profit"), J24 (widgets), J25 (re-enter 45026), J26 (45089 two concurrent positions
  noted), J28 (quarter re-enter), J29 (45204), J30 (75%-out + 0.25 residual widget), S1 ("closing 0.5 …
  another 50% … leave 10%"), S3 (45553), S4 (45627).
- **MULTI_POSITION_INFERRED (11)** — partial-exit language without explicit legs: J02, J05, J07, J12,
  J14, J15, J16, J17, J18, J22, J27.
- **SINGLE_POSITION_SIMPLE (2):** S2 (stopped, one shot), J06 (tp1 then optional hold).
- **MULTI_POSITION_UNCLEAR (3):** J03, J08 (manual cuts, leg structure never described), + J26's second
  concurrent position (referenced but unobservable).

## 3. The widget irony (important, evidence-backed)

Where widgets exist, **his own position often ran as ONE unchanged volume while he instructed followers
into multi-leg management**: J24 shows the same single short at 4132.02 across all three snapshots
(no partial visible to +170p); J11 shows the same single long at 4056.64 at "take 50% off" AND at the
final close. His multi-leg instructions describe the *follower* choreography more than his own book.
Consequence: **lane-1 (his outcomes) is mostly leg-insensitive; the leg problem lives in the follower
lanes.**

## 4. Sensitivity of the big Step-8 cases

| case | leg-sensitivity | reasoning (deterministic anchors) |
|---|---|---|
| **S3** | **HIGH — the material case** | zone 4072–4083, far edge 4083 genuinely FILLED (12:47Z) and the post-fill high was ~4086.6; a hold-best leg with BE at 4083 plausibly survived the retrace that scratched Model B's 4072 near-edge leg at 12:28 (+25p) — best-leg runner could ride toward the 4021.65 low (~+300–500p on that leg) |
| J25 / J26 / S1 / J20 | LOW | far zone edges NEVER traded (adverse extremes 4144.79 / 4034.65 / 4062.43 max) — deeper legs never filled; single-leg reality confirmed by OHLC |
| S2 | NONE | far edge filled (11:58Z) but every leg dies at 4180 — loss in all reconstructions |
| J24 | LOW | his widget = single leg; follower divergence conclusion (scratch vs his +170p) unchanged |
| J30 | LOW-MODERATE | single entry, tranche exits; claims were price-based; conclusions robust |
| J11 | LOW | single-lot widget; no zone posted — leg layer has nothing to change |
| J10 | MODERATE | "3-point layered entry" is explicitly multi-leg with NO posted prices — any reconstruction is assumption; SL 4060 killed all legs regardless (loss robust), only the loss MAGNITUDE (−427p Model B) is assumption-based |

**Materiality estimate (marked ESTIMATE, not computed):** granting hold-best legs where the far edge
verifiably filled (mainly S3; partially S4/J09) would add roughly **+300–500p** to Model B's 34-trade
total (+48 → ~+350–550; mean +1.4 → **~+10–16p/trade**). It narrows the Model-A/B band from below but
does not close it — **the binding uncertainty remains instruction timing (Step-8C addendum), followed by
leg reconstruction.**

## 5. What remains assumption-based (cannot be recovered from June/July data)

Unposted leg entry prices (layered fills he never numbered — J10's three points); which legs a real
follower holds vs closes at "close worst"; per-leg BE placement (his own stops provably differ from
instructions); leg fractions (volumes are redacted-by-policy and follower-irrelevant anyway); everything
about J26's second concurrent position.

## 6. Forward capture requirements (Cycle 002 / XAU-F001) — leg events

Every XAU-F record logs a **leg-event stream** (extends the Step-8C `management_timing` block; schema in
`multi_position_reconstruction_schema_v0_1.json`): every entry message, every re-entry, every
partial-close instruction, every close-worst/hold-best, every final-close/result claim — each with exact
message ID + timestamp + leg linkage where statable. With that stream, the follower simulation becomes
leg-resolved instead of assumption-bound.

## 7. Safety confirmation

Audit + schema design only; no computation against live systems; no cycle run; no outcome matching. No
lot/risk/account/broker/ticket fields anywhere in the schema (forbidden-token guard applies to the new
record type too). No broker/QST/cTrader/nano/copy/demo/live execution; no permits/leases/orders; gates
unchanged; listener PID 87988 running; no TradingView/Worker/R2/secret action. `NOT_INTEGRATION_READY`
unchanged.

## Next step

Optional offline follow-up: compute the S3 hold-best leg deterministically (the one HIGH-sensitivity
case) to replace the +300–500p estimate with a number. Otherwise: await gold-trades activity → Cycle 002
under the 8C+8D capture spec.
