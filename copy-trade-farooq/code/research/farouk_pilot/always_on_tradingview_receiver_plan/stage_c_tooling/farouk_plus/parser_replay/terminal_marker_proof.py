"""TERMINAL-MARKER (v3) proof (D-063). Proves the XAU_F_TERMINAL_OUTCOME support:
  1. NO-OP: on the CURRENT ledger (no XAU_F_TERMINAL_OUTCOME records), v3 load_campaign_state
     returns the SAME open_ids as the deployed live_wire.
  2. MARKER CLOSES: injecting one XAU_F_TERMINAL_OUTCOME for a nominal-open campaign drops
     exactly that campaign from open_ids; all others unchanged.
  3. FAIL-OPEN: a malformed marker (no setup_id) is ignored — campaign STAYS open (a missing
     close never fabricates a terminal).
READ-ONLY: builds temp ledgers in scratch; never writes the real forward ledger.
"""
import importlib.util
import json
import os
import sys
import tempfile

FA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "follower_assistant")


def _load(modname, path, fwd_override):
    spec = importlib.util.spec_from_file_location(modname, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[modname] = m
    _cwd = os.getcwd()
    os.chdir(FA)
    spec.loader.exec_module(m)
    os.chdir(_cwd)
    m.FWD_LEDGER = fwd_override
    return m


def main():
    real_fwd = os.path.join(os.path.dirname(FA), "forward_validation_ledger_v0_2.jsonl")
    live = _load("lw_live", os.path.join(FA, "live_wire.py"), real_fwd)
    v3 = _load("lw_v3", os.path.join(FA, "live_wire_v3_terminal_marker.py"), real_fwd)

    ok = True

    def ck(name, cond, detail=""):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  <- {detail}"))
        ok = ok and bool(cond)

    # 1. NO-OP on current ledger
    _, live_open, _ = live.load_campaign_state()
    _, v3_open, _ = v3.load_campaign_state()
    ck(f"NO-OP: v3 open_ids == live open_ids ({v3_open})", v3_open == live_open, (live_open, v3_open))

    # 2. MARKER CLOSES — inject XAU_F_TERMINAL_OUTCOME for the first nominal-open campaign
    if not v3_open:
        ck("marker test needs >=1 open campaign", False, "no open campaigns")
        return
    target = v3_open[0]
    lines = open(real_fwd, encoding="utf-8").read().splitlines()
    marker = json.dumps({"record_type": "XAU_F_TERMINAL_OUTCOME", "setup_id": target,
                         "effective_ts_utc": "2026-07-21T00:00:00Z", "basis_price": "TEST",
                         "per_leg_states": [], "review_only": True, "executable": False})
    tmp = os.path.join(tempfile.mkdtemp(prefix="tmk_"), "fwd.jsonl")
    open(tmp, "w", encoding="utf-8").write("\n".join(lines + [marker]) + "\n")
    v3.FWD_LEDGER = tmp
    _, v3_open2, _ = v3.load_campaign_state()
    ck(f"MARKER: {target} removed from open set", target not in v3_open2, v3_open2)
    ck("MARKER: all other campaigns unchanged",
       set(v3_open2) == set(v3_open) - {target}, (v3_open, v3_open2))

    # 3. FAIL-OPEN — malformed marker (no setup_id) ignored, nothing closes
    bad = json.dumps({"record_type": "XAU_F_TERMINAL_OUTCOME", "effective_ts_utc": "x"})
    open(tmp, "w", encoding="utf-8").write("\n".join(lines + [bad]) + "\n")
    v3.FWD_LEDGER = tmp
    _, v3_open3, _ = v3.load_campaign_state()
    ck("FAIL-OPEN: malformed marker closes nothing", set(v3_open3) == set(v3_open), v3_open3)

    v3.FWD_LEDGER = real_fwd
    print("\nTERMINAL_MARKER_PROOF:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
