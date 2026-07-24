"""
ASSOC-1 runner: initialise the isolated decision DB (empty), run the A–V test matrix on
temp DBs/snapshots, and print the fixture decision census. Exit 0 iff all pass.
"""
from __future__ import annotations
import os
import sys
import traceback

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "tests"))

from decisions_db import AssociationDecisionsDB, DB_PATH


def main():
    db = AssociationDecisionsDB(DB_PATH)        # create empty canonical decision DB
    persistent_decisions = db.count()
    db.close()

    import test_assoc1 as T
    tests = sorted((n for n in dir(T) if n.startswith("test_")),
                   key=lambda n: n.split("_")[1])
    passed, failed = [], []
    for name in tests:
        try:
            getattr(T, name)()
            passed.append(name); print(f"  PASS  {name}")
        except Exception as e:                  # noqa: BLE001
            failed.append((name, repr(e))); print(f"  FAIL  {name}: {e!r}")
            traceback.print_exc()

    tally, _ = T.census()
    print("\n=== ASSOC-1 SUMMARY ===")
    print(f"  total={len(tests)} passed={len(passed)} failed={len(failed)} skipped=0")
    print(f"  persistent decision rows = {persistent_decisions}")
    print(f"  fixture decision census  = {tally}")
    if failed:
        for n, e in failed:
            print(f"    - {n}: {e}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
