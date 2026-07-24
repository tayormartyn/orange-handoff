"""Kill-switch: the presence of data/DEMO_EXECUTION_DISABLED blocks EVERYTHING (proposals + any
future submission). Fail-closed."""
from __future__ import annotations
import os

import config as CFG


def is_disabled(path=None):
    return os.path.exists(path or CFG.DISABLE_FILE)


def disabled_check(path=None):
    from models import Check
    return Check("disable_file_absent", not is_disabled(path),
                 "BLOCKED_BY_DISABLE_FILE" if is_disabled(path) else "ok")
