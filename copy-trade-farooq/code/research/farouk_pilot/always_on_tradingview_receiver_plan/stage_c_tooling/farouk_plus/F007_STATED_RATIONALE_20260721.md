# F007 STATED RATIONALE — SOURCE_REPORTED (registered 2026-07-21)

**Tier: PERSONAL_LIVE_METHOD_UNCONFIRMED · SOURCE_REPORTED · linked campaign: XAU-F007-20260721.**
Msg 45930-series channel, id **45976**, posted 09:07:27Z (Telegram evidence DB, CREATED):
> "Reason for potential BUYS — 1h Bullish FVG tapped / 1h Low Sweep / 1/3m Bullish CHoCH"

Why it matters: Farouk's **itemised setup reasoning published live**, attached to a campaign whose **T=0 freeze already existed and predates it** (freeze logical hash `f74697194cbbb359`, decision ts 08:26:42Z; rationale posted +41 minutes). First campaign with a stated, itemised rationale against a pre-existing freeze — the closest available thing to a labelled example. **n=1, no conclusions drawn; comparison recorded only.** The wire correctly classified 45976 as commentary (OTHER — no instruction); this registration is the evidence-layer capture.

## Lane C comparison — could Orange independently verify the three claimed features at the decision timestamp?

| Claimed feature | Orange deterministic verdict | Basis |
|---|---|---|
| 1h Bullish FVG tapped | **NOT COMPUTABLE** | No registered FVG detector exists in Orange's deterministic tooling |
| 1h Low Sweep | **NOT COMPUTABLE** | No registered sweep detector exists |
| 1m/3m Bullish CHoCH | **NOT COMPUTABLE** | No registered CHoCH detector exists; panel state (Playbook indicator, prior art FP-INDICATOR-005/006) is not captured by the bar feed |

Stated plainly: Orange's deterministic detectors (detector_v0_2/v0_3) are **message-feature classifiers** (attempt number, re-entry, caution language — F007 scored SHADOW_CANDIDATE_MEDIUM), and the bar-side tooling computes zone touches/fills only. None of the three claimed SMC features has a deterministic Orange implementation. **Constructing one ad-hoc now, after seeing the rationale, would be post-hoc fitting — refused.**

**CANDIDATE WORK ORDER (registered, NOT started):** deterministic SMC feature detectors (1h FVG formation+tap, session-low sweep, 1m/3m CHoCH) with definitions **pre-registered before any campaign comparison**, then applied prospectively from registration forward. Rationale statements like 45976 become the label source only AFTER the detector definitions are frozen. Requires operator approval to build.

## Fill reconciliation (operator screenshot, result-card images — numbers operator-transcribed)
Farouk's two fills **4060.55 and 4059.71** — both inside the published 4053-4063 zone, both between Lane A's near (4063) and mid (4058) theoretical legs. Lane A: **near leg FILLED @4063** (1/12 open after TP1 + close-worst partials, BE 4063 via SCOPED_LEG basis), **mid 4058 and far 4053 CANCELLED** (P14 effect of SL_TO_ENTRY, unfilled legs cancelled). Average entry divergence: Lane A 4063.00 vs Farouk ~4060.13 — **K-018-family fill-model divergence (2 real fills vs 3-leg model), recorded as evidence, constitution unchanged.**
