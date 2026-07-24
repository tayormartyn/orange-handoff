"""
Two-gate model tests: capture (channel) vs mutation (sender). Passing capture must NEVER
imply passing mutation. wazwithazed stays CONTEXT_ONLY.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from prospective.gates import capture_allowed, mutation_allowed, sender_status

ALLOWLIST = [-1001902136163]


def test_capture_gate_channel_only():
    assert capture_allowed(-1001902136163, ALLOWLIST) is True
    assert capture_allowed(-100999, ALLOWLIST) is False


def test_mutation_gate_farouk_only():
    assert mutation_allowed("seascalperfarouk") is True
    assert mutation_allowed("wazwithazed") is False
    assert mutation_allowed("kyledoops") is False
    assert mutation_allowed(None) is False


def test_capture_does_not_imply_mutation():
    # wazwithazed in an allowlisted channel: capture YES, mutation NO
    assert capture_allowed(-1001902136163, ALLOWLIST) is True
    assert mutation_allowed("wazwithazed") is False


def test_sender_status_context_only_vs_tracked():
    assert sender_status("seascalperfarouk") == "TRACKED"
    assert sender_status("wazwithazed") == "CONTEXT_ONLY"
    assert sender_status("kyledoops") == "CONTEXT_ONLY"


def test_explicitly_approved_sender_may_mutate():
    # only if Martyn explicitly approves a sender as tracked
    assert mutation_allowed("wazwithazed", tracked_senders={"wazwithazed"}) is True
    assert sender_status("wazwithazed", tracked_senders={"wazwithazed"}) == "TRACKED"
