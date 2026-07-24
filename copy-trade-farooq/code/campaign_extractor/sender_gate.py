"""
Deterministic sender gate.

Sender identity is EVIDENCE. It is derived from the literal first-line header
    "<handle> Posted in <emoji>·<channel>"
and recorded on every message. Only Farouk (`seascalperfarouk`) may produce
campaign-state-mutating events. Everything else is ANALYSIS_ONLY_CONTEXT.

Fail closed: a header with no handle, or no header at all, yields sender=None and
role=ANALYSIS_ONLY_CONTEXT — it is NEVER assumed to be Farouk.
"""
from __future__ import annotations
import re
from enum import Enum

from schema import FAROUK_HANDLE

HANDLE_RE = re.compile(r"^([A-Za-z0-9_.]+)\s+Posted in\b")

KNOWN_VOICES = {
    "seascalperfarouk": "Farouk",
    ".ccolumbus": "Columbus",
    "kyledoops": "Kyle Dukes",
    "wazwithazed": "Azed (quant-flow)",
    "navigatorjosh": "Josh the Navigator",
    "wallstreetsingh": "Wall Street Singh",
    "terrilyn": "Terrilyn",
}


class Role(str, Enum):
    CAMPAIGN_SOURCE = "CAMPAIGN_SOURCE"            # only Farouk
    ANALYSIS_ONLY_CONTEXT = "ANALYSIS_ONLY_CONTEXT"


def derive_sender(raw_text: str):
    """Return (handle_or_None, voice_label)."""
    first = ""
    for line in (raw_text or "").splitlines():
        if line.strip():
            first = line.strip()
            break
    m = HANDLE_RE.match(first)
    if m:
        h = m.group(1)
        return h, KNOWN_VOICES.get(h, "UNKNOWN_HANDLE")
    if "Posted in" in (raw_text or ""):
        return None, "AMBIGUOUS_NO_HANDLE"
    return None, "NO_HEADER"


def is_farouk(handle) -> bool:
    return handle == FAROUK_HANDLE


def role_for(handle) -> Role:
    return Role.CAMPAIGN_SOURCE if is_farouk(handle) else Role.ANALYSIS_ONLY_CONTEXT


def may_mutate_campaign_state(raw_text: str) -> bool:
    """The hard gate: only Farouk's posts can ever reach candidate extraction."""
    handle, _ = derive_sender(raw_text)
    return is_farouk(handle)
