"""Q4A OFFLINE runner — runs the deterministic test matrix (no connection). Exit 0 iff all pass."""
from __future__ import annotations
import os
import sys
import traceback

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "tests"))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, os.path.dirname(os.path.dirname(_HERE)))


def main():
    print("=== Q4A ALIGNMENT KERNEL — OFFLINE ===")
    import test_q4 as T
    passed = failed = 0
    for name in sorted(n for n in dir(T) if n.startswith("test_")):
        try:
            getattr(T, name)(); passed += 1; print(f"  PASS  {name}")
        except Exception as e:                # noqa: BLE001
            failed += 1; print(f"  FAIL  {name}: {e!r}"); traceback.print_exc()
    print(f"\n=== Q4A OFFLINE SUMMARY ===  passed={passed} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
