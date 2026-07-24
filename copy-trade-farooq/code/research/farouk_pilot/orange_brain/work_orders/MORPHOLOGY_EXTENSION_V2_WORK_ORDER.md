# MORPHOLOGY EXTENSION v2 — PROPOSED WORK ORDER (approved-in-principle D-020; code changes follow THIS document)
Scope: interpreter.py entry + SL-variant families. Target: amend D-018 to SATISFIED. Sequence (operator-fixed): this extension → full replay re-proof → D-018 amended → drift canary → demo lane.

## A. New morphology families
**A1 — single-price entry family** (pre-June era, could recur):
- `gold long sl 5090` / `gold long 5015 sl` (direction word + gold + single SL, entry at market/implied)
- `XAUUSD SELL 4635 … SL @ 4670` (single entry price + labelled SL)
- `High-risk short on gold. (entry 4740.2) Stop loss at 4762`
- `Gold buy sl 4710 … Entry 4732` (separate Entry line)
- Design: ENTRY with `zone_low == zone_high == price` where a single price exists; entry-at-market (no price) parses ENTRY only when direction + gold-instrument + SL all present, zone = `AT_MARKET_UNPRICED` flag (engine treats fail-closed: proposal-only, no fill simulation without price). Never guess a zone.
**A2 — SL-variant family** (timeless): `stoploss to entry` (one word) · `sl entry` / `move sl entry` (no to/at) · `stop( |-)loss (now )?(at|to) <price>` · `set (your )?stop-?loss at <price>` · typo class `enty`/`entyr` · `take N% sl entry` (compound: TAKE_PCT + SL_TO_ENTRY co-delivery).

## B. Hard assertions (write as FAILING tests FIRST, then fix)
1. **`gold long sl 5090` → ENTRY. NEVER MANAGEMENT/REVISED_STOP.** (The entry-misread-as-stop-move class — worst copy-trader failure: modifies an unrelated position.) Entry detection must run BEFORE stop-instruction typing for any message containing a direction word + instrument evidence.
2. Every A1/A2 sample above (verbatim from the archive) classifies to its intended type.
3. Claimed-pips / result cards still NEVER terminal (R-003 doctrine).

## C. No-regression proof (mandatory before any restart)
1. **F001–F006 byte-identical:** capture `classify()` + `type_instructions()` outputs for every real message of all six campaigns (45711…45935 sets) BEFORE the change; assert byte-identical AFTER.
2. Full existing battery green (~1090 checks: follower/wire/tracker/intake/close-pct/EPPC/watcher-race/full-exit suites).
3. Replay regression set 12/12 PLUS the new A1/A2 fixtures.
4. **Full 43,969-row replay re-proof** (parser_coverage_replay.py, reusable as-is): expect archive PARSED_ENTRY ≈ old-extractor's 240 Farouk XAU signals (reconcile the delta with named reasons); stop-wording quarantine class shrinks with every remaining member re-sampled.
5. Diff report: every message whose disposition CHANGED, classed (entry-gained / mgmt-type-changed / quarantine-released) — no unexplained changes.

## D. Deployment discipline
New interpreter sha recorded; restart ONLY the usual 4 (tracker/wire/watcher/observer — the guards.py loaders); listener/companion/shadow untouched; ledgers byte-identity proven through restart; D-018 amended only after C1–C5 all green. RETROSPECTIVE outputs stay tagged; no campaign backfill from newly-parsed old entries (they are corpus evidence, NOT campaigns — no freezes, no backdating, K-021 unchanged).

## E. Estimate
One focused session: fixtures first (~40 new checks), regex/order surgery, battery, replay, diff review, restart, report.
