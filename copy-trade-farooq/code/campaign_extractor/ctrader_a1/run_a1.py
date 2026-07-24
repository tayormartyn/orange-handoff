"""
cTrader A1 runner — the OFFLINE preflight deliverable. Loads the authoritative .env, reports
MASKED presence (PRESENT/MISSING/EMPTY/MALFORMED_FORMAT) only, runs the secret-safety scan
(reports file paths/categories ONLY), and confirms locks. NEVER prints a credential value.
NO connection, NO OAuth, NO order.
"""
from __future__ import annotations
import os
import sys
import traceback

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.dirname(_HERE))   # campaign_extractor
sys.path.insert(0, os.path.join(_HERE, "tests"))

import dotenv_loader as DL
import masked_presence as MP
import scope_validator as SV
import secret_scan as SS

REPORTED = ("CTRADER_CLIENT_ID", "CTRADER_CLIENT_SECRET", "CTRADER_ACCESS_TOKEN",
            "CTRADER_REFRESH_TOKEN", "CTRADER_ACCOUNT_ID", "CTRADER_ENV", "CTRADER_SCOPE",
            "CTRADER_REDIRECT_URI", "CTRADER_GOLD_SYMBOL")
SECRET_KEYS = {"CLIENT_ID": "CTRADER_CLIENT_ID", "CLIENT_SECRET": "CTRADER_CLIENT_SECRET",
               "ACCESS_TOKEN": "CTRADER_ACCESS_TOKEN", "REFRESH_TOKEN": "CTRADER_REFRESH_TOKEN"}


def preflight():
    env = DL.load_ctrader_env()                 # values kept private; never printed
    print("=== A1.1 AUTHORITATIVE .env ===")
    print(f"  path                : {DL.ENV_PATH}")
    print(f"  exists              : {os.path.exists(DL.ENV_PATH)}")
    print(f"  gitignored          : {SS.env_is_gitignored()}")
    print(f"  is git repo         : {SS.is_git_repo()}  (no repo => cannot be committed)")
    print("=== A1.2 MASKED PRESENCE (no values) ===")
    for name, st in MP.report(env, REPORTED).items():
        print(f"  {name:24} {st}")
    print("=== A1.3 SCOPE ===")
    print(f"  requested OAuth scope : {SV.requested_oauth_scope()}  (view-only; 'trading' never emitted)")
    print(f"  SCOPE_VIEW accepted   : {SV.returned_scope_is_view_only('SCOPE_VIEW')}")
    print(f"  SCOPE_TRADE rejected  : {not SV.returned_scope_is_view_only('SCOPE_TRADE')}")
    print("=== A1.4 SECRET-SAFETY SCAN (paths/categories only) ===")
    secret_values = {cat: env.get(var, "") for cat, var in SECRET_KEYS.items()}
    findings = SS.scan_for_secret_values(secret_values)
    print(f"  secret-VALUE exposures outside authorised .env : {len(findings)}")
    for path, cat, status in findings:
        print(f"    {status}  {cat}  {path}")
    from broker_readonly.source_scan import scan_secret_leaks
    leaks = scan_secret_leaks([os.path.join(os.path.dirname(_HERE), "..", "ctrader_auth.py"),
                               os.path.join(os.path.dirname(_HERE), "..", "ctrader_config.py"),
                               os.path.join(_HERE, "..", "broker_readonly")])
    print(f"  source-pattern secret-in-log findings (full auth path): {len(leaks)} (expected 6 known FPs)")
    return findings


def main():
    findings = preflight()
    import test_ctrader_a1 as T
    tests = sorted((n for n in dir(T) if n.startswith("test_")), key=lambda n: n.split("_")[1])
    passed = failed = 0
    print("\n=== A1.5 OFFLINE TESTS ===")
    for name in tests:
        try:
            getattr(T, name)(); passed += 1; print(f"  PASS  {name}")
        except Exception as e:                # noqa: BLE001
            failed += 1; print(f"  FAIL  {name}: {e!r}"); traceback.print_exc()
    print(f"\n=== CTRADER A1 SUMMARY ===  tests passed={passed} failed={failed} "
          f"secret_exposures={len(findings)}")
    return 1 if (failed or findings) else 0


if __name__ == "__main__":
    sys.exit(main())
