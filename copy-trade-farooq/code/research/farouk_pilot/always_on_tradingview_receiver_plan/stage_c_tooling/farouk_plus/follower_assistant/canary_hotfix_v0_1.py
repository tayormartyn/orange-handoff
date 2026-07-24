"""Phase 9 — post-activation isolated CANARY (RESEARCH-ONLY / SYNTHETIC). Runs the EXACT 15:32
morphology through the fixed parser + wire correlation in a fully sandboxed world (temp ledgers,
synthetic provenance). Proves parse + exactly one test campaign + a producible test freeze, with the
genuine ledgers and F001/F002 untouched. Writes a canary artifact.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "evidence_layer"))
import interpreter                                                # noqa: E402
import live_wire as W                                             # noqa: E402
import strategy_router as R                                       # noqa: E402

CANARY = ("seascalperfarouk Posted in gold-trades\n\n"
          "@Whale XAUUSD Sell Zone: 4059–4069\nStop Loss: 4090\nhigh Risk: Low lot size")


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    tmp = tempfile.mkdtemp(prefix="canary_")
    # capture genuine-ledger identities BEFORE (must not change)
    genuine_fwd = os.path.join(HERE, "..", "forward_validation_ledger_v0_2.jsonl")
    genuine_freeze = os.path.join(HERE, "evidence_layer", "router_freeze_v0_1.jsonl")
    before_fwd = hashlib.sha256(open(genuine_fwd, "rb").read()).hexdigest()
    before_freeze = (os.path.getsize(genuine_freeze) if os.path.exists(genuine_freeze) else 0)

    # 1) PARSE
    c = interpreter.classify(CANARY)
    parse_ok = (c["kind"] == "ENTRY" and c["direction"] == "SHORT" and c["zone_low"] == "4059"
                and c["zone_high"] == "4069" and c["sl"] == "4090"
                and c["qualitative_risk_flag"] == "HIGH_RISK_SOURCE_WORDING")

    # 2) CAMPAIGN CREATION in a sandboxed wire world
    W.FWD_LEDGER = os.path.join(tmp, "fwd.jsonl")
    W.FOLLOWER_LEDGER = os.path.join(tmp, "follower.jsonl")
    W.CARD_DIR = os.path.join(tmp, "cards")
    setups, open_ids = {}, []
    msg = {"id": 999001, "posted_at": "2026-07-15T14:32:18+00:00", "raw_text": CANARY,
           "raw_text_sha256": hashlib.sha256(CANARY.encode()).hexdigest(), "event_type": "CREATED", "revision": 1}
    act = W.process_message(msg, setups, open_ids, {"version": "0.1.0"})
    campaigns = list(setups)
    one_campaign = len(campaigns) == 1 and campaigns[0].startswith("XAU-F")
    not_f001_f002 = all(cid not in ("XAU-F001-20260714", "XAU-F002-20260714") for cid in campaigns)

    # 3) a router freeze is PRODUCIBLE for the canary (sandbox ledger, SYNTHETIC class)
    cid = campaigns[0]
    pre = [(1784132000 - (60 - i) * 60, __import__("decimal").Decimal("4065"),
            __import__("decimal").Decimal("4067"), __import__("decimal").Decimal("4063"),
            __import__("decimal").Decimal("4065")) for i in range(60)]
    R.ROUTER_FREEZE_LEDGER = os.path.join(tmp, "canary_freeze.jsonl")
    fz = R.freeze_router(setup_id=cid, direction="SHORT", zone_low="4059", zone_high="4069", sl="4090",
                         decision_ts=1784132000, bars=pre, record_class="SYNTHETIC_INTEGRATION_TEST",
                         raw_source_ref={"pretrade_logical_hash": "canary", "source_message_utc": "2026-07-15T14:32:18Z"})
    freeze_ok = fz["record_type"] == "ROUTER_FREEZE" and fz["eligible_for_prospective_evidence"] is False

    # 4) genuine ledgers untouched
    after_fwd = hashlib.sha256(open(genuine_fwd, "rb").read()).hexdigest()
    after_freeze = (os.path.getsize(genuine_freeze) if os.path.exists(genuine_freeze) else 0)
    genuine_untouched = (before_fwd == after_fwd) and (before_freeze == after_freeze)

    artifact = {
        "canary_id": "parser_correlation_hotfix_canary_v0_1", "provenance": "SYNTHETIC_CANARY / SANDBOX",
        "morphology": "XAUUSD Sell Zone: 4059–4069 / Stop Loss: 4090 / high Risk: Low lot size",
        "parse": {"kind": c["kind"], "direction": c.get("direction"), "zone_low": c.get("zone_low"),
                  "zone_high": c.get("zone_high"), "sl": c.get("sl"), "risk_flag": c.get("qualitative_risk_flag")},
        "parse_ok": parse_ok, "wire_action": act, "campaigns": campaigns,
        "exactly_one_test_campaign": one_campaign, "not_f001_f002": not_f001_f002,
        "test_freeze_producible": freeze_ok, "freeze_prospective_eligible": fz["eligible_for_prospective_evidence"],
        "genuine_forward_ledger_untouched": before_fwd == after_fwd,
        "genuine_freeze_ledger_untouched": before_freeze == after_freeze,
        "genuine_ledgers_untouched": genuine_untouched,
        "eligible_for_training": False, "eligible_for_performance_attribution": False,
        "SIMULATION_ONLY": True, "review_only": True, "observation_only": True,
    }
    out = os.path.join(HERE, "evidence_layer", "copy_simulator", "canary_hotfix_result_v0_1.json")
    json.dump(artifact, open(out, "w", encoding="utf-8"), indent=1, default=str)
    allok = parse_ok and one_campaign and not_f001_f002 and freeze_ok and genuine_untouched
    print("CANARY:", "PASS" if allok else "FAIL")
    print("  parse:", artifact["parse"])
    print("  wire_action:", act, "| campaigns:", campaigns)
    print("  test_freeze_producible:", freeze_ok, "| prospective_eligible:", fz["eligible_for_prospective_evidence"])
    print("  genuine ledgers untouched:", genuine_untouched)
    print("  artifact ->", out)
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()
