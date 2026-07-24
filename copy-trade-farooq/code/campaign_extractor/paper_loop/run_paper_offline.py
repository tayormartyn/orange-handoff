"""Unified Paper Loop V0.1 OFFLINE runner — runs the 30-test matrix (no connection)."""
from __future__ import annotations
import os
import sys
import traceback

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(_HERE)))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "q4_align"))
sys.path.insert(0, os.path.join(_HERE, "tests"))
sys.path.insert(0, _HERE)


def main():
    print("=== UNIFIED PAPER DECISION LOOP V0.1 — OFFLINE ===")
    import test_paper_loop as T
    passed = failed = 0
    for name in sorted(n for n in dir(T) if n.startswith("test_")):
        try:
            getattr(T, name)(); passed += 1; print(f"  PASS  {name}")
        except Exception as e:                # noqa: BLE001
            failed += 1; print(f"  FAIL  {name}: {e!r}"); traceback.print_exc()
    print(f"\n=== PAPER LOOP OFFLINE SUMMARY ===  passed={passed} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
