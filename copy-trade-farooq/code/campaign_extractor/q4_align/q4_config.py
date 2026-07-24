"""
Frozen, versioned, READ-ONLY Q4 threshold configuration — derived from the Q2B continuity capture.
Do NOT invent new thresholds. load_config() FAILS CLOSED (raises) if any required key is missing.

Provenance (Q2B session q1-20260701T142344Z, 588 events, ~5 min, one healthy session):
  worst-side provenance age: p99 = 509.071 ms, max = 1013.822 ms; inter-event gap max ~1.03 s.
Derivation:
  stale_warning_ms   = p99 worst-side age, rounded up to 50 ms      -> 550
  stale_rejection_ms = 1.5 x max worst-side age, rounded up 100 ms  -> 1600
  coverage_gap_ms    = max worst-side age rounded up to 100 ms      -> 1100
  max_match_delay_ms = stale_rejection_ms (first valid quote must land within the reject window) -> 1600
"""
from __future__ import annotations

CONFIG_VERSION = "q4-thresholds-v1"
SOURCE_SESSION = "q1-20260701T142344Z"          # Q2B 5-minute healthy capture

_FROZEN = {
    "stale_warning_ms": 550,
    "stale_rejection_ms": 1600,
    "coverage_gap_ms": 1100,
    "max_match_delay_ms": 1600,
    "xauusd_symbol_id": 41,
    "xauusd_digits": 2,
}

REQUIRED_KEYS = ("stale_warning_ms", "stale_rejection_ms", "coverage_gap_ms",
                 "max_match_delay_ms", "xauusd_symbol_id", "xauusd_digits")


class ThresholdConfigMissing(Exception):
    """Raised when the frozen threshold config is absent or incomplete (fail closed)."""


def load_config(override=None):
    """Return a validated copy of the frozen config. Raises ThresholdConfigMissing if any
    required key is absent/None. Pass `override` (a dict) only in tests to simulate a bad config."""
    cfg = dict(_FROZEN if override is None else override)
    for k in REQUIRED_KEYS:
        if cfg.get(k) is None:
            raise ThresholdConfigMissing(f"missing required threshold: {k}")
    cfg["config_version"] = CONFIG_VERSION
    cfg["source_session"] = SOURCE_SESSION
    return cfg
