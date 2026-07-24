"""
backfill_audit.py — READ-ONLY validation diagnostics for the GOLD signal archive.

Validates the back-filled gold signals before any aggregate from them is trusted.
ADVISORY ONLY: changes NO scoring, writes NOTHING to the archive, never touches the
signed-off 28 baseline or the LIVE stub. It reads the archive and writes diagnostic
artifacts under data/audit/.

Run order matters (the brief: FREEZE before interpreting):
  1. FREEZE & RECORD — lock detector/parser/calc versions + shadow config hash +
     the flag thresholds + the master seed, to data/audit/freeze.json.
  2. UNCORRECTED BASELINE — the raw aggregate over ALL gold, INCLUDING known parse
     errors (e.g. the +221.63R outlier), saved labelled + NOT trusted.
  3. DIAGNOSTIC FLAGGING — parse-error suspects, high-risk categories, top-10% R.
  4. AGGREGATES — flagged vs clean; mean AND median; WITH and WITHOUT flagged;
     gold denominator reported separately (no silver/crypto/forex mixed in).
  5. FULL GOLD AUDIT CSV — all 296 gold rows for independent review.

Gold denominator = 296 (27 signed-off + 269 back-filled). Silver/crypto/forex are
NOT included in the gold number anywhere.

Usage:  python backfill_audit.py
"""

import csv
import json
import os
import re
import sqlite3
import statistics
import sys
from datetime import datetime, timezone

import archive            # for DETECTOR_VERSION / PARSER_VERSION / CALC_VERSION (read-only use)
import shadow_config

ARCHIVE_DB = "data/signal_archive.db"
AUDIT_DIR = "data/audit"
MASTER_SEED = 20260628    # recorded so every random selection in the audit is reproducible

# --- FROZEN flag thresholds (advisory) --------------------------------------
R_IMPLAUSIBLE = 5.0
LEVEL_LOW_RATIO = 0.5
LEVEL_HIGH_RATIO = 2.0
ABSURD_MOVE_PCT = 0.30
RISK_MIN = 2.0
RISK_MAX = 200.0
REENTRY_WINDOW_MIN = 90
TOP_CONTRIB_FRACTION = 0.10

HIGH_RISK_CATS = {"manual_loss", "original_stop_loss", "stop_loss", "breakeven",
                  "missed", "unclear", "profit_confirmed_r_unknown"}

PARSE_FLAG_KEYS = ("IMPLAUSIBLE_R", "MALFORMED_LEVEL", "MISSING/ZERO_LEVEL",
                   "STOP_WRONG_SIDE", "ABSURD_TP_DISTANCE", "TINY_RISK", "HUGE_RISK")

_REENTRY_RE = re.compile(
    r"\b(re-?enter|re-?entry|add(?:ing|ed)?\b|layer|layered|dca|scale\s*in|"
    r"second\s+entry|another\s+(?:entry|one)|more\s+(?:longs?|shorts?))\b", re.I)
_RECAP_RE = re.compile(
    r"\b(recap|results?|summary|this\s+(?:week|month)|report\s*card|"
    r"\d+\s*(?:wins?|losses?)|scoreboard|wrap[\s-]*up)\b", re.I)
_OTHER_TICKER_RE = re.compile(
    r"\b(BTC|ETH|SOL|XRP|BNB|ADA|DOGE|AVAX|LINK|LTC|XAG|SILVER|EUR|GBP|JPY|"
    r"NAS|US30|SPX|OIL|WTI)\b", re.I)
_GOLD_RE = re.compile(r"\b(XAU|GOLD)\b", re.I)


def _f(s):
    if s is None:
        return None
    s = str(s).strip().replace(",", "")
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        m = re.search(r"-?\d+\.?\d*", s)
        return float(m.group()) if m else None


def _ro_conn():
    c = sqlite3.connect(f"file:{ARCHIVE_DB}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c


def load_gold(conn):
    """ALL 296 gold signals, with a source tag (signed_off vs backfill)."""
    rows = conn.execute("""
        SELECT s.signal_id, s.sent_at_utc, s.direction, s.entry_low, s.entry_high,
               s.stop, s.tp1, s.tp2, s.tp3, s.source_message_key,
               p.outcome_category, p.calculated_r, p.r_is_known, p.binary_rollup,
               p.primary_evidence_message_key
        FROM signals s LEFT JOIN outcome_projections p ON p.signal_id = s.signal_id
        WHERE s.asset = 'XAUUSD'
        ORDER BY s.sent_at_utc
    """).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["source"] = ("signed_off" if str(r["source_message_key"]).startswith("telegram:baseline:")
                       else "backfill")
        out.append(d)
    return out


def _text_for(conn, message_key):
    if not message_key:
        return ""
    r = conn.execute(
        "SELECT raw_text FROM raw_message_versions WHERE message_key=? "
        "ORDER BY version_number DESC LIMIT 1", (message_key,)).fetchone()
    return (r["raw_text"] if r else "") or ""


def _epoch(s):
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(s).strip(), fmt).replace(tzinfo=timezone.utc).timestamp()
        except (ValueError, TypeError):
            continue
    try:
        d = datetime.fromisoformat(str(s))
        return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).timestamp()
    except (ValueError, TypeError):
        return None


def flag_signal(s, conn, gold_epochs):
    flags = []
    lo, hi = _f(s["entry_low"]), _f(s["entry_high"])
    stop = _f(s["stop"])
    tps = [_f(s["tp1"]), _f(s["tp2"]), _f(s["tp3"])]
    tps_present = [t for t in tps if t is not None]
    entry_mid = (lo + hi) / 2 if (lo is not None and hi is not None) else lo
    rval = _f(s["calculated_r"]) if s["r_is_known"] else None
    direction = (s["direction"] or "").upper()

    # PARSE-ERROR SUSPECTS
    if rval is not None and abs(rval) > R_IMPLAUSIBLE:
        flags.append(f"IMPLAUSIBLE_R({rval:g})")
    if entry_mid in (None, 0) or stop in (None, 0):
        flags.append("MISSING/ZERO_LEVEL")
    if not tps_present:
        flags.append("NO_NUMERICAL_TP")
    if entry_mid:
        for name, v in [("stop", stop), ("tp1", tps[0]), ("tp2", tps[1]), ("tp3", tps[2])]:
            if v is not None and v != 0 and (v < LEVEL_LOW_RATIO * entry_mid
                                             or v > LEVEL_HIGH_RATIO * entry_mid):
                flags.append(f"MALFORMED_LEVEL({name}={v:g})")
        for i, t in enumerate(tps, 1):
            if t is not None and abs(t - entry_mid) / entry_mid > ABSURD_MOVE_PCT:
                flags.append(f"ABSURD_TP_DISTANCE(tp{i}={t:g})")
    if entry_mid and stop:
        if direction in ("LONG", "BUY") and stop >= entry_mid:
            flags.append("STOP_WRONG_SIDE(long stop>=entry)")
        if direction in ("SHORT", "SELL") and stop <= entry_mid:
            flags.append("STOP_WRONG_SIDE(short stop<=entry)")
        risk = abs(entry_mid - stop)
        if risk < RISK_MIN:
            flags.append(f"TINY_RISK(${risk:g})")
        elif risk > RISK_MAX:
            flags.append(f"HUGE_RISK(${risk:g})")

    # HIGH-RISK CATEGORIES
    cat = s["outcome_category"] or ""
    if cat in HIGH_RISK_CATS:
        flags.append(f"HIGH_RISK_CAT({cat})")
    se = _epoch(s["sent_at_utc"])
    if se is not None:
        for oe in gold_epochs:
            if oe is not None and 0 < (se - oe) <= REENTRY_WINDOW_MIN * 60:
                flags.append("REENTRY_CLUSTER")
                break
    if _REENTRY_RE.search(_text_for(conn, s["source_message_key"])):
        flags.append("REENTRY_WORDING")
    ev_text = _text_for(conn, s["primary_evidence_message_key"])
    if ev_text:
        if _RECAP_RE.search(ev_text):
            flags.append("RECAP_EVIDENCE")
        if _OTHER_TICKER_RE.search(ev_text) and not _GOLD_RE.search(ev_text):
            flags.append("CROSS_ASSET_EVIDENCE")
    return flags, ev_text


def run_audit(conn):
    sigs = load_gold(conn)
    gold_epochs = [_epoch(s["sent_at_utc"]) for s in sigs]

    # top-10% positive R contributors (across all gold)
    known_pos = sorted(
        ((float(s["calculated_r"]), s["signal_id"]) for s in sigs
         if s["r_is_known"] and _f(s["calculated_r"]) is not None and float(s["calculated_r"]) > 0),
        reverse=True)
    n_top = max(1, int(len(known_pos) * TOP_CONTRIB_FRACTION)) if known_pos else 0
    top_ids = {sid for _, sid in known_pos[:n_top]}

    results = []
    for s in sigs:
        flags, ev_text = flag_signal(s, conn, gold_epochs)
        rval = _f(s["calculated_r"]) if s["r_is_known"] else None
        if s["signal_id"] in top_ids:
            flags.append(f"TOP_10PCT_CONTRIBUTOR(R={rval:g})")
        results.append({
            "signal_id": s["signal_id"], "date": s["sent_at_utc"], "asset": "XAUUSD",
            "source": s["source"], "direction": (s["direction"] or "").upper(),
            "entry": f"{s['entry_low']}-{s['entry_high']}", "stop": s["stop"],
            "tps": "/".join(str(x) for x in (s["tp1"], s["tp2"], s["tp3"])),
            "outcome": s["outcome_category"],
            "R": s["calculated_r"] if s["r_is_known"] else "(unknown)",
            "r_is_known": bool(s["r_is_known"]),
            "binary": s["binary_rollup"],
            "evidence": (ev_text[:160].replace("\n", " ") if ev_text else ""),
            "flags": flags, "why": "; ".join(flags),
        })
    return results, n_top


def _agg(rows):
    rs = [float(r["R"]) for r in rows if r["r_is_known"] and r["R"] not in (None, "(unknown)")]
    if not rs:
        return {"n": 0, "mean": None, "median": None}
    return {"n": len(rs), "mean": round(statistics.mean(rs), 4),
            "median": round(statistics.median(rs), 4)}


def freeze_record(results):
    rec = {
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Freeze audit mechanics BEFORE interpreting any aggregate.",
        "detector_version": archive.DETECTOR_VERSION,
        "parser_version": archive.PARSER_VERSION,
        "calc_version": archive.CALC_VERSION,
        "code_version": archive.CODE_VERSION,
        "shadow_config_version": shadow_config.CONFIG_VERSION,
        "shadow_config_hash": shadow_config.config_hash(),
        "master_seed": MASTER_SEED,
        "gold_denominator": len(results),
        "gold_signed_off": sum(1 for r in results if r["source"] == "signed_off"),
        "gold_backfill": sum(1 for r in results if r["source"] == "backfill"),
        "flag_thresholds": {
            "R_IMPLAUSIBLE": R_IMPLAUSIBLE, "LEVEL_LOW_RATIO": LEVEL_LOW_RATIO,
            "LEVEL_HIGH_RATIO": LEVEL_HIGH_RATIO, "ABSURD_MOVE_PCT": ABSURD_MOVE_PCT,
            "RISK_MIN": RISK_MIN, "RISK_MAX": RISK_MAX,
            "REENTRY_WINDOW_MIN": REENTRY_WINDOW_MIN,
            "TOP_CONTRIB_FRACTION": TOP_CONTRIB_FRACTION,
            "HIGH_RISK_CATS": sorted(HIGH_RISK_CATS),
        },
    }
    return rec


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    os.makedirs(AUDIT_DIR, exist_ok=True)
    conn = _ro_conn()
    results, n_top = run_audit(conn)
    conn.close()

    # ---- 1. FREEZE & RECORD (before interpretation) ----
    freeze = freeze_record(results)
    with open(os.path.join(AUDIT_DIR, "freeze.json"), "w", encoding="utf-8") as f:
        json.dump(freeze, f, indent=2)

    # ---- 2. UNCORRECTED BASELINE (raw, includes parse errors; NOT trusted) ----
    raw_all = _agg(results)
    raw_bf = _agg([r for r in results if r["source"] == "backfill"])
    raw_so = _agg([r for r in results if r["source"] == "signed_off"])
    uncorrected = [
        "UNCORRECTED BASELINE — DO NOT TRUST",
        "Raw aggregate over ALL gold known-R signals, INCLUDING known parse errors",
        "(e.g. the +221.63R outlier). Preserved verbatim so later corrected numbers",
        "can be compared against the naive starting point. No flagging applied here.",
        f"frozen_at_utc: {freeze['frozen_at_utc']}",
        f"detector={freeze['detector_version']} parser={freeze['parser_version']} "
        f"calc={freeze['calc_version']} shadow_cfg={freeze['shadow_config_hash'][:12]}",
        "",
        f"GOLD denominator: {freeze['gold_denominator']} "
        f"(signed_off={freeze['gold_signed_off']} + backfill={freeze['gold_backfill']})",
        f"ALL gold known-R   : n={raw_all['n']} mean={raw_all['mean']} median={raw_all['median']}",
        f"backfill known-R   : n={raw_bf['n']} mean={raw_bf['mean']} median={raw_bf['median']}",
        f"signed_off known-R : n={raw_so['n']} mean={raw_so['mean']} median={raw_so['median']}",
    ]
    with open(os.path.join(AUDIT_DIR, "uncorrected_baseline.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(uncorrected) + "\n")

    # ---- 3/4. FLAGGING + AGGREGATES ----
    flagged = [r for r in results if r["flags"]]
    clean = [r for r in results if not r["flags"]]
    all_agg = _agg(results)
    clean_agg = _agg(clean)
    flagged_agg = _agg(flagged)

    # ---- 5. FULL GOLD AUDIT CSV (all 296) ----
    full_csv = os.path.join(AUDIT_DIR, "gold_audit_full.csv")
    with open(full_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["signal_id", "date", "asset", "source", "direction", "entry", "stop",
                    "tps", "outcome", "R", "r_is_known", "binary", "flagged", "why", "evidence"])
        for r in results:
            w.writerow([r["signal_id"], r["date"], r["asset"], r["source"], r["direction"],
                        r["entry"], r["stop"], r["tps"], r["outcome"], r["R"], r["r_is_known"],
                        r["binary"], bool(r["flags"]), r["why"], r["evidence"]])

    # flag tally
    tally = {}
    for r in flagged:
        for fl in r["flags"]:
            k = fl.split("(")[0]
            tally[k] = tally.get(k, 0) + 1
    parse_suspects = [r for r in flagged
                      if any(any(p in fl for p in PARSE_FLAG_KEYS) for fl in r["flags"])]

    # ---- report ----
    print("=" * 88)
    print("  GOLD ARCHIVE VALIDATION — FROZEN AUDIT (read-only, advisory, NO scoring changed)")
    print("=" * 88)
    print(f"  FROZEN: detector={freeze['detector_version']}  parser={freeze['parser_version']}  "
          f"calc={freeze['calc_version']}  shadow_cfg={freeze['shadow_config_hash'][:12]}  "
          f"seed={MASTER_SEED}")
    print(f"  GOLD DENOMINATOR: {freeze['gold_denominator']}  "
          f"(signed_off={freeze['gold_signed_off']} + backfill={freeze['gold_backfill']})  "
          f"[silver/crypto/forex NOT included]")
    print("  " + "-" * 84)
    print("  UNCORRECTED BASELINE (raw, includes parse errors — NOT trusted):")
    print(f"    ALL gold known-R : n={raw_all['n']} mean={raw_all['mean']} median={raw_all['median']}")
    print("  " + "-" * 84)
    print(f"  FLAGGED (>=1 reason): {len(flagged)} / {len(results)}    CLEAN: {len(clean)} / {len(results)}")
    bf = [r for r in results if r['source'] == 'backfill']
    bf_flagged = sum(1 for r in bf if r['flags'])
    print(f"    of backfill (269): flagged={bf_flagged} clean={len(bf)-bf_flagged}")
    so = [r for r in results if r['source'] == 'signed_off']
    so_flagged = sum(1 for r in so if r['flags'])
    print(f"    of signed_off (27): flagged={so_flagged} clean={len(so)-so_flagged}")
    print("  " + "-" * 84)
    print("  AGGREGATE R (gold known-R; mean is outlier-sensitive, median resists):")
    print(f"    ALL gold        : n={all_agg['n']:3d}  mean={all_agg['mean']}  median={all_agg['median']}")
    print(f"    WITHOUT flagged : n={clean_agg['n']:3d}  mean={clean_agg['mean']}  median={clean_agg['median']}")
    print(f"    flagged only    : n={flagged_agg['n']:3d}  mean={flagged_agg['mean']}  median={flagged_agg['median']}")
    print("  " + "-" * 84)
    print("  FLAG TALLY (signals per reason):")
    for k, v in sorted(tally.items(), key=lambda x: -x[1]):
        print(f"    {k:28} {v}")
    print("  " + "-" * 84)
    print(f"  PARSE-ERROR SUSPECTS: {len(parse_suspects)} (verify first). Worst by |R|:")
    def absr(r):
        return abs(float(r["R"])) if r["r_is_known"] and r["R"] not in (None, "(unknown)") else 0
    for r in sorted(parse_suspects, key=absr, reverse=True)[:12]:
        print(f"    {r['date'][:16]} {r['direction']:5} {r['entry']:>14} sl={str(r['stop']):>7} "
              f"tp={r['tps']:>18} {str(r['outcome'])[:20]:20} R={str(r['R']):>8} | {r['why'][:70]}")
    print("  " + "-" * 84)
    print("  ARTIFACTS:")
    print(f"    freeze record       : {os.path.join(AUDIT_DIR, 'freeze.json')}")
    print(f"    uncorrected baseline: {os.path.join(AUDIT_DIR, 'uncorrected_baseline.txt')}")
    print(f"    full gold audit CSV : {full_csv}  ({len(results)} rows)")
    print("=" * 88)
    print("  DIAGNOSTIC ONLY — no scoring changed; signed-off 28 + LIVE stub untouched.")
    print("=" * 88)


if __name__ == "__main__":
    main()
