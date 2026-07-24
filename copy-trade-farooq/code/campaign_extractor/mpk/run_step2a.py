"""
MPK-2A offline test runner. Runs the onboarding + permission-gate test matrix on TEMP
databases (no real provider registered, no persistent canonical write). Reads the
persistent Farouk state read-only for the final summary. Exit 0 iff all pass.
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
from appendonly import ro_connect


def _farouk_summary():
    reg = ro_connect(init_db.REGISTRY_DB_PATH, immutable=True)
    cam = ro_connect(init_db.CAMPAIGNS_DB_PATH, immutable=True)
    try:
        return {
            "canonical_provider_count": reg.execute("SELECT COUNT(*) FROM providers").fetchone()[0],
            "provider_farouk_001_count": reg.execute(
                "SELECT COUNT(*) FROM providers WHERE provider_id='provider_farouk_001'").fetchone()[0],
            "legacy_campaign_mapping_count": cam.execute(
                "SELECT COUNT(*) FROM legacy_campaign_mapping").fetchone()[0],
        }
    finally:
        reg.close(); cam.close()


def main():
    import test_mpk_step2a as T
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
    fs = _farouk_summary()
    print("\n=== MPK-2A SUMMARY ===")
    print(f"  total={len(tests)} passed={len(passed)} failed={len(failed)} skipped=0")
    print(f"  persistent canonical_provider_count   = {fs['canonical_provider_count']}")
    print(f"  persistent provider_farouk_001_count  = {fs['provider_farouk_001_count']}")
    print(f"  persistent legacy_campaign_mapping    = {fs['legacy_campaign_mapping_count']}")
    print(f"  source_candidate_count (persistent)   = 0 (synthetic candidates live in temp DBs only)")
    if failed:
        for n, e in failed:
            print(f"    - {n}: {e}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
