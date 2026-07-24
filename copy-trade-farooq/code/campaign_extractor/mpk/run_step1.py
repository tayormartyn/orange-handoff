"""
MPK-1 Step 1 offline test runner (no pytest; matches project's inline-harness convention).

Initialises the two empty canonical databases, then runs every test_* function in
tests/test_mpk_step1.py. Prints PASS/FAIL per test and a summary. Exit code 0 iff all pass.
"""
from __future__ import annotations
import os
import sys
import traceback

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "tests"))

import init_db


def main():
    # 1) deterministic empty-schema initialisation of the persistent canonical DBs
    rep = init_db.initialise()
    rc = rep["registry"]["business_counts"]; cc = rep["campaigns"]["business_counts"]
    allcounts = {**rc, **cc}
    assert all(v == 0 for v in allcounts.values()), f"business data present: {allcounts}"

    # 2) run the test suite
    import test_mpk_step1 as T
    tests = sorted(n for n in dir(T) if n.startswith("test_"))
    passed, failed = [], []
    for name in tests:
        try:
            getattr(T, name)()
            passed.append(name)
            print(f"  PASS  {name}")
        except Exception as e:                       # noqa: BLE001
            failed.append((name, repr(e)))
            print(f"  FAIL  {name}: {e!r}")
            traceback.print_exc()

    print("\n=== MPK-1 STEP 1 TEST SUMMARY ===")
    print(f"  total   : {len(tests)}")
    print(f"  passed  : {len(passed)}")
    print(f"  failed  : {len(failed)}")
    print(f"  skipped : 0")
    print(f"  business row counts (canonical persistent DBs): {allcounts}")
    if failed:
        print("  FAILURES:")
        for n, e in failed:
            print(f"    - {n}: {e}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
