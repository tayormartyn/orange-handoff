"""Brick 5C Phase 2A runner: run the A–Q offline test matrix. Exit 0 iff all pass.
Initialises NO real media DB/dir; all work is on temp fixtures."""
from __future__ import annotations
import os
import sys
import traceback

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "tests"))
sys.path.insert(0, os.path.dirname(_HERE))   # campaign_extractor (for prospective import)

# Collision-proof config load (never the ROOT project config.py) — see store.py for rationale.
import importlib.util as _ilu
_cfgspec = _ilu.spec_from_file_location("media_capture_config", os.path.join(_HERE, "config.py"))
CFG = _ilu.module_from_spec(_cfgspec)
_cfgspec.loader.exec_module(CFG)


def main():
    import test_phase2a as T
    tests = sorted((n for n in dir(T) if n.startswith("test_")), key=lambda n: n.split("_")[1])
    passed, failed = [], []
    for name in tests:
        try:
            getattr(T, name)()
            passed.append(name); print(f"  PASS  {name}")
        except Exception as e:                # noqa: BLE001
            failed.append((name, repr(e))); print(f"  FAIL  {name}: {e!r}")
            traceback.print_exc()
    print(f"\n=== BRICK 5C PHASE 2A SUMMARY ===  total={len(tests)} passed={len(passed)} "
          f"failed={len(failed)} skipped=0")
    print(f"  TELEGRAM_MEDIA_CAPTURE_ENABLED = {CFG.TELEGRAM_MEDIA_CAPTURE_ENABLED} (fail-closed)")
    print(f"  TELEGRAM_MEDIA_MAX_BYTES       = {CFG.TELEGRAM_MEDIA_MAX_BYTES}")
    if failed:
        for n, e in failed:
            print(f"    - {n}: {e}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
