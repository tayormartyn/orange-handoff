"""cTrader A2 OFFLINE runner — runs the mocked test matrix (no connection, no token). Exit 0 iff pass."""
from __future__ import annotations
import os
import sys
import traceback

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_HERE, "tests"))

import token_loader


def main():
    print("=== A2 OFFLINE READINESS ===")
    print(f"  cached token present : {token_loader.load_cached_token() is not None}  "
          f"(A2 mints/requests nothing)")
    import test_a2_reader as T
    tests = sorted(n for n in dir(T) if n.startswith("test_"))
    passed = failed = 0
    for name in tests:
        try:
            getattr(T, name)(); passed += 1; print(f"  PASS  {name}")
        except Exception as e:                # noqa: BLE001
            failed += 1; print(f"  FAIL  {name}: {e!r}"); traceback.print_exc()
    print(f"\n=== CTRADER A2 OFFLINE SUMMARY ===  passed={passed} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
