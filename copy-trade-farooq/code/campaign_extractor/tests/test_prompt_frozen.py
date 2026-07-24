"""
Lock the frozen extractor prompt. After refinements 1 & 2 landed on the June 26 dev set,
the prompt is FROZEN — no more edits before the held-out June 24 test. If anyone changes
SYSTEM_PROMPT / the user template / the version, this hash breaks.
"""
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import extractor as E

FROZEN_PROMPT_HASH = "95bbf6a4b18ebdd7fc4db2a3e1449ab2e7b7e65a7cf16da461d8ea251a802ef4"
FROZEN_PROMPT_VERSION = "prompt-0.2.0"


def test_prompt_is_frozen():
    artifact = (E.SYSTEM_PROMPT + "\n----USER_TEMPLATE----\n" + E._USER_TEMPLATE
                + "\n----VERSION----\n" + E.PROMPT_VERSION)
    h = hashlib.sha256(artifact.encode("utf-8")).hexdigest()
    assert E.PROMPT_VERSION == FROZEN_PROMPT_VERSION
    assert h == FROZEN_PROMPT_HASH, (
        f"extractor prompt changed after freeze! got {h}. The prompt is frozen for the "
        f"held-out test — do not edit it.")
