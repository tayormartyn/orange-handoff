"""
OCR proposal adapter (PURE, no OCR dependency here). Given an OCR result (lines of text with
optional boxes/confidence), it PROPOSES a semantic class and trade fields, each with a confidence
tier (HIGH/MEDIUM/LOW), a source snippet, a region reference, and a reason. It NEVER creates a
review, UnifiedSignal, paper observation, cohort count or alert, and it NEVER auto-verifies a
provider — proposals are advisory and must pass the existing explicit human-confirmation route.

The live OCR itself runs in ocr_runner.py under .venv-vision (RapidOCR); this module is the pure,
fully-testable proposal logic (synthetic OCR text in tests). No hard-coded per-format bounding boxes.
"""
from __future__ import annotations
import re

GOLD_SYMS = ("XAUUSD", "XAU/USD", "XAU USD", "GOLD", "XAU")
KNOWN_SYMS = GOLD_SYMS + ("BTCUSD", "BTC/USD", "BITCOIN", "BTC", "ETHUSD", "ETH", "XAGUSD", "SILVER")
DIRECTIONS = {"BUY": "BUY", "SELL": "SELL", "LONG": "BUY", "SHORT": "SELL"}
RESULT_KWS = ("p&l", "pnl", "p & l", "profit:", "net profit", "booked", "closed in profit",
              "final result", "result:", "total pips", "stopped out", "closed +", "closed -", "loss:")
UPDATE_KWS = ("move sl", "sl to entry", "stop to entry", "sl to be", "sl to breakeven", "to breakeven",
              "break even", "breakeven", "tp1 secured", "tp1 hit", "tp1 reached", "tp2 reached",
              "tp2 hit", "tp3 hit", "take more profit", "take some profit", "secure profit",
              "bank profit", "take partial", "close partial", "partial close", "reduce position",
              "take one out", "close worst entry", "hold best entry", "hold runner", "still holding",
              "holding", "next target", "recovery mode", "move stop", "trail stop")
NONSIGNAL_KWS = ("looking for", "waiting for", "possible entry", "if we get", "watching for",
                 "potential entry", "planning", "might enter")
PROVIDER_TOKENS = ("seascalperfarouk", "sea scalper", "seascalper", "farouk", "@whale", "whale")

_NUM = r"[0-9OoIl]{1,7}(?:[.,][0-9OoIl]{1,5})?"
_AMBIG = re.compile(r"[OoIl?]")


def _clean_number(tok):
    """(value_str_or_None, ambiguous_bool). Ambiguous glyphs (O/l/I/?) are NOT silently accepted."""
    if tok is None:
        return None, False
    t = tok.strip().rstrip(".,")
    if _AMBIG.search(t):
        return None, True                          # AMBIGUOUS_DIGITS -> never guessed
    t = t.replace(",", "")
    return (t if re.fullmatch(r"\d+(?:\.\d+)?", t) else None), False


def _field(value, confidence, snippet=None, region=None, reason=None, candidate=None):
    # LOW confidence -> leave value blank but keep the candidate visible separately
    if confidence == "LOW":
        return {"value": None, "confidence": "LOW", "candidate": candidate, "snippet": snippet,
                "region": region, "reason": reason or "LOW_CONFIDENCE"}
    return {"value": value, "confidence": confidence, "candidate": candidate or value,
            "snippet": snippet, "region": region, "reason": reason}


def _find(lines, needle):
    n = needle.lower()
    for ln in lines:
        if n in (ln.get("text") or "").lower():
            return ln.get("text"), ln.get("box")
    return None, None


def _first_num_after(text, labels):
    for lab in labels:
        m = re.search(re.escape(lab) + r"[^0-9OoIl]{0,6}(" + _NUM + r")", text, re.I)
        if m:
            return m.group(1)
    return None


def _compact(s):
    """alphanumeric-only lower form, so OCR that drops spaces ('takemoreprofit') still matches."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


RESULT_CARD_CUES = ("profit", "p&l", "pnl", "closed", "history", "deal", "balance")
_PRICE_PAIR = re.compile(r"(\d{3,5}(?:\.\d{1,2})?)\s*(?:->|→|to)\s*(\d{3,5}(?:\.\d{1,2})?)")
_LEG = re.compile(r"\b(buy|sell)\b\s*(\d)?", re.I)
# a standalone monetary/P&L value: optional currency/sign, optional space/comma thousands, 2 decimals
_MONEY = re.compile(r"(?:[£$]\s?|\+\s?)?(\d{1,3}(?:[ ,]\d{3})+\.\d{2}|\d{3,7}\.\d{2})")


def _norm_money(s):
    return s.replace("£", "").replace("$", "").replace("+", "").replace(" ", "").replace(",", "").strip()


def result_card(full_text):
    """Detect a COMPLETED MT4/MT5-style result card: instrument + direction/leg + entry->exit price
    pair + a STANDALONE money value distinct from the pair. Returns a dict or None. A bare price pair
    alone or a bare money value alone never qualifies."""
    t = full_text
    if not re.search(r"xau|gold", t, re.I):
        return None
    leg = _LEG.search(t)
    if not leg:
        return None
    pair = _PRICE_PAIR.search(t)
    if not pair:
        return None
    a, b = pair.group(1), pair.group(2)
    money = None
    for m in _MONEY.finditer(t):
        norm = _norm_money(m.group(1))
        if norm in (_norm_money(a), _norm_money(b)):
            continue                                    # skip the entry/exit prices themselves
        money = norm
        break
    if money is None:
        return None
    return {"direction": leg.group(1).upper(),
            "leg": (leg.group(1).upper() + "_" + leg.group(2)) if leg.group(2) else None,
            "entry": a, "exit": b, "profit": money}


def classify(full_text, lines):
    t = full_text.lower()
    tc = _compact(t)
    res = next((k for k in RESULT_KWS if k in t), None)   # exact: result punctuation is meaningful
    if res and re.search(r"[-+$]?\s*" + _NUM, t):
        return "TRADE_RESULT", "HIGH", res
    # management wording (tolerant of dropped spaces) marks an IN-FLIGHT update — checked before the
    # completed-result card so "take profit"/"move SL" stay TRADE_UPDATE (not a finished result).
    upd = next((k for k in UPDATE_KWS if k in t or _compact(k) in tc), None)
    card = result_card(full_text) if not upd else None
    if card:                                            # completed result card overrides weak SIGNAL
        return "TRADE_RESULT", "HIGH", "completed_result_card"
    if upd:
        return "TRADE_UPDATE", "HIGH", upd
    nonsig = next((k for k in NONSIGNAL_KWS if k in t), None)
    has_instr = any(s.lower() in t for s in KNOWN_SYMS)
    has_dir = any(re.search(r"\b" + d.lower() + r"\b", t) for d in DIRECTIONS)
    has_price = re.search(r"\b\d{2,6}(?:[.,]\d{1,5})?\b", t) is not None
    has_levels = any(w in t for w in ("sl", "stop", "tp", "target", "entry"))
    if has_instr and has_dir and has_price and has_levels and not nonsig:
        strong = ("sl" in t or "stop" in t) and ("tp" in t or "target" in t)
        return "SIGNAL", ("HIGH" if strong else "MEDIUM"), "instrument+direction+entry+levels"
    if nonsig:
        return "UNKNOWN", "MEDIUM", f"non-actionable intent: '{nonsig}'"
    return "UNKNOWN", "LOW", "no clear signal/update/result pattern"


def propose(ocr_result):
    """ocr_result = {'lines':[{'text','box','conf'}...], 'full_text': str} -> proposals dict."""
    lines = ocr_result.get("lines") or []
    full = ocr_result.get("full_text") or "\n".join((l.get("text") or "") for l in lines)
    tl = full.lower()
    cls, cconf, csnip = classify(full, lines)

    # instrument
    instr = next((s for s in KNOWN_SYMS if s.lower() in tl), None)
    instr_norm = "XAUUSD" if instr in GOLD_SYMS else ("BTCUSD" if instr in ("BTCUSD", "BTC/USD", "BITCOIN", "BTC") else instr)
    isnip, ibox = (_find(lines, instr) if instr else (None, None))
    f_instr = _field(instr_norm, "HIGH" if instr else "LOW", isnip, ibox,
                     None if instr else "no_recognised_symbol", candidate=instr)

    # direction
    dkey = next((d for d in DIRECTIONS if re.search(r"\b" + d.lower() + r"\b", tl)), None)
    dsnip, dbox = (_find(lines, dkey) if dkey else (None, None))
    f_dir = _field(DIRECTIONS.get(dkey), "HIGH" if dkey else "LOW", dsnip, dbox,
                   None if dkey else "no_direction_token", candidate=dkey)

    # entry (range or single)
    entry_low = entry_high = None
    e_amb = False
    rng = re.search(r"(" + _NUM + r")\s*[-/]\s*(" + _NUM + r")", full)
    if rng:
        lo, a1 = _clean_number(rng.group(1))
        hi, a2 = _clean_number(rng.group(2))
        entry_low, entry_high, e_amb = lo, hi, (a1 or a2)
    else:
        single = _first_num_after(full, ("entry", "buy", "sell", "@"))
        entry_low, e_amb = _clean_number(single)
        entry_high = entry_low
    esnip, ebox = _find(lines, "entry")
    if e_amb:
        f_entry_low = _field(None, "LOW", esnip, ebox, "AMBIGUOUS_DIGITS", candidate=(rng.group(1) if rng else None))
        f_entry_high = _field(None, "LOW", esnip, ebox, "AMBIGUOUS_DIGITS", candidate=(rng.group(2) if rng else None))
    else:
        conf = "HIGH" if (entry_low and (esnip or rng)) else ("MEDIUM" if entry_low else "LOW")
        f_entry_low = _field(entry_low, conf, esnip, ebox, None if entry_low else "no_entry_found")
        f_entry_high = _field(entry_high, conf, esnip, ebox, None if entry_high else "no_entry_found")

    # stop
    st_raw = _first_num_after(full, ("sl", "stop loss", "stop", "s/l"))
    st_val, st_amb = _clean_number(st_raw)
    ssnip, sbox = _find(lines, "sl") if "sl" in tl else _find(lines, "stop")
    f_stop = (_field(None, "LOW", ssnip, sbox, "AMBIGUOUS_DIGITS", candidate=st_raw) if st_amb
              else _field(st_val, "HIGH" if st_val else "LOW", ssnip, sbox,
                          None if st_val else "no_stop_found"))

    # targets
    tps = []
    for m in re.finditer(r"(?:tp\s*\d?|target)\s*[:=]?\s*(" + _NUM + r")", full, re.I):
        v, amb = _clean_number(m.group(1))
        if v and not amb:
            tps.append(v)
    tsnip, tbox = _find(lines, "tp")
    f_targets = _field(", ".join(tps) if tps else None, "HIGH" if tps else "LOW", tsnip, tbox,
                       None if tps else "no_targets_found")

    # quantity / result / provider candidate / post time
    qty = _first_num_after(full, ("lot", "lots", "qty", "size", "volume"))
    qv, _ = _clean_number(qty)
    f_qty = _field(qv, "MEDIUM" if qv else "LOW", *(_find(lines, "lot")), reason=None if qv else "no_quantity")
    pnl = _first_num_after(full, ("p&l", "pnl", "profit", "$", "result"))
    pv, _ = _clean_number(pnl)
    f_result = _field(pv, "MEDIUM" if pv else "LOW", *(_find(lines, "profit")), reason=None if pv else "no_result")
    prov = next((p for p in PROVIDER_TOKENS if p in tl), None)
    psnip, pbox = (_find(lines, prov) if prov else (None, None))
    # PROVIDER IS A CANDIDATE ONLY — never a verification. Verification needs attestation elsewhere.
    f_provider = {"candidate": prov, "confidence": "MEDIUM" if prov else "LOW", "snippet": psnip,
                  "region": pbox, "verification_state": "PROVIDER_UNVERIFIED",
                  "reason": "OCR name is not proof — requires evidence + provenance + explicit attestation"}
    tm = re.search(r"\b([01]?\d|2[0-3]):[0-5]\d\b", full)
    f_time = _field(tm.group(0) if tm else None, "MEDIUM" if tm else "LOW",
                    (_find(lines, tm.group(0))[0] if tm else None), None,
                    "time shown without date/timezone is not verifiable" if tm else "no_time")

    out = {
        "note": "OCR PROPOSAL ONLY — advisory. No review/UnifiedSignal/observation/cohort/alert is "
                "created here; explicit human confirmation is still required. Provider NOT auto-verified.",
        "classification": {"value": cls, "confidence": cconf, "snippet": csnip,
                           "reason": ("proposed from: " + str(csnip)) if csnip else "no clear pattern"},
        "fields": {"instrument": f_instr, "direction": f_dir, "entry_low": f_entry_low,
                   "entry_high": f_entry_high, "stop_price": f_stop, "target_prices": f_targets,
                   "quantity": f_qty, "result_pnl": f_result, "post_time": f_time},
        "provider_candidate": f_provider,
        "full_text": full,
    }
    # enrich a completed result-card classification (advisory candidates + non-actionable flags)
    if cls == "TRADE_RESULT" and csnip == "completed_result_card":
        rc = result_card(full)
        if rc:
            out["intent"] = "COMPLETED_TRADE_RESULT"
            out["result_card"] = {
                "instrument": instr_norm or "XAUUSD", "direction": rc["direction"],
                "provider_leg_candidate": rc["leg"], "entry_candidate": float(rc["entry"]),
                "exit_candidate": float(rc["exit"]), "reported_profit_candidate": float(rc["profit"])}
            out["flags"] = ["HISTORICAL_RESULT_CARD", "NOT_ACTIONABLE_SIGNAL", "REPLAY_VALIDATION_ONLY"]
    return out
