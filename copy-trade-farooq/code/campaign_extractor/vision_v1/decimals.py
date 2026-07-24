"""
Raw-string / decimal handling. Preserves the raw visible string separately from any parsed
candidate; accepted value always NULL. Ambiguous decimal/separator meaning -> AMBIGUOUS_DIGITS
with all plausible readings retained. NEVER infers formatting from expected BTC/Gold price ranges.
"""
from __future__ import annotations


def normalise_for_compare(field_type, s):
    if s is None:
        return None
    t = str(s).strip()
    if field_type in ("INSTRUMENT", "DIRECTION", "MANAGEMENT_INSTRUCTION", "COMMENTARY_TEXT"):
        return "".join(ch for ch in t.upper() if ch.isalnum())
    return "".join(ch for ch in t if ch.isdigit() or ch in ".,+-")   # numeric-ish


def parse_numeric(raw):
    """Return (parsed_candidate_string_or_None, status, plausible_readings). accepted stays NULL."""
    if raw is None:
        return None, "AMBIGUOUS_DIGITS", []
    s = str(raw).strip().replace(" ", "")
    if not s:
        return None, "AMBIGUOUS_DIGITS", []
    sign = ""
    if s[0] in "+-":
        sign, s = s[0], s[1:]
    if not s:
        return None, "AMBIGUOUS_DIGITS", [raw]
    has_c, has_p = "," in s, "." in s
    body = "".join(ch for ch in s if ch.isdigit() or ch in ".,")
    if not any(ch.isdigit() for ch in body):
        return None, "AMBIGUOUS_DIGITS", [raw]
    if has_c and has_p:
        if s.rfind(".") > s.rfind(","):                # 58,585.70 -> comma thousands, dot decimal
            return sign + s.replace(",", ""), "PARSED", [sign + s.replace(",", "")]
        # 58.585,70 -> ambiguous (EU vs US)
        return None, "AMBIGUOUS_DIGITS", [sign + s.replace(".", "").replace(",", "."),
                                          sign + s.replace(",", "")]
    if has_c and not has_p:                            # comma alone -> decimal or thousands? unclear
        return None, "AMBIGUOUS_DIGITS", [sign + s.replace(",", ""), sign + s.replace(",", ".")]
    if has_p and not has_c:
        if s.count(".") > 1:
            return None, "AMBIGUOUS_DIGITS", [raw]
        return sign + s, "PARSED", [sign + s]          # single dot -> decimal
    if s.isdigit():
        return sign + s, "PARSED", [sign + s]
    return None, "AMBIGUOUS_DIGITS", [raw]
