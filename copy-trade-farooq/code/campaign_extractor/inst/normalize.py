"""
INST-1 deterministic token normalisation. Conservative formatting-only changes.

No fuzzy matching, no embeddings, no LLM, no probabilistic inference. Distinct instruments
must NOT collapse: only case folding, whitespace trim/collapse, and removal of the two
recognised separators (space and '/') are applied. 'BTCUSD' and 'BTCUSDT' stay distinct;
'XAU/USD' / 'XAU USD' / 'xauusd' all canonicalise to 'XAUUSD'.
"""
from __future__ import annotations
import re

_VALID = re.compile(r"[A-Z0-9 /._-]+")
MAX_LEN = 32


def normalise_token(raw):
    """Return (normalised_token, validity) where validity is 'OK' or 'REJECTED_INVALID'.

    REJECTED_INVALID for: None, empty/whitespace-only, > MAX_LEN, or characters outside
    the conservative allowed set. A well-formed but unrecognised token is 'OK' here and is
    classified UNKNOWN_NEEDS_REVIEW later by the resolver (validity != recognition).
    """
    if raw is None:
        return None, "REJECTED_INVALID"
    s = raw.strip()
    if not s:
        return "", "REJECTED_INVALID"
    collapsed = re.sub(r"\s+", " ", s)
    up = collapsed.upper()
    if len(up) > MAX_LEN or not _VALID.fullmatch(up):
        return up, "REJECTED_INVALID"
    # remove ONLY the two recognised separators; keep . _ - intact (conservative)
    token = up.replace(" ", "").replace("/", "")
    if not token:
        return up, "REJECTED_INVALID"
    return token, "OK"
