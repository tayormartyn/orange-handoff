"""
signal_quality.py — read a trader's OWN risk flags and tag the signal's confidence.

Traders routinely tell you how much they trust their own call, right there in the
message: "high-risk, low lot", "against the trend, be careful", or "A+ setup,
100% confident". This module scans the raw signal text for those cues (the lists
live in config.py so you can tune them) and tags the signal with a confidence
level:

    HIGH    — the trader signalled a strong, clean call (and no caution flags)
    LOW     — the trader flagged caution / risk (and no strong flags)
    NORMAL  — no cues found, or the cues cancel out (the default)

It is METADATA ONLY. It reads text and returns a label. It sizes nothing, routes
nothing, blocks nothing, and touches no money. The pipeline records the label so
review.py can later show whether HIGH-confidence calls actually outperform LOW
ones. (Whether a LOW tag is ever ACTED on is a separate, off-by-default switch,
config.SKIP_LOW_CONFIDENCE — handled in the router, not here.)
"""

import re
from dataclasses import dataclass, field
from typing import List

import config

# The three confidence levels (NORMAL is the default when nothing is found).
HIGH = "HIGH"
NORMAL = "NORMAL"
LOW = "LOW"


@dataclass
class QualityResult:
    """The outcome of scanning one signal's text."""
    level: str = NORMAL                 # HIGH / NORMAL / LOW
    high_hits: List[str] = field(default_factory=list)   # raising-confidence cues found
    low_hits: List[str] = field(default_factory=list)    # lowering-confidence cues found

    @property
    def cues(self) -> List[str]:
        """All matched cues, for display/logging."""
        return list(self.high_hits) + list(self.low_hits)

    def summary(self) -> str:
        """A short plain-English description of why this level was assigned."""
        if self.level == HIGH:
            return f"HIGH — strong cue(s): {', '.join(self.high_hits)}"
        if self.level == LOW:
            return f"LOW — caution cue(s): {', '.join(self.low_hits)}"
        if self.high_hits or self.low_hits:
            return ("NORMAL — mixed cues cancelled out "
                    f"(+{', '.join(self.high_hits)} / -{', '.join(self.low_hits)})")
        return "NORMAL — no risk/quality cues found"


def _norm(text: str) -> str:
    """Lowercase and make hyphen/underscore/whitespace differences irrelevant."""
    text = (text or "").lower()
    text = re.sub(r"[-_/]+", " ", text)     # "high-risk" / "high_risk" -> "high risk"
    text = re.sub(r"\s+", " ", text)
    return text


def _find(cues, normalised_text: str) -> List[str]:
    """
    Return the cues (as written in config) that appear in the text as whole
    words/phrases. Case- and hyphen-insensitive; de-duplicated, order preserved.
    """
    found = []
    seen = set()
    for cue in cues:
        cue_norm = _norm(cue)
        if not cue_norm:
            continue
        # \b…\b so "strong" doesn't fire inside "strongest", but multi-word
        # phrases like "low lot" still match cleanly. A trailing space in a cue
        # (e.g. "a+ ") is preserved as a literal, escaped boundary.
        pattern = r"\b" + re.escape(cue_norm).replace(r"\ ", " ") + r"\b"
        if re.search(pattern, normalised_text):
            if cue_norm not in seen:
                found.append(cue.strip())
                seen.add(cue_norm)
    return found


def _drop_substring_overlaps(hits: List[str]) -> List[str]:
    """
    Collapse overlapping matches in one category so they aren't double-counted:
    if "a+ setup" matched, "a+" shouldn't also count; if "be careful" matched,
    "careful" shouldn't. Keeps a cue only if its (normalised) phrase isn't
    contained in a different, longer matched phrase. Order preserved.
    """
    norms = {h: _norm(h) for h in hits}
    kept = []
    for h in hits:
        hn = norms[h]
        if any(other != h and hn != norms[other] and hn in norms[other] for other in hits):
            continue
        kept.append(h)
    return kept


def classify(raw_text: str) -> QualityResult:
    """
    Scan raw signal text and return a QualityResult (level + matched cues).

    Rule: count caution cues vs strong cues. More strong than caution -> HIGH;
    more caution than strong -> LOW; tie or none -> NORMAL. This keeps the default
    NORMAL and makes conflicting messages ("strong but risky") read as NORMAL
    rather than guessing.
    """
    text = _norm(raw_text)
    high_cues = getattr(config, "CONFIDENCE_HIGH_CUES", [])
    low_cues = getattr(config, "CONFIDENCE_LOW_CUES", [])

    high_hits = _drop_substring_overlaps(_find(high_cues, text))
    low_hits = _drop_substring_overlaps(_find(low_cues, text))

    if len(high_hits) > len(low_hits):
        level = HIGH
    elif len(low_hits) > len(high_hits):
        level = LOW
    else:
        level = NORMAL

    return QualityResult(level=level, high_hits=high_hits, low_hits=low_hits)


def is_valid_level(level: str) -> bool:
    return (level or "").strip().upper() in (HIGH, NORMAL, LOW)
