"""
Demo-account safety validator (for the LATER A2 discovery step). OFFLINE — operates on a
supplied account list (no connection, no discovery here). A1 NEVER selects, guesses, or
hard-codes an account id; selection of the £10k demo is a human step in A2.

Rules:
  * require isLive == False (demo); any live/unknown account is rejected for selection;
  * 0 demo  -> NO_DEMO_ACCOUNT;
  * 1 demo  -> SINGLE_DEMO_CANDIDATE (still requires human confirmation in A2);
  * >1 demo -> NEEDS_HUMAN_SELECTION (return all candidate ids; never auto-pick, never by balance);
  * `selected` is ALWAYS None at A1.
"""
from __future__ import annotations


def validate_demo_selection(accounts):
    """accounts: list of dicts each with 'account_id' and 'isLive' (bool). Returns a verdict
    dict with status, candidates, selected(None). Account ids are returned only for routing the
    later human choice — never auto-selected."""
    if accounts is None:
        accounts = []
    demo = [a for a in accounts if a.get("isLive") is False]
    has_live = any(a.get("isLive") is True for a in accounts)
    candidates = [a.get("account_id") for a in demo]
    if not demo:
        status = "REJECTED_LIVE_ONLY" if has_live else "NO_DEMO_ACCOUNT"
        return {"status": status, "candidates": [], "selected": None,
                "reason": "no isLive=false account available"}
    if len(demo) == 1:
        return {"status": "SINGLE_DEMO_CANDIDATE", "candidates": candidates, "selected": None,
                "reason": "one demo account; A2 must human-confirm before authenticating"}
    return {"status": "NEEDS_HUMAN_SELECTION", "candidates": candidates, "selected": None,
            "reason": "multiple demo accounts; human must choose (never auto/recency/balance)"}
