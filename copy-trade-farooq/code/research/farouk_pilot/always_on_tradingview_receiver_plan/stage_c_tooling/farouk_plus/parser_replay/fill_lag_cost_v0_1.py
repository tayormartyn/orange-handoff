"""fill_lag_cost v0.1 — READ-ONLY measurement (D-037 item B).

Retires the master-vNEXT 'fill_lag_cost measured' blocker and feeds the demo-lane spec.
Method (stated before results; no fitting, no promotion):

  1. BAR DELIVERY LAG: for every ACCEPTED 1m bar in the tracker ingestion log,
     lag = receive_ts - (event_ts + 60)   (a 1m bar closes at open+60; the webhook fires
     at close; receive_ts is when the tracker pulled it from R2). This bounds how stale
     Orange's price view is when it detects fills/levels from bars.
  2. MESSAGE PIPELINE LAG: for every campaign-driving Telegram message (fwd-ledger
     setups + tracker slice message_ids), listener lag from the evidence DB
     (listener_received_at_utc - telegram_posted_at_utc; cross-check listener_latency_ms).
  3. ACTUATION LAG + PRICE DRIFT COST per management action: tracker slices record the
     bar_ts at which an instruction was applied and the execution basis price.
       actuation_lag = (slice.bar_ts + 60) - telegram_posted_at
       drift_cost_pips = signed(close_at_msg_bar - exit_price) for closes of LONGs
         (positive = lag cost: price fell between Farouk's post and the applied basis);
         sign flipped for SHORTs.
     ENTRIES are resting LIMIT legs at posted prices — fill lag cost is structurally ~0
     (the order rests at the level; no chase), stated rather than computed.

Scope: campaigns with tracker slices (F004, F006). F006 is statistically EXCLUDED from
expectancy (OUTCOME_AFFECTED_BY_DEFECT) — these are OPERATIONAL latency metrics, not
expectancy numbers; disclosed. F005 = NO_FILL (no slices). Genuine prospective count for
expectancy purposes remains 2 (F004, F005).
"""
import json
import os
import sqlite3
import statistics
from datetime import datetime, timezone

ST = r"C:\Users\Marty\signal-terminal"
FP = os.path.join(ST, r"research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling\farouk_plus")
FA = os.path.join(FP, "follower_assistant")
MT = os.path.join(FA, "market_tracker")
OUT_JSON = os.path.join(FP, "parser_replay", "fill_lag_cost_v0_1_results.json")

BANNER = "READ-ONLY MEASUREMENT | NO BROKER ACTION | NOT AN EXPECTANCY ARTIFACT"


def iso_to_epoch(s):
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def main():
    # 1) bar delivery lag over the whole ingestion log
    bars = {}
    lags = []
    with open(os.path.join(MT, "ingestion_log_v0_1.jsonl"), encoding="utf-8") as f:
        for ln in f:
            r = json.loads(ln)
            if r.get("kind") != "ACCEPTED":
                continue
            b = r["bar"]
            ets, rts = int(b["event_ts"]), int(b["receive_ts"])
            bars[ets] = b
            lags.append(rts - (ets + 60))
    # Catch-up batches (reboot/weekend backfill: old bars pulled at once) are not live
    # operating lag — split at 600s so steady-state and recovery are reported separately.
    live = [x for x in lags if x <= 600]
    catchup = [x for x in lags if x > 600]
    lag_stats = {
        "n_bars": len(lags),
        "steady_state_lte_600s": {
            "n": len(live), "median_s": statistics.median(live),
            "p90_s": statistics.quantiles(live, n=10)[-1], "max_s": max(live),
        },
        "catchup_gt_600s": {
            "n": len(catchup), "share": round(len(catchup) / len(lags), 3),
            "max_s": max(catchup) if catchup else None,
            "note": "backfill after outages/weekend gaps — bars delivered late in batches; "
                    "matches known host-reboot gaps (OQ-7), not live-mode delivery",
        },
    }

    # 2+3) per-slice actuation lag + drift cost from the latest tracker snapshot per setup
    latest = {}
    with open(os.path.join(MT, "tracker_ledger_v0_1.jsonl"), encoding="utf-8") as f:
        for ln in f:
            r = json.loads(ln)
            if r.get("record_type") == "TRACKER_SNAPSHOT":
                latest[r["setup_id"]] = r["snapshot"]

    db = sqlite3.connect(os.path.join(ST, r"campaign_extractor\prospective\data\prospective_evidence_v1.db"))

    def msg_times(mid):
        row = db.execute(
            "select telegram_posted_at_utc, listener_received_at_utc, listener_latency_ms "
            "from prospective_message_evidence where telegram_message_id=? "
            "order by rowseq desc limit 1", (str(mid),)).fetchone()
        if not row:
            return None
        return {"posted": iso_to_epoch(row[0]), "listener_received": iso_to_epoch(row[1]),
                "listener_latency_ms": row[2]}

    actions = []
    for sid, snap in sorted(latest.items()):
        direction = snap.get("direction")
        for sl in snap["lanes"]["LANE_A"]["engine"].get("slices", []):
            mid = sl.get("message_id")
            if mid is None:
                continue  # non-message-driven (e.g. adjudicated final close) — no lag concept
            t = msg_times(mid)
            if not t or not t["posted"]:
                continue
            bar_ts = int(sl["bar_ts"])
            msg_bar = bars.get((t["posted"] // 60) * 60)
            close_at_msg = float(msg_bar["close"]) if msg_bar else None
            exit_price = float(sl["exit"])
            drift = None
            bound = None
            if close_at_msg is not None:
                raw = close_at_msg - exit_price  # LONG close: positive = price fell = cost
                drift = raw if direction == "LONG" else -raw
                # tracker applies within the message bar, so bar-close drift is ~0 BY
                # CONSTRUCTION; the honest number is the worst-case intra-bar bound
                bound = float(msg_bar["high"]) - float(msg_bar["low"])
            actions.append({
                "setup_id": sid, "message_id": mid, "reason": sl["reason"],
                "leg_id": sl["leg_id"], "direction": direction,
                "posted_utc": t["posted"], "listener_lag_s": (
                    t["listener_received"] - t["posted"] if t["listener_received"] else None),
                "listener_latency_ms_recorded": t["listener_latency_ms"],
                "actuation_lag_s": (bar_ts + 60) - t["posted"],
                "close_at_msg_bar": close_at_msg, "applied_exit_basis": exit_price,
                "drift_cost_pips_signed": round(drift * 10, 2) if drift is not None else None,
                "intra_bar_worst_case_bound_pips": round(bound * 10, 2) if bound is not None else None,
                "note": "positive drift = lag cost; bar-close drift ~0 BY CONSTRUCTION "
                        "(applied basis = message-bar close) — worst case bounded by the "
                        "message bar's high-low range at the measured 3-34s actuation lag",
            })
    db.close()

    covered = [a for a in actions if a["drift_cost_pips_signed"] is not None]
    result = {
        "banner": BANNER,
        "method": "see module docstring; stated before computation",
        "bar_delivery_lag": lag_stats,
        "management_actions_measured": actions,
        "summary": {
            "n_actions": len(actions),
            "n_with_price_coverage": len(covered),
            "drift_cost_pips_signed": [a["drift_cost_pips_signed"] for a in covered],
            "intra_bar_worst_case_bound_pips": [a["intra_bar_worst_case_bound_pips"] for a in covered],
            "actuation_lag_s": [a["actuation_lag_s"] for a in actions],
            "entries_note": "LIMIT legs rest at posted prices: entry fill-lag cost structurally ~0; "
                            "lag risk concentrates in MANAGEMENT actions and bar-based detection.",
            "disclosure": "F006 actions are operational-latency evidence only "
                          "(OUTCOME_AFFECTED_BY_DEFECT, statistically excluded); genuine "
                          "prospective count for expectancy purposes = 2 (F004, F005).",
        },
        "review_only": True, "executable": False, "trade_ready": False, "observation_only": True,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1)
    print(json.dumps({k: result[k] for k in ("bar_delivery_lag", "summary")}, indent=1))
    print("wrote", OUT_JSON)


if __name__ == "__main__":
    main()
