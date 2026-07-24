"""
Brick 1 census — acceptance tests: deterministic/reproducible, and the materiality
findings are locked (no fabricated R can sneak in as a number or a bound).
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "phase0"))

brick1 = importlib.import_module("brick1_census")


def test_census_is_deterministic():
    a = brick1.build()
    b = brick1.build()
    assert a["camp_hash"] == b["camp_hash"]
    assert a["evt_hash"] == b["evt_hash"]
    assert a["sum_hash"] == b["sum_hash"]


def test_known_evidence_only_scenario_is_uncomputable_not_a_number():
    r = brick1.build()
    # 0 campaigns have a deterministically-supported realised R -> denominator 0 -> mean UNDEFINED
    assert r["included"] == 0
    assert r["denominator"] == 0
    assert r["mean_R"] is None              # never substituted with a fabricated number
    assert r["total_known_R"] == 0.0


def test_every_unresolved_event_has_a_named_reason():
    r = brick1.build()
    # no generic / empty category; total ambiguous == sum of named categories
    assert r["total_ambiguous"] == sum(r["cat_counts"].values())
    assert all(c and "unexplained" not in c.lower() for c in r["cat_counts"])


def test_corpus_counts():
    r = brick1.build()
    assert r["total_campaigns"] == 4
    assert r["fully"] + r["partial"] + r["unresolved"] == 4
