# STAGE 2 RULE MINING — STANDING GUARDRAILS (recorded 2026-07-20, D-016; binding when Stage 2 runs)

## G1 — AUDIO VERIFICATION RULE (operator-instructed)
Any candidate rule whose meaning depends on:
- a **timeframe number** (5m/15m/1h/3m…),
- a **price level**, or
- a **term on the known-mishear list**
must be **verified against the source audio** (or the on-screen chart frame) before registration — NEVER accepted from transcript text alone. Rationale: transcripts are small.en+domain-prompt (gate-passed) but residual mishears survive; a surviving 50↔15 in a timeframe context would mint a confidently wrong rule.

## Known-mishear list (v1 — extend append-only as found; transcripts are NEVER auto-edited)
| Heard | Means | Risk class |
|---|---|---|
| `50 minute` / `550 minute` | 15-minute / 5-and-15-minute | **CRITICAL (timeframe)** |
| `FPG` / `FEG` / `effigy` / `fidget` | FVG | vocabulary (mappable) |
| `sale` / `cell` | sell | vocabulary |
| `chock` / `chalk` / `truck` | CHoCH | vocabulary |
| `boss` | BOS | vocabulary |
| `obi` / `obese` | OB(s) | vocabulary |
| `bison` | buy zone(s) | vocabulary |
| `breeding space` | breathing space | phrase |
| `weeks` | wicks | phrase |
| price digits split/garbled (e.g. "four zero three one") | verify vs chart frame | **CRITICAL (price)** |

## G2 — provenance chain
Every mined rule cites: corpus source_id + transcript timestamp + (for G1-class rules) the audio-verification note or frame reference. Rules from `10 min stream` (tier-ambiguous, D-011) carry the tier ambiguity forward.

## G3 — tier + scope
Rules inherit the WEAKEST source_tier of their evidence; crypto-scoped sources can never feed XAUUSD rules (K-047).

---
## G1 ADDENDUM (2026-07-21, D-051 — operator-ratified after the pilot)
**STANDING PRINCIPLE: the mishear table is a list of SUSPICIONS, never corrections, and must never be applied without per-segment audio verification.** Proven necessary by pilot segment 5: the table would have "corrected" the GENUINE statement "change of character under three and one minutes" (CHoCH on 3m + 1m — independently corroborated by the 3-minute indicator alert standard and F007's posted "1/3m Bullish CHoCH" rationale) into a false 5-minute reading. **A wrongly-"corrected" rule reads plausibly and is undetectable downstream — the more dangerous direction of the two failure modes.**

**METHOD (recorded): in-audio semantic anchors outrank surface transcription.** Pilot segment 1: both models transcribe "the first 50 minutes", but the same breath contains "London opens 9 o'clock until 9.15" — the anchor resolves the token where the surface form cannot. An anchor must be inside the verified segment itself, never imported from elsewhere.

**Per-rule cited-segment verification stands with NO family-level shortcuts** — even a triple-confirmed mishear family never auto-resolves another rule's cited instance.

**D-052 EXTENSION OF THE PRINCIPLE (operator-ratified): suspicion of a transcript is itself an UNVERIFIED HYPOTHESIS and carries its own false-positive rate.** Pilot evidence: two of the flagged suspicions proved to be GENUINE statements wrongly suspected (segment 5 CHoCH "3m and 1m"; segment 7 sizing "do more than that" — no negation, operator-ear-verified, the "surrounding logic" reasoning was a reviewer misreading of an internally coherent ascending sizing ladder). Both models heard correctly; the suspicion was human. **Neither the mishear table nor reviewer intuition may override audio without verification.**
