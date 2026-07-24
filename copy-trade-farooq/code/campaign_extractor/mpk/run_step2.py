"""
MPK-1 Step 2 runner: register Farouk + map the signed-off 28 into the persistent canonical
DBs (idempotent), then run the Step 2 test suite. Exit 0 iff all pass.
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

import init_db
import step2_register_and_map as S2


def main():
    init_db.initialise()                      # ensure schema present (idempotent)
    rep = S2.run(init_db.REGISTRY_DB_PATH, init_db.CAMPAIGNS_DB_PATH)
    print("STEP 2 REGISTRATION + MAPPING REPORT:")
    print(json.dumps(rep, indent=2, sort_keys=True))

    import test_mpk_step2 as T
    tests = sorted(n for n in dir(T) if n.startswith("test_"))
    passed, failed = [], []
    print("\nTESTS:")
    for name in tests:
        try:
            getattr(T, name)()
            passed.append(name); print(f"  PASS  {name}")
        except Exception as e:                # noqa: BLE001
            failed.append((name, repr(e))); print(f"  FAIL  {name}: {e!r}")
            traceback.print_exc()

    print("\n=== MPK-1 STEP 2 SUMMARY ===")
    print(f"  total={len(tests)} passed={len(passed)} failed={len(failed)} skipped=0")
    print(f"  canonical_provider_count   = {rep['canonical_provider_count']}")
    print(f"  provider_farouk_001_count  = {rep['provider_farouk_001_count']}")
    print(f"  legacy_mapping_total       = {rep['legacy_mapping_total']}")
    print(f"  mapped_verified_count      = {rep['mapped_verified_count']}")
    print(f"  needs_review_count         = {rep['needs_review_count']}")
    print(f"  campaigns_count            = {rep['campaigns_count']}")
    if failed:
        for n, e in failed:
            print(f"    - {n}: {e}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
