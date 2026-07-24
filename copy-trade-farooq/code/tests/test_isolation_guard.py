"""Isolation guard: running the console/accelerator test suites must NOT write to the real
review/status/link directory, must not change any real sidecar hash, and must never recreate the
synthetic intake-41a2e5a0 in the real effective-status stream — even across repeated runs."""
from __future__ import annotations
import hashlib
import importlib
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

REVIEW_DIR = os.path.join(_ROOT, "data", "manual_image_intake_v1", "review")
STATUS_LOG = os.path.join(REVIEW_DIR, "effective_status_events.jsonl")
SYNTHETIC = "intake-41a2e5a0a8d56565"


def _snapshot():
    snap = {}
    if os.path.isdir(REVIEW_DIR):
        for fn in sorted(os.listdir(REVIEW_DIR)):
            p = os.path.join(REVIEW_DIR, fn)
            if os.path.isfile(p):
                snap[fn] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return snap


def _run_suite(modname):
    T = importlib.import_module(modname)
    for n in sorted(x for x in dir(T) if x.startswith("test_")):
        getattr(T, n)()


def test_suites_do_not_mutate_real_review_dir():
    before = _snapshot()
    for _ in range(2):                                  # repeated runs must not re-pollute
        _run_suite("test_console")
        _run_suite("test_console_accelerator")
        _run_suite("test_console_provider_cohort")
    after = _snapshot()
    assert before == after, f"real review dir changed: {set(before) ^ set(after)} / hash diffs"


def test_no_synthetic_in_real_status_stream():
    if os.path.exists(STATUS_LOG):
        assert SYNTHETIC not in open(STATUS_LOG, encoding="utf-8").read()


def test_no_synthetic_manifest_or_review_leaked():
    for fn in (os.listdir(REVIEW_DIR) if os.path.isdir(REVIEW_DIR) else []):
        assert SYNTHETIC not in fn
    mdir = os.path.join(_ROOT, "data", "manual_image_intake_v1", "manifests")
    for fn in (os.listdir(mdir) if os.path.isdir(mdir) else []):
        assert SYNTHETIC not in fn
