"""
Safe OCR normalization with raw-evidence preservation and MATERIAL-CHANGE detection. Harmless changes
(unicode arrows, whitespace, casing, S1->SL label, money thousands separators) are applied silently.
An economically MATERIAL number change (decimal moved/removed, digit substituted, magnitude change) is
NEVER silently repaired — it is surfaced as CONFIRMATION_REQUIRED.
"""
from __future__ import annotations
import re

_ARROWS = {"→": "->", "➔": "->", "➡": "->", "⮕": "->", "→": "->"}
_OCR_SUBS = {"O": "0", "o": "0", "l": "1", "I": "1", "S": "5", "B": "8"}   # only for MATERIAL comparison


def normalize(raw):
    """Return {normalized_text, normalizations_applied[]}. Harmless-only."""
    applied = []
    t = raw or ""
    for a, rep in _ARROWS.items():
        if a in t:
            t = t.replace(a, rep); applied.append(f"arrow '{a}'->'->'")
    if re.search(r"\bS1\b", t):                          # S1 mis-OCR of SL (label only)
        t = re.sub(r"\bS1\b", "SL", t); applied.append("label S1->SL")
    # money thousands separators inside a value: "1,518.00" / "1 518.00" -> "1518.00"
    def _money(m):
        applied.append(f"money '{m.group(0)}'->'{m.group(0).replace(',', '').replace(' ', '')}'")
        return m.group(0).replace(",", "").replace(" ", "")
    t = re.sub(r"\d{1,3}(?:[ ,]\d{3})+(?:\.\d{1,2})?", _money, t)
    # collapse whitespace / casing is harmless (kept for display; not asserted material)
    t2 = re.sub(r"\s+", " ", t).strip()
    if t2 != t:
        applied.append("whitespace")
    return {"normalized_text": t2, "normalizations_applied": applied}


def material_number_change(raw_value, normalized_value):
    """Compare a raw vs normalized numeric token. Returns a decision dict. A change in the numeric
    VALUE (not just formatting) is MATERIAL and requires confirmation."""
    def _num(s):
        try:
            return float(re.sub(r"[^0-9.]", "", str(s)))
        except Exception:
            return None
    rv, nv = _num(raw_value), _num(normalized_value)
    material = False
    reason = None
    if rv is None or nv is None:
        material = True; reason = "UNPARSEABLE_NUMBER"
    elif abs(rv - nv) > 1e-9:
        # a genuine value change (decimal moved, digit substituted, magnitude) is material
        material = True
        reason = ("DECIMAL_OR_MAGNITUDE_CHANGE" if abs(rv - nv) / max(abs(rv), 1e-9) > 0.001
                  else "SMALL_NUMERIC_CHANGE")
    return {"raw_value": raw_value, "normalized_candidate": normalized_value,
            "material_change": material, "confirmation_required": material, "reason": reason}


def scan_material_corrections(raw, normalized):
    """Extract numeric tokens from raw vs normalized and flag any that changed value. Digit-substitution
    (O/l/I/S/B) or decimal shifts in an entry/stop/price are material -> confirmation required."""
    raw_nums = re.findall(r"\d+(?:\.\d+)?", raw or "")
    norm_nums = re.findall(r"\d+(?:\.\d+)?", normalized or "")
    corrections = []
    for r, n in zip(raw_nums, norm_nums):
        if r != n and _num_val(r) != _num_val(n):
            corrections.append(material_number_change(r, n))
    return {"material_corrections": [c for c in corrections if c["material_change"]],
            "any_material": any(c["material_change"] for c in corrections),
            "confirmation_required": any(c["confirmation_required"] for c in corrections)}


def _num_val(s):
    try:
        return float(s)
    except Exception:
        return None
