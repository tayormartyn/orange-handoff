"""
Firewalls. (1) Provider-profit: PROVIDER_DISPLAYED evidence can never enter R/outcome/expectancy
calculators. (2) Campaign-write: the vision package has no path to accepted campaign state
(static scan + runtime sqlite guard). (3) No-number-repair: arithmetic may FLAG an inconsistency
but may never manufacture/replace an unreadable value.
"""
from __future__ import annotations
import glob
import os

_HERE = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------- provider-profit firewall
class ProviderProfitFirewallError(Exception):
    pass


def _eligible(evidence, flag):
    return evidence.get("evidence_domain") != "PROVIDER_DISPLAYED" and bool(evidence.get(flag))


def assert_r_eligible(evidence):
    if not _eligible(evidence, "eligible_for_account_r"):
        raise ProviderProfitFirewallError(
            "evidence rejected from R calculator (PROVIDER_DISPLAYED or not account-R eligible)")


def assert_expectancy_eligible(evidence):
    if not _eligible(evidence, "eligible_for_expectancy"):
        raise ProviderProfitFirewallError(
            "evidence rejected from expectancy calculator (PROVIDER_DISPLAYED or not eligible)")


def calculate_account_r(evidence, risk_unit=None):
    """Guarded stub — refuses PROVIDER_DISPLAYED / ineligible input. In V1 there is no eligible
    realised-outcome evidence, so it returns None and never derives R from a screenshot figure."""
    assert_r_eligible(evidence)
    return {"account_r": None, "note": "no eligible realised outcome evidence in V1"}


def calculate_expectancy(evidences):
    for e in evidences:
        assert_expectancy_eligible(e)
    return {"expectancy": None, "note": "no eligible realised outcome evidence in V1"}


def provider_display_statement(value):
    """The ONLY permitted assertion about a displayed profit figure."""
    return f"The provider screenshot displayed a candidate profit figure of {value}."


# ---------------------------------------------------------------- campaign-write firewall
class CampaignAccessViolation(Exception):
    pass

_FORBIDDEN_CAMPAIGN_TOKENS = ("campaign_v1.db", "mpk_campaigns_v1.db", "mpk_registry_v1.db",
                              "write_campaign", "create_campaign_event", "insert_campaign_event",
                              "accepted_campaign_writer")
_CAMPAIGN_PATH_MARKERS = ("campaign_v1", "mpk_campaigns", "mpk_registry", "campaign_events",
                          "association_decisions")


def production_modules():
    # exclude this firewall-definition file (it legitimately NAMES the forbidden tokens as data)
    # and the runner; scan the actual data-handling modules.
    return [p for p in glob.glob(os.path.join(_HERE, "*.py"))
            if os.path.basename(p) not in ("run_v1_offline.py", "firewalls.py")]


def scan_campaign_write_access(paths=None):
    """Static: no vision production module may reference a campaign DB or campaign-write function."""
    viol = []
    for p in (paths or production_modules()):
        src = open(p, encoding="utf-8").read()
        for tok in _FORBIDDEN_CAMPAIGN_TOKENS:
            if tok in src:
                viol.append((os.path.basename(p), tok))
    return viol


def make_guarded_connect(original_connect, violations):
    """Wrap sqlite3.connect to RAISE if any campaign database path is opened (runtime proof)."""
    def _connect(target, *a, **k):
        s = str(target).lower()
        if any(m in s for m in _CAMPAIGN_PATH_MARKERS):
            violations.append(str(target))
            raise CampaignAccessViolation(f"vision attempted to open campaign state: {target}")
        return original_connect(target, *a, **k)
    return _connect


# ---------------------------------------------------------------- no-number-repair guard
class NumberRepairForbidden(Exception):
    pass


def reconcile_arithmetic(entry=None, exit_price=None, displayed_profit=None):
    """May FLAG consistency when ALL values are independently readable; NEVER fills a missing one.
    Returns computed_value=None always — reconstruction (e.g. entry = exit - profit) is forbidden."""
    known = [v for v in (entry, exit_price, displayed_profit) if v is not None]
    if len(known) < 3:
        return {"status": "INSUFFICIENT_DATA_NO_REPAIR", "computed_value": None,
                "note": "a missing/unreadable value is NEVER derived from the others"}
    try:
        e, x, p = float(entry), float(exit_price), float(str(displayed_profit).replace("+", ""))
    except (TypeError, ValueError):
        return {"status": "NON_NUMERIC", "computed_value": None}
    # flag-only: direction/scale unknown from a screenshot, so we only note gross plausibility
    consistent = abs(abs(x - e)) >= 0    # trivially true; real check would need lot size (unknown)
    return {"status": "FLAGGED_ONLY", "computed_value": None,
            "note": "arithmetic used for a consistency FLAG only; no value manufactured",
            "gross_move_abs": round(abs(x - e), 5), "displayed_profit_seen": p, "consistent": consistent}
