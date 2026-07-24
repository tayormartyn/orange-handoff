# Active Alert Route Verification — 2026-07-14

**Mode: READ-ONLY REGISTER/EVIDENCE CROSS-CHECK.** No TradingView alert created/edited/stopped/re-armed;
no Worker deploy; no R2 write; no gate change. Inputs: Martyn's screenshots (six Active XAUUSD 3m alerts),
the FP-INDICATOR-005 `ALERT_INTERFACE_REGISTER`, LIVE-alert records (Gate E–H, Batch-002), Worker source,
and captured R2 evidence through 2026-07-14 ~05:20Z (audit `farouk_plus/overnight_indicator_alert_audit_20260714.json`).

## Route architecture (from the durable record)

Webhooks are attached to **duplicate "mirror" alerts only** — originals are never edited (mirror-first
policy, every Gate E–H and Batch-002 record). The only capture destination is the Cloudflare Worker
`farouk-tv-webhook-logger-v1` → R2 `farouk-tv-webhook-evidence-v1`, **logging-only** (every stored object:
`mode=LOGGING_ONLY`, `validation_status=ACCEPTED`; no execution surface).

## Per-alert status (screenshot set vs register vs captures)

| Screenshot alert | Register identity | Route per record | Capture evidence | Status |
|---|---|---|---|---|
| Liquidity Sweep high | LIVE010_SWEEP_HIGH_MIRROR_BATCH002 (+ original) | webhook in mirror | latest capture 2026-07-14 05:18Z | TRADINGVIEW_ACTIVE + ROUTE_CONFIGURED + FIRED_AND_CAPTURED |
| Liquidity Sweep low | LIVE011_SWEEP_LOW_MIRROR_BATCH002 (+ original) | webhook in mirror | latest 2026-07-13 23:48Z | TRADINGVIEW_ACTIVE + ROUTE_CONFIGURED + FIRED_AND_CAPTURED |
| CHoCH up | LIVE008_CHOCH_UP_MIRROR_BATCH002 (+ original) | webhook in mirror | latest 2026-07-14 00:36Z | TRADINGVIEW_ACTIVE + ROUTE_CONFIGURED + FIRED_AND_CAPTURED |
| CHoCH down | LIVE009_CHOCH_DOWN_MIRROR_BATCH002 (+ original) | webhook in mirror (Martyn-attested Jul-10 setup) | **no CHoCH-down capture since LIVE009 creation** (last CHoCH-down object 2026-07-10 07:09Z via the since-deleted H2 LIVE005) | TRADINGVIEW_ACTIVE + ROUTE_CONFIGURED(attested) + ARMED_NO_FIRING_OBSERVED — delivery never yet demonstrated for LIVE009 itself; NOT evidence of disconnection |
| **A+ or better setup** | original `LIVE001_APLUS_XAUUSD_3M`; routed mirror WAS `LIVE004_APLUS_MIRROR_GATE_H1` | **mirror deleted/disabled by Martyn 2026-07-10** (instructed in `H1_FIRE_VERIFICATION_REPORT.md`; recorded done in `H2_FIRE_VERIFICATION_REPORT.md`); Batch-002 did not recreate an A+ mirror; originals carry no webhook by policy | FIRED_AND_CAPTURED historically: 2026-07-10T04:57:02.069Z, event `0130f3b3…`, raw `"A+ or better setup"`; **zero A_PLUS objects since** | TRADINGVIEW_ACTIVE + **ROUTE_MISSING per last durable record** (see caveat) |
| **A+++ setup** | condition documented in `ALERT_INTERFACE_REGISTER` (evidence-only screenshots); **no LIVE id, no mirror ever created** | **no route ever configured in any record** | **never fired in ANY captured evidence** (phone batch + Gate-G + Jul-6 server CSV + all R2 concur) | TRADINGVIEW_ACTIVE + **ROUTE_MISSING** |

## Caveat (binding on both A-grade verdicts)

- Zero captured events is **NOT** treated as proof of disconnection (audit rule): A+ is rare (0 in most
  observed windows) and A+++ has never fired anywhere — so "no R2 object" alone distinguishes nothing.
  The ROUTE_MISSING conclusions rest on the **positive configuration record** (mirror deletion recorded;
  webhook attachments only ever happen as recorded, gated events), not on capture absence.
- What the record cannot see: a webhook added to an original/new A-grade alert **after** 2026-07-10
  without a record. Only the TradingView alert-dialog webhook field (Martyn, ~30 seconds per alert) can
  confirm the current field state. No local file, worker config, or R2 object encodes per-alert webhook
  presence.
- No recent TradingView server-side alerts-log export exists (newest local: `TradingView_Alerts_Log_2026-07-06.csv`),
  so whether the A+/A+++ *conditions* fired overnight at all is locally unknowable.

## Verdicts

- **A+ alert: ACTIVE BUT ROUTE MISSING** (per the last durable record; historical fire WAS captured via
  the deleted H1 mirror — that capture verified the pipeline, not the currently-active alert instance).
- **A+++ alert: ACTIVE BUT ROUTE MISSING** (no route has ever existed for this condition).

"Armed but did not fire" is therefore NOT the record-supported explanation for zero overnight A-grade
events — the record-supported explanation is "no capture route since 2026-07-10 04:57Z (A+) / ever (A+++)",
pending Martyn's webhook-field check.

## Action required

YES — but Martyn's, not Claude's, and only if A-grade capture is wanted:
1. Open each A-grade alert's dialog and check the Webhook URL field (confirms/refutes ROUTE_MISSING).
2. If missing and capture is desired: duplicate-first mirror per the established checklist
   (`BATCH_002_LOW_NOISE_MIRROR_SETUP_CHECKLIST.md` pattern; URL from the gitignored LOCAL_ONLY file;
   never edit the originals). Note the webhook-secret rotation flag remains OPEN/deferred (Batch-002).
3. Claude touches nothing on TradingView either way.

## Safety

Read-only verification; v0.3/v0.2/v0.4 untouched (v0.2 comparator-only, v0.4 offline-only); gates
`PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY` unchanged; pre-marks frozen; listener PID 13172
untouched.

---

## ADDENDUM — A-grade route activation: OPERATOR ATTESTATION (2026-07-14T07:00:48Z)

**Martyn attests (manual TradingView action, performed by Martyn only; Claude touched nothing and the
webhook URL is not exposed here or anywhere):**
- `A+ or better setup`: established logging-only webhook URL populated and SAVED.
- `A+++ setup`: established logging-only webhook URL populated and SAVED.

**Recorded route status (supersedes the ROUTE_MISSING verdicts above as of this timestamp):**
- A+ or better setup: **ROUTE_OPERATOR_ATTESTED / DELIVERY_UNVERIFIED**
- A+++ setup: **ROUTE_OPERATOR_ATTESTED / DELIVERY_UNVERIFIED**

Delivery is NOT claimed verified until each condition naturally fires and the object is found in R2.
**First-fire protocol (each condition, when it happens):** preserve raw payload byte-exact; record
`received_at_utc` + derived 3-minute bar-close (`DERIVED_FROM_RECEIVED_AT` unless a payload trigger_time
exists); verify destination is logging-only (`mode=LOGGING_ONLY`); check duplicate delivery by
(alert_type | direction | bar_close) — same-bar primitive-vs-composite pairs are NOT duplicates; only
then update status to **FIRED_AND_CAPTURED**.

Standing guards unchanged: no XAU-F001 from indicator alerts; nothing enters v0.3;
DOCUMENT_FORMULA_KNOWN / INDICATOR_EQUIVALENCE_UNKNOWN; F5 repaint guard binding; gates
`PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY` unchanged; listener PID 13172 healthy,
single-instance, untouched; cursor 45710 = store max 45710.

---

## ADDENDUM 2 — LIVE R2 CAPTURE VERIFICATION (2026-07-20, operator-authorised)

Method: temp token-gated read-only list branch on the CURRENT baseline (483ad090 + list endpoint), deployed
14:5xZ, all listing/fetching read-only, then **reverted to byte-exact baseline 483ad090e5 (deploy b4367ae5)
and token destroyed**; GET ?list re-verified 405. POST path untouched throughout; bar feed unaffected.

**Result: the alert lane never stopped.** 5,295 event objects 07-14→07-20 (07-18 Saturday = 0, correct);
~160 small (≈729 B) plain-text alert payloads on exact 3-minute closes, continuing through 2026-07-20T14:18Z.
Sampled 20 objects:

| Route | Last CONFIRMED capture (sampled) |
|---|---|
| Sweep low (LIVE011 mirror) | **2026-07-20T14:18:04Z** (+ 12:27, 05:27/33/39, 07-19 22:06/22:33 — fired within hours of Sunday reopen) |
| Sweep high (LIVE010 mirror) | **2026-07-20T11:36:02Z** (+ 11:03, 10:57, 07-17 18:33) |
| CHoCH up (LIVE008 mirror) | **2026-07-20T11:33:01Z** (+ 07-20 00:18/02:33, 07-19 23:54, 07-17 18:30, 19:54) |
| CHoCH down (LIVE009 mirror) | NOT OBSERVED in 20 samples — ARMED_NO_FIRING_OBSERVED persists (unsurprising in a rallying tape; full 160-object census not run) |
| **A+ or better** | **FIRED_AND_CAPTURED ×2: 2026-07-17T19:51:03.994Z and 2026-07-17T20:30:06.166Z**, raw `"A+ or better setup"`, derived 3m closes 19:51:00Z / 20:30:00Z, mode=LOGGING_ONLY, distinct bar-closes (not duplicates). **Status upgrade: ROUTE_OPERATOR_ATTESTED/DELIVERY_UNVERIFIED → FIRED_AND_CAPTURED** per the first-fire protocol (raw preserved byte-exact in R2; DERIVED_FROM_RECEIVED_AT basis). |
| A+++ | never captured (consistent with never having fired anywhere) |
| 1m bar feed | continuous; tracker ingesting live (last bar minutes old at verification) |
| LIVE003_FAROUK_MIRR | payload identity not distinguishable in samples (no matching distinct raw text observed); route state unresolved from R2 alone |

**Correction to the 2026-07-20 stopped-alert report:** that report said the A+/A+++ routes were Active "per
the screenshot" — WRONG: they were not visible in the supplied frames (99+ alert list, partial). Corrected
status: A+ = delivery-PROVEN (above) regardless of which alert instance carries it; A+++ = TradingView
instance state UNOBSERVED → added to Martyn's visual-check list (~30s: confirm the A+++ alert shows Active).

**Named defect registered (ALERT_LANE_SILENCE_UNMONITORED):** the fail-loud intake observer watches the
TELEGRAM lane only. NOTHING monitors alert-lane delivery: had the mirrors silently stopped, no process,
counter or alert would have fired. Six days of uncertainty were only resolvable by this manual R2 audit.
Registered in orange_brain known_defects (monitor design = future approved task; candidate: a read-only
staleness check on the predictable bars/ lane + a daily small-object count, run from ORANGE_STATUS).

**ADDENDUM 2 close-out (2026-07-20, Martyn visual check):** the `A+++ setup` alert shows **Active** in
TradingView (Martyn, manual, ~30s check as requested). Recorded status: A+++ = TRADINGVIEW_ACTIVE +
ROUTE_OPERATOR_ATTESTED (07-14) + DELIVERY_UNVERIFIED (condition has still never fired anywhere — delivery
can only be proven by a natural first fire per the first-fire protocol). Martyn's visual-check list from
Addendum 2 is now EMPTY.
