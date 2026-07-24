"""ASSOC-1R runner: run the real-evidence replay, print the per-message table + census, then
run the A–L test matrix. Exit 0 iff all pass."""
from __future__ import annotations
import os
import sys
import traceback

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "tests"))

import replay as R


def main():
    rep = R.run(write_db=True)
    print(f"live rows replayed: {rep['rows']}")
    print("per-message decisions:")
    for r in rep["results"]:
        d = r["decision"]
        status = d["association_status"] if d else "ORIGINAL_SIGNAL"
        rule = d["rule_fired"] if d else "-"
        print(f"  {r['message_id']}  {r['candidate_type']:16} {str(r['intent']):26} "
              f"-> {status:28} {rule}")
    print(f"\ncensus: {rep['census']}")
    print(f"rules : {rep['rules']}")

    import test_assoc1r as T
    tests = sorted((n for n in dir(T) if n.startswith("test_")), key=lambda n: n.split("_")[1])
    passed, failed = [], []
    for name in tests:
        try:
            getattr(T, name)()
            passed.append(name); print(f"  PASS  {name}")
        except Exception as e:                  # noqa: BLE001
            failed.append((name, repr(e))); print(f"  FAIL  {name}: {e!r}")
            traceback.print_exc()
    print(f"\n=== ASSOC-1R SUMMARY ===  total={len(tests)} passed={len(passed)} "
          f"failed={len(failed)} skipped=0")
    if failed:
        for n, e in failed:
            print(f"    - {n}: {e}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
