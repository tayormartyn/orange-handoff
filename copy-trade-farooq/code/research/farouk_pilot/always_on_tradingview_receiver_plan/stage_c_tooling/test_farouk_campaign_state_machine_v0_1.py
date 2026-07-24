"""
Tests for Farouk Campaign State Machine v0.1 (offline, observation-only).

Runnable standalone:  python test_farouk_campaign_state_machine_v0_1.py
Also importable by pytest (test_* functions).
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import farouk_campaign_state_machine_v0_1 as sm  # noqa: E402

# rank for "is X a downgrade of Y": higher = stronger candidate
_RANK = {"SHADOW_CANDIDATE_MEDIUM": 3, "SHADOW_CANDIDATE_LOW": 2, "WATCH_ONLY": 1, "SHADOW_REJECTED": 0}


def _base_medium():
    """A clean, HTF-aligned observation that the machine rates SHADOW_CANDIDATE_MEDIUM."""
    return sm.Observation(
        campaign_id="BASE", direction_hint="LONG",
        sweep="CONFIRMED", structure_choch="CONFIRMED", choch_in_chop=False,
        order_block="FRESH", displacement="MODERATE", htf="ALIGNED",
        contradiction=False, outcome="MIXED",
    )


def test_hr0001_ends_shadow_candidate_low():
    r = sm.run(sm.fixture_hr0001())
    assert r.campaign_state == "SHADOW_CANDIDATE_LOW", r.campaign_state
    assert "SHADOW_CANDIDATE_LOW" in r.state_path


def test_hr0002_ends_watch_only():
    r = sm.run(sm.fixture_hr0002())
    assert r.campaign_state == "WATCH_ONLY", r.campaign_state


def test_hr0003_ends_shadow_rejected():
    r = sm.run(sm.fixture_hr0003())
    assert r.campaign_state in ("SHADOW_REJECTED", "REJECT"), r.campaign_state


def test_htf_opposed_downgrades_candidate():
    aligned = sm.run(_base_medium())
    assert aligned.campaign_state == "SHADOW_CANDIDATE_MEDIUM", aligned.campaign_state
    opp = sm.run(sm.Observation(**{**_base_medium().__dict__, "htf": "OPPOSED"}))
    assert _RANK[opp.campaign_state] < _RANK[aligned.campaign_state], opp.campaign_state
    assert "HTF_OPPOSED" in opp.state_path


def test_spent_ob_downgrades_candidate():
    base = sm.run(_base_medium())
    spent = sm.run(sm.Observation(**{**_base_medium().__dict__, "order_block": "MITIGATED_SPENT"}))
    assert spent.campaign_state != "SHADOW_CANDIDATE_MEDIUM"
    assert spent.campaign_state in ("WATCH_ONLY", "SHADOW_REJECTED"), spent.campaign_state
    assert _RANK[spent.campaign_state] < _RANK[base.campaign_state]


def test_breached_ob_downgrades_candidate():
    base = sm.run(_base_medium())
    breached = sm.run(sm.Observation(**{**_base_medium().__dict__, "order_block": "FRESH_BREACHED"}))
    assert breached.campaign_state not in ("SHADOW_CANDIDATE_MEDIUM", "SHADOW_CANDIDATE_LOW"), breached.campaign_state
    assert _RANK[breached.campaign_state] < _RANK[base.campaign_state]


def test_weak_choch_in_chop_cannot_be_medium():
    weak = sm.run(sm.Observation(**{**_base_medium().__dict__, "choch_in_chop": True, "structure_choch": "WEAK"}))
    assert weak.campaign_state != "SHADOW_CANDIDATE_MEDIUM", weak.campaign_state


def test_no_state_emits_execution():
    for obs in (sm.fixture_hr0001(), sm.fixture_hr0002(), sm.fixture_hr0003(), _base_medium()):
        r = sm.run(obs)
        assert sm.emits_execution(r) is False
        d = r.to_dict()
        # any key containing an execution substring must be an explicit negative flag == False
        for k, v in d.items():
            if any(bad in k.lower() for bad in sm.FORBIDDEN_KEY_SUBSTRINGS):
                assert k in sm.ALLOWED_NEGATIVE_FLAGS, f"forbidden key {k}"
                assert v is False, f"{k} must be False"
        for flag in ("trade_ready", "execution_allowed", "broker_execution_allowed",
                     "qst_allowed", "order_intent", "risk_sizing_allowed"):
            assert d[flag] is False, flag
        assert d["observation_only"] is True and d["candidate_only"] is True


def test_not_integration_ready_unchanged():
    assert sm.NOT_INTEGRATION_READY is True
    assert sm.OBSERVATION_ONLY is True


def test_gates_remain_false():
    # repo root is 4 parents above this file
    root = _HERE
    for _ in range(4):
        root = os.path.dirname(root)
    if root not in sys.path:
        sys.path.insert(0, root)
    import config
    import ctrader_config
    assert config.MODE == "PAPER"
    assert config.LISTENER_MODE == "PREVIEW"
    assert config.EXECUTION_ENABLED is False
    assert ctrader_config.CTRADER_EXECUTION_ENABLED is False


# --- extra: reviewed-fixture lifecycle reaches REVIEWED -> JOURNALLED and agrees with the human verdict ---
def test_human_review_lifecycle_and_agreement():
    for fx, label in ((sm.fixture_hr0001(), "SHADOW_CANDIDATE_LOW"),
                      (sm.fixture_hr0002(), "WATCH"),
                      (sm.fixture_hr0003(), "REJECT")):
        obs = sm.Observation(**{**fx.__dict__, "human_review": {"label": label, "status": "REVIEWED"}})
        r = sm.run(obs)
        assert "REVIEWED" in r.state_path and "JOURNALLED" in r.state_path
        assert r.final_state == "JOURNALLED"
        assert r.machine_human_agree is True, (fx.campaign_id, r.campaign_state, label)


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    failed = []
    for t in tests:
        try:
            t()
            passed += 1
            print(f"PASS  {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed.append((t.__name__, repr(e)))
            print(f"FAIL  {t.__name__}: {e!r}")
    print(f"\n{passed}/{len(tests)} passed")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(_run_all())
