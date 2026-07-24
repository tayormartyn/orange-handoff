"""
INST-1 runner: seed the persistent instrument_registry_v1.db (idempotent), then run the
offline test matrix on temp DBs. Exit 0 iff all pass.
"""
from __future__ import annotations
import json
import os
import sys
import traceback

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "tests"))

import seed as SEED


def main():
    rep = SEED.initialise()
    print("SEED:", json.dumps(rep, sort_keys=True))

    import test_inst1 as T
    tests = sorted((n for n in dir(T) if n.startswith("test_")),
                   key=lambda n: n.split("_")[1])
    passed, failed = [], []
    for name in tests:
        try:
            getattr(T, name)()
            passed.append(name); print(f"  PASS  {name}")
        except Exception as e:                # noqa: BLE001
            failed.append((name, repr(e))); print(f"  FAIL  {name}: {e!r}")
            traceback.print_exc()

    c = rep["counts"]
    print("\n=== INST-1 SUMMARY ===")
    print(f"  total={len(tests)} passed={len(passed)} failed={len(failed)} skipped=0")
    print(f"  db path                  = {rep['path']}")
    print(f"  canonical_underlyings    = {c['canonical_underlyings']}")
    print(f"  canonical_instruments    = {c['canonical_instruments']}")
    print(f"  global_aliases           = {c['global_aliases']}")
    print(f"  provider_aliases         = {c['provider_aliases']}")
    print(f"  mapping_rules            = {c['mapping_rules']}")
    print(f"  mapping_decisions        = {c['mapping_decisions']}")
    if failed:
        for n, e in failed:
            print(f"    - {n}: {e}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
