# Sprint Day 6 — Interim Decision Report

**Mode: DAY 6 INTERIM DECISION REPORT ONLY.** Observation-only. Date 2026-07-11.
Listener **PID 87988 running/untouched**. Deterministic OHLC matching remains the authority; this report is
analysis of already-validated evidence (AI narrative = review-only). No broker/cTrader/QST; no
permit/lease/order; gates `PAPER/PREVIEW/False/False`; no TradingView/Worker/R2/secret action; **nothing in
this report promotes anything to trade-ready**. `NOT_INTEGRATION_READY` unchanged.

---

## DECISION: **CONTINUE**

(Not yet DEMO_READINESS_RESEARCH_ONLY — reasons in §6. Not COLLECT_MORE-only — the evidence threshold is
already exceeded 3× and the signal is directionally clear. Not REJECT — nothing was contradicted at setup
level and the independently verified record is strong.)

---

## 1. Evidence base (sources: Day-2 report; Day-3 ledger v1; Day-4 + Day-5 matching JSONs/report)

| lane | sample | result |
|---|---|---|
| **July local (Day 2, 1m)** | 4 setups (Jun-30, Jul-7, Jul-8, Jul-10) | 2 VERIFIED_WIN · 1 VERIFIED_LOSS · 1 PARTIAL |
| **June full (Days 3–5)** | 30 setups / 33 executions / ~24 grouped campaigns | 18 VERIFIED_WIN · 2 VERIFIED_LOSS · 9 PARTIAL · 0 CONTRADICTED · 0 AMBIGUOUS_INTRABAR · 1 INSUFFICIENT (J24) |
| **Cumulative** | **33 trades matched / 18 sessions** | **20 W · 3 L · 10 P · 0 C** |
| precision | 10 trades **1m-confirmed** (J25–J30 + S1–S4) · 23 trades **5m-fallback** (Jun 1–19 subset) | intrabar guard triggered 0 ambiguities |

Decisive-outcome win rate (W vs L only): **20/23 ≈ 87%** on independent OHLC. The 10 PARTIALs are mostly
his own breakeven scratches and manual cuts — outcomes consistent with price action but inherently dependent
on his private stop placement.

## 2. Claims assessment

- **"22 trades / 2 losers" (June): PARTIALLY SUPPORTED, convention-dependent.** Exactly **2 verified
  full-SL losses** (J10 06-11, J17 06-15) — "2 losers" is precisely right under the hard-SL convention.
  Total losing trades were **5** (adding 3 self-posted manual cuts: J03, J08, J23). "22 trades" fits grouped
  campaign counting (~24), not strict counting (30/33). Verdict: favourable-but-defensible convention, not
  fabrication.
- **Win/loss honesty: materially better than expected.** Every loss was posted in real time. TP-touch
  announcements repeatedly lag the actual touch by 1–10 minutes (J06, J07, J13, J20 — the touches are real
  before he claims them). J08's "just missed our sl" was accurate to **$0.56**; J23's "it went up after I
  closed" was accurate (+293p after exit); J21's scary "just missed my sl" correctly referred to his moved
  entry-level stop.
- **The one recurring distortion: headline pip inflation.** J30 material (170/200/240p claimed vs
  128/128/175p achievable, +33–56%); S1 mild (1000+p vs 922p max); J11 unverifiable without a posted zone
  (500/800p only true under best-case layered fills). Momentum-moment claims round up; structural claims
  (entry/SL/TP levels, loss admissions) check out.

## 3. What the winners have in common (from the matched sample; review-only observations)

1. **Zone entry at a pre-marked level** (OB / FVG / BPR / session liquidity) **taken WITH an imminent
   displacement move** — the big verified winners (J26 859p MFE, J21 400p, J04 436p, S1, S3) all entered on
   the first touch of an unmitigated level during London morning (~09:00–11:30Z) or NY open (~13:30–15:00Z).
2. **The realistic edge is the first 50–130 pips**, not the runner: his own mechanical behaviour (TP1 at
   ~50p, SL-to-entry at 50–60p, "close worst hold best") converts almost every zone touch that moves 50p+
   into a locked profit. Verified TP1-before-anything-bad in 18 of 20 wins.
3. **Stated reasons match the chart**: where he posted a reason (CHoCH + sweep + FVG midpoint etc.) the
   referenced structures were present at the referenced levels (consistent with the Day-0/HR reviews).

## 4. What the losses/manual cuts have in common

1. **Re-entry escalation**: J17 (verified SL loss) was the **6th** attempt at the same long idea that day;
   J10 (verified SL loss) was a layered re-entry after a BE stop. Losses concentrate on attempts ≥3.
2. **No early displacement** → the trade never reaches the ~50p sl-to-entry milestone: all 5 losing
   outcomes (J03, J08, J10, J17, J23 + July S2) never printed 50p favourable before the adverse move.
3. **Counter-trend fades at fresh extremes** (S2 July: sell 4144–4154 into a rally, stopped at 4180.52;
   J23: "bad timing" long) — where HTF trend disagreed, the zone touch failed.
4. **End-of-session persistence** — J17's final re-entry was 16:42Z after a full day of scratches.

## 5. Missing evidence (carried forward)

- **1m upgrade for June 1–21** (23 verdicts currently 5m-fallback; TP-vs-SL guards flagged nothing, but
  claim-time precision would improve).
- **77 recovered June screenshots** — not yet reviewed/OCR'd against the ledger.
- **Forward-captured TradingView alert sequences** — the indicator lane only started Jul-7; Batch-002
  produced 0 valid CHoCH→A sequences; zero forward trades yet have an aligned alert trail.
- **More aligned CHoCH/Sweep/A sequences** tying his discretionary calls to the mechanical indicator.
- J24 entry message; his actual fills (never observable — bound everything with achievable-fill logic).

## 6. Why CONTINUE and not DEMO_READINESS_RESEARCH_ONLY (yet)

The edge signal is real on independent data, but three legs are missing before demo-readiness is even a
research topic: (a) **70% of the sample is 5m-fallback and 100% is retrospective** — zero trades have been
matched from *forward* capture with the full alert+text+screenshot trail; (b) **expectancy is not yet
quantified** — 87% decisive-win-rate is not an expectancy number until fill/scratch modelling is done
(the PARTIALs are where the money quietly leaks); (c) **the distortion channel (pip inflation) means
follower-experienced results ≠ poster-claimed results** — the shadow engine must model follower fills, not
his claims. Evidence thresholds are defined in §7; work plan in
`FAROUK_PLUS_SHADOW_ENGINE_NEXT_STEPS.md`.

## 7. Evidence thresholds before demo-readiness can even be DISCUSSED

| requirement | threshold |
|---|---|
| matched trades | ≥ 50 total, of which ≥ 15 **forward-captured** (post Jul-10, full capture trail) |
| sessions | ≥ 25 total, ≥ 10 forward |
| precision | ≥ 80% of sample 1m-confirmed (June 1–21 upgrade counts) |
| contradicted claims | ≤ 5% of setups at setup level; pip-inflation factor quantified with CI |
| alert alignment | ≥ 10 forward trades with an aligned TV CHoCH/Sweep/A sequence captured |
| expectancy model | follower-fill expectancy (TP1-centric, scratch-aware) computed and positive after spread |
| human review | 100% of shadow candidates through the existing HR process (HR-0001-style) |
| broker safety | read-only cTrader lane validated separately; execution remains gated; `NOT_INTEGRATION_READY` lift requires explicit governance sign-off — never implied by this sprint |

## 8. Safety confirmation

Listener PID 87988 verified running (start 2026-07-10 21:54:45 unchanged). No broker/demo/live execution
built or run; no permits/leases/orders; gates `PAPER/PREVIEW/False/False` unchanged; no
TradingView/Worker/R2/secret action; deterministic validators remain authority; nothing promoted to
trade-ready. `NOT_INTEGRATION_READY` unchanged.

## Next step

Execute the review-only shadow-engine plan in `FAROUK_PLUS_SHADOW_ENGINE_NEXT_STEPS.md`, starting with the
winner/loss comparison table + rule extraction (offline, from the 33-trade matched sample), while the
listener keeps accumulating forward evidence.
