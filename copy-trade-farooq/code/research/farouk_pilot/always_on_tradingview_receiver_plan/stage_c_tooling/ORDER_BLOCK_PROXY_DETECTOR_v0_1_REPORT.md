# Order-Block Proxy Detector v0.1 — Report

**Mode:** OFFLINE ORDER-BLOCK PROXY. Looks for possible OB context around a candidate anchor from OHLC.
**Proxy-only, candidate-only, human-review required. Never claims a confirmed Farouk OB; never emits a
tradeable entry zone.** No R2, no deploy, no TradingView, no broker/QST. `NOT_INTEGRATION_READY` unchanged.

## Files

- `order_block_proxy_detector_v0_1.py` — the detector (pure compute; CSV read only in `__main__`).
- `test_order_block_proxy_detector_v0_1.py` — tests (synthetic OHLC).
- `FAROUK_ORDER_BLOCK_PROXY_POLICY_v0_1.md` — corpus-grounded policy (what it may/may not do).

## Output

detector_version, anchor, direction_hint, `order_block_proxy_found`, `proxy_direction`
(BULLISH_OB_PROXY / BEARISH_OB_PROXY), `candidate_candle_time_utc`, `candidate_zone_high/low` (OB candle
**body** — descriptive), `displacement_after_candidate` + `displacement_ratio`, `mitigation_touched`,
`distance_from_anchor_min`, `confidence` (**LOW only**), `evidence_summary`, `missing_evidence`, warnings,
and the safety block: `requires_human_review=true`, candidate_only=true,
execution/broker/qst/order_intent/risk_sizing=false.

## Logic (conservative proxy)

- **LONG** context → last **bearish** candle before an **upward displacement proxy** (range ≥ 2.0× rolling
  ATR). **SHORT** → last **bullish** candle before a **downward displacement proxy**.
- Requires a qualifying displacement after the candidate candle; else `order_block_proxy_found=false`.
- **Mitigation proxy:** flags if price re-entered the zone after displacement (→ "may be spent" /
  degraded).
- Zone bounds = candle **body**, **descriptive evidence only** — no entry/SL/TP/size/route fields exist.
- **Confidence is LOW by default and never higher at v0.1.** Always `NEEDS_HUMAN_REVIEW`.
- Leaves corpus-UNKNOWN pieces (FVG-left-behind, first-tap numeric rule, HTF alignment) in
  `missing_evidence` — never asserted.

## Test results — ✅ PASS

`python test_order_block_proxy_detector_v0_1.py` → **7 tests, OK.** Covers: bullish OB proxy in a LONG
sequence; bearish OB proxy in a SHORT sequence; no OB proxy without displacement; malformed/empty OHLC →
warning not fake; zone bounds descriptive (no entry/SL/TP keys); requires_human_review=true; all safety
flags false; non-directional hint → not found.

## Safety confirmations

- Proxy-only; **no confirmed OB claimed**; `requires_human_review=true` on every record.
- Candidate-only; no execution / order / broker / lot / account / risk / permit / lease field.
- Offline; read-only CSV; no broker/cTrader/QST; no deploy.
- **`NOT_INTEGRATION_READY` unchanged.**

## Status

v0.1 — implemented, tested (7/7). Applied to the 3 Gate G candidates (see replay + rescoring reports).
