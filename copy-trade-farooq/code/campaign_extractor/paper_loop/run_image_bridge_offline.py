"""Confirmed Image Paper Bridge V0.1 OFFLINE runner — 42-test matrix (no connection, no image)."""
from __future__ import annotations
import os
import sys
import traceback

_HERE = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.dirname(os.path.dirname(_HERE)), os.path.dirname(_HERE),
          os.path.join(os.path.dirname(_HERE), "q4_align"), _HERE, os.path.join(_HERE, "tests"),
          os.path.join(os.path.dirname(_HERE), "vision_v1")):   # vision_v1 last -> first on path
    sys.path.insert(0, p)


def main():
    print("=== CONFIRMED IMAGE PAPER BRIDGE V0.1 — OFFLINE ===")
    import test_image_bridge as T
    passed = failed = 0
    for name in sorted(n for n in dir(T) if n.startswith("test_")):
        try:
            getattr(T, name)(); passed += 1; print(f"  PASS  {name}")
        except Exception as e:                # noqa: BLE001
            failed += 1; print(f"  FAIL  {name}: {e!r}"); traceback.print_exc()
    print(f"\n=== IMAGE BRIDGE OFFLINE SUMMARY ===  passed={passed} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
