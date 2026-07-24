"""
audit.py — the audit trail (the machine's black box).

A PERMANENT, APPEND-ONLY record of every decision the pipeline makes. Each signal
that flows through the pipeline writes exactly ONE entry recording its whole
journey: what came in, what was decided at each stage (parse, confirm, route,
circuit breaker, sizing), and the final outcome (logged, or stopped and why).

    * Entries are written one-per-line as JSON to audit_log.jsonl (JSON Lines).
    * Writing is APPEND-ONLY. This file never overwrites and never deletes — it
      only ever adds. THE AUDIT LOG IS IMMUTABLE: do not edit it by hand.
    * It is read-only with respect to your paper_log.csv — it touches only its
      own file.

Why it exists: months from now you'll want to ask "why did the machine reject
that one in March?" or "what exactly happened the day the circuit breaker fired?"
The audit trail answers, because a serious system can always show its working.

View the most recent decisions:

    python audit.py            # last 20 entries, most recent first
    python audit.py 50         # last 50

PAPER MODE. No execution. Nothing here places an order or touches the LIVE stub.
"""

import json
import os
from datetime import datetime, timezone
from decimal import Decimal

import config


def _s(value):
    """JSON-safe scalar: Decimal/None -> str/None, leave the rest."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return str(value)
    return value


# ----------------------------------------------------------------------------
# Building one record as the pipeline progresses
# ----------------------------------------------------------------------------
class AuditRecord:
    """
    Accumulates one signal's journey, stage by stage. The pipeline fills it in as
    it goes, then writes it exactly once (success or stop) via audit.record().
    """

    def __init__(self, raw_signal: str = "", channel: str = ""):
        self.data = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "raw_signal": raw_signal or "",
            "channel": channel or "",
            "parse": None,
            "confirm": None,
            "route": None,
            "circuit_breaker": None,
            "sizing": None,
            "result": {"status": "INCOMPLETE", "detail": "pipeline did not finish"},
        }

    # --- stage setters ------------------------------------------------------
    @classmethod
    def from_signal(cls, signal, channel: str = ""):
        rec = cls(raw_signal=getattr(signal, "raw_text", "") or "", channel=channel)
        rec.data["parse"] = {
            "ticker": getattr(signal, "ticker", ""),
            "pair": getattr(signal, "pair", ""),
            "direction": getattr(signal, "direction", ""),
            "asset_class": getattr(signal, "asset_class", ""),
            "entry_low": _s(getattr(signal, "entry_low", None)),
            "entry_high": _s(getattr(signal, "entry_high", None)),
            "stop_loss": _s(getattr(signal, "stop_loss", None)),
            "targets": [_s(t) for t in getattr(signal, "targets", [])],
            "source": getattr(signal, "source", ""),
        }
        return rec

    def parse_failed(self, raw_signal: str, error: str):
        self.data["raw_signal"] = raw_signal or ""
        self.data["parse"] = {"error": str(error)}
        self.data["result"] = {"status": "STOPPED", "stage": "PARSE", "detail": str(error)}
        return self

    def confirm(self, yes: bool):
        self.data["confirm"] = "yes" if yes else "no"
        return self

    def route(self, decision):
        self.data["route"] = {
            "asset_class": getattr(decision, "asset_class", ""),
            "trader": getattr(decision, "trader", ""),
            "venue": getattr(decision, "venue", ""),
            "bucket": getattr(decision, "bucket", ""),
            "confidence": getattr(decision, "confidence", ""),
            "review_reasons": list(getattr(decision, "review_reasons", []) or []),
        }
        return self

    def circuit_breaker(self, decision):
        self.data["circuit_breaker"] = {
            "verdict": "blocked" if getattr(decision, "blocked", False) else "pass",
            "reason": getattr(decision, "block_reason", "") or "",
            "warnings": list(getattr(decision, "warnings", []) or []),
            "lines": list(getattr(decision, "lines", []) or []),
        }
        return self

    def sizing(self, ticket):
        self.data["sizing"] = {
            "lots": _s(getattr(ticket, "lots", None)),
            "entry": _s(getattr(ticket, "sizing_entry", None)),
            "raw_entry": _s(getattr(ticket, "raw_entry", None)),
            "slippage": _s(getattr(ticket, "slippage", None)),
            "stop": _s(getattr(ticket, "stop_loss", None)),
            "cash_at_risk": _s(getattr(ticket, "cash_at_risk", None)),
            "dollar_risk": _s(getattr(ticket, "dollar_risk", None)),
            "rr_first_target": _s(getattr(ticket, "rr_first_target", None)),
        }
        return self

    def sizing_rejected(self, reason: str):
        self.data["sizing"] = {"rejected": str(reason)}
        return self

    def result_logged(self, log_path: str):
        self.data["result"] = {"status": "LOGGED", "log_path": log_path or ""}
        return self

    def result_stopped(self, stage: str, reason: str):
        self.data["result"] = {"status": "STOPPED", "stage": stage, "detail": str(reason)}
        return self

    def result_other(self, status: str, detail: str = ""):
        self.data["result"] = {"status": status, "detail": detail}
        return self

    def to_dict(self) -> dict:
        return self.data


# ----------------------------------------------------------------------------
# The one writer — APPEND ONLY
# ----------------------------------------------------------------------------
def record(entry, path: str = None) -> str:
    """
    Append ONE audit entry (an AuditRecord or a plain dict) as a JSON line.

    APPEND-ONLY by construction: the file is opened in 'a' mode, so this can only
    ever add a line — it cannot overwrite or delete existing history.
    """
    path = path or config.AUDIT_LOG_FILE
    data = entry.to_dict() if isinstance(entry, AuditRecord) else dict(entry)
    if "ts" not in data:
        data["ts"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")
    return path


# ----------------------------------------------------------------------------
# The viewer (read-only)
# ----------------------------------------------------------------------------
def load_entries(path: str = None) -> list:
    """Read all audit entries (oldest first). Skips any unreadable line, loudly-safe."""
    path = path or config.AUDIT_LOG_FILE
    entries = []
    if not os.path.exists(path):
        return entries
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                entries.append({"_unreadable": line})
    return entries


def _round(value, places: str = "0.01") -> str:
    """Round a stored (string) number for display; leave it as-is if unparseable."""
    try:
        return str(Decimal(str(value)).quantize(Decimal(places)))
    except Exception:
        return str(value)


def _ts_local(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return iso or "?"


def _format_entry(e: dict) -> list:
    if "_unreadable" in e:
        return ["  [unreadable audit line]"]

    parse = e.get("parse") or {}
    route = e.get("route") or {}
    cb = e.get("circuit_breaker") or {}
    sizing = e.get("sizing") or {}
    result = e.get("result") or {}

    headline = f"{parse.get('ticker', '?')} {parse.get('direction', '')}".strip() or "(unparsed)"
    status = result.get("status", "?")
    tail = ""
    if status == "STOPPED":
        tail = f"  (stopped at {result.get('stage', '?')})"

    lines = [f"[{_ts_local(e.get('ts'))}]  {headline}  ->  {status}{tail}"]

    raw = (e.get("raw_signal") or "").replace("\n", " ").strip()
    if raw:
        lines.append(f"   raw     : {raw[:80]}{'...' if len(raw) > 80 else ''}")

    if "error" in parse:
        lines.append(f"   parse   : FAILED — {parse['error']}")
    elif parse:
        tps = "/".join(str(t) for t in parse.get("targets", [])) or "none"
        lines.append(f"   parse   : {parse.get('ticker','?')} {parse.get('direction','')}  "
                     f"zone {parse.get('entry_low','?')}-{parse.get('entry_high','?')}  "
                     f"SL {parse.get('stop_loss','?')}  TPs {tps}")

    if e.get("confirm") is not None:
        lines.append(f"   confirm : {e['confirm']}")

    if route:
        rr = route.get("review_reasons") or []
        extra = f"  reasons: {'; '.join(rr)}" if rr else ""
        lines.append(f"   route   : {route.get('asset_class','?')} / "
                     f"{route.get('trader','?')} / {route.get('venue','?')}  "
                     f"({route.get('bucket','?')}){extra}")

    if cb:
        reason = cb.get("reason") or ""
        warns = cb.get("warnings") or []
        bits = []
        if reason:
            bits.append(reason)
        if warns:
            bits.append("; ".join(warns))
        suffix = f"  {' | '.join(bits)}" if bits else ""
        lines.append(f"   breaker : {cb.get('verdict','?')}{suffix}")

    if sizing:
        if "rejected" in sizing:
            lines.append(f"   sizing  : REJECTED — {sizing['rejected']}")
        else:
            lines.append(f"   sizing  : {sizing.get('lots','?')} lot @ {sizing.get('entry','?')}  "
                         f"risk {config.CURRENCY}{_round(sizing.get('cash_at_risk'))}  "
                         f"R:R {_round(sizing.get('rr_first_target'))}")

    if status == "LOGGED":
        lines.append(f"   result  : LOGGED -> {result.get('log_path','')}")
    elif status == "STOPPED":
        lines.append(f"   result  : STOPPED — {result.get('detail','')}")
    else:
        lines.append(f"   result  : {status}")

    return lines


def view(limit: int = 20, path: str = None) -> str:
    entries = load_entries(path)
    out = []
    out.append("=" * 64)
    out.append("   AUDIT TRAIL — the machine's decision history  (most recent first)")
    out.append("=" * 64)
    if not entries:
        out.append("\n  No audit entries yet. Run a signal through  python pipeline.py.\n")
        out.append("=" * 64)
        return "\n".join(out)

    total = len(entries)
    shown = entries[-limit:][::-1]    # last `limit`, most recent first
    out.append(f"  Showing {len(shown)} of {total} entries.  "
               "(Append-only, permanent — never edited by hand.)")
    for e in shown:
        out.append("")
        out.extend(_format_entry(e))
    out.append("")
    out.append("=" * 64)
    return "\n".join(out)


def main():
    import sys
    limit = 20
    args = [a for a in sys.argv[1:] if a.strip()]
    if args and args[0].isdigit():
        limit = int(args[0])
    print(view(limit=limit))


if __name__ == "__main__":
    main()
