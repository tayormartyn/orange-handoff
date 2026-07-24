"""
ASSOC-1 deterministic association engine. DECISION-ONLY — no campaign/leg/stop/order/broker
write capability exists or is reachable. Pure function over (candidate, campaign snapshots).

Order: preconditions (tracking, recognised intent, approved identity) then the strict
evidence hierarchy Rules 1..6, stopping at the first tier yielding exactly one valid,
non-conflicting campaign. Fail-closed everywhere; recency is NEVER used to establish
association.
"""
from __future__ import annotations
import os

import sys as _sys
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)
from _util import canonical_hash
import model as M

ENGINE_VERSION = "assoc-1.0"


def _fp_campaign(c):
    return [c.campaign_uid, c.provider_id, c.canonical_underlying_id, c.canonical_instrument_id,
            c.lifecycle_status]


def _decide(candidate, campaigns, *, status, rule, tier, associated_uid=None,
            candidates=None, context=None, review_reason=None, exclusion_reasons=None):
    considered = sorted(c.campaign_uid for c in campaigns)
    cand_sorted = sorted(candidates or ([] if associated_uid is None else [associated_uid]))
    decision = {
        "source_message_uid": candidate.source_message_uid,
        "provider_id": candidate.provider_id,
        "source_channel_id": candidate.immutable_channel_id,
        "source_message_timestamp": candidate.source_message_timestamp,
        "management_intent": candidate.management_intent,
        "association_status": status,
        "associated_campaign_uid": associated_uid,
        "candidate_campaign_uids": cand_sorted,
        "campaigns_considered": considered,
        "association_context": context,
        "exclusion_reasons": exclusion_reasons or {},
        "rule_fired": rule,
        "evidence_tier": tier,
        "evidence_references": list(candidate.evidence_references),
        "review_reason": review_reason,
        "engine_version": ENGINE_VERSION,
        # ASSOC-1 NEVER asserts that the instructed action occurred or that a broker confirmed it
        "instruction_executed": False,
        "broker_confirmed": False,
    }
    decision["decision_hash"] = canonical_hash({
        "msg": candidate.source_message_uid, "provider": candidate.provider_id,
        "channel": candidate.immutable_channel_id, "ts": candidate.source_message_timestamp,
        "intent": candidate.management_intent,
        "evidence": {"ref": candidate.explicit_campaign_reference,
                     "reply": candidate.reply_to_message_uid,
                     "quote": candidate.quoted_message_uid,
                     "ticket": candidate.screenshot_or_ticket_identity,
                     "underlying": candidate.explicit_instrument_underlying,
                     "instrument": candidate.explicit_instrument_id},
        "snapshot": sorted([_fp_campaign(c) for c in campaigns]),
        "status": status, "associated": associated_uid, "candidates": cand_sorted,
        "rule": rule, "tier": tier, "context": context, "engine": ENGINE_VERSION})
    decision["association_decision_uid"] = "adec_" + decision["decision_hash"][:16]
    return decision


def associate(candidate, campaigns):
    # ---------------- preconditions ----------------
    if candidate.provider_tracking_status_at_message_time != M.TRACKED_PROVIDER:
        return _decide(candidate, campaigns, status=M.REJECTED_UNTRACKED_PROVIDER,
                       rule=M.RULE_NONE, tier=M.TIER_NONE,
                       review_reason="provider tracking != TRACKED_PROVIDER at message time")
    if candidate.management_intent not in M.RECOGNISED_INTENTS:
        return _decide(candidate, campaigns, status=M.UNASSOCIATED, rule=M.RULE_NONE,
                       tier=M.TIER_NONE,
                       review_reason="unrecognised management intent (ordinary commentary)")
    if not candidate.source_identity_approved:
        return _decide(candidate, campaigns, status=M.UNASSOCIATED, rule=M.RULE_NONE,
                       tier=M.TIER_NONE,
                       review_reason="immutable sender/channel not approved for provider at "
                                     "message time (display-name match is insufficient)")

    own = [c for c in campaigns if c.provider_id == candidate.provider_id]

    def context_for(camp):
        return M.CTX_DIRECT if camp.lifecycle_accepts(candidate.management_intent) \
            else M.CTX_RETROSPECTIVE

    # ---------------- RULE 1: explicit campaign reference ----------------
    if candidate.explicit_campaign_reference:
        ref = candidate.explicit_campaign_reference
        match = [c for c in campaigns if c.campaign_uid == ref
                 or c.provider_campaign_reference == ref]
        if not match:
            return _decide(candidate, campaigns, status=M.UNASSOCIATED, rule=M.RULE_1,
                           tier=M.TIER_NONE,
                           review_reason="explicit reference does not resolve to a campaign")
        if all(c.provider_id != candidate.provider_id for c in match):
            return _decide(candidate, campaigns, status=M.REJECTED_PROVIDER_MISMATCH,
                           rule=M.RULE_1, tier=M.TIER_1,
                           review_reason="explicit reference belongs to another provider")
        mine = [c for c in match if c.provider_id == candidate.provider_id]
        if len(mine) == 1:
            return _decide(candidate, campaigns, status=M.ASSOCIATED, rule=M.RULE_1,
                           tier=M.TIER_1, associated_uid=mine[0].campaign_uid,
                           context=context_for(mine[0]))
        return _decide(candidate, campaigns, status=M.NEEDS_REVIEW, rule=M.RULE_1, tier=M.TIER_1,
                       candidates=[c.campaign_uid for c in mine],
                       review_reason="explicit reference resolves to multiple own campaigns")

    # ---------------- RULE 2: direct reply / thread linkage ----------------
    r = _by_linked(candidate, campaigns, candidate.reply_to_message_uid, M.RULE_2, M.TIER_2,
                   context_for)
    if r:
        return r
    # ---------------- RULE 3: quoted / exact referenced message identity ----------------
    r = _by_linked(candidate, campaigns, candidate.quoted_message_uid, M.RULE_3, M.TIER_3,
                   context_for)
    if r:
        return r

    # ---------------- RULE 4: explicit instrument + exactly one compatible open campaign ----
    if candidate.explicit_instrument_underlying:
        compat = [c for c in own if c.lifecycle_accepts(candidate.management_intent)
                  and _instrument_matches(c, candidate)]
        if len(compat) == 1:
            return _decide(candidate, campaigns, status=M.ASSOCIATED, rule=M.RULE_4,
                           tier=M.TIER_4, associated_uid=compat[0].campaign_uid,
                           context=M.CTX_DIRECT)
        if len(compat) > 1:
            return _decide(candidate, campaigns, status=M.NEEDS_REVIEW, rule=M.RULE_4,
                           tier=M.TIER_4, candidates=[c.campaign_uid for c in compat],
                           review_reason="explicit instrument matches multiple compatible "
                                         "campaigns")
        return _decide(candidate, campaigns, status=M.UNASSOCIATED, rule=M.RULE_4,
                       tier=M.TIER_NONE,
                       review_reason="explicit instrument resolves but no compatible campaign")

    # ---------------- RULE 5: screenshot / ticket identity ----------------
    if candidate.screenshot_or_ticket_identity:
        tid = candidate.screenshot_or_ticket_identity
        match = [c for c in campaigns if tid in (c.ticket_identities or ())]
        if all(c.provider_id != candidate.provider_id for c in match) and match:
            return _decide(candidate, campaigns, status=M.REJECTED_PROVIDER_MISMATCH,
                           rule=M.RULE_5, tier=M.TIER_5,
                           review_reason="ticket/screenshot identity belongs to another provider")
        mine = [c for c in match if c.provider_id == candidate.provider_id]
        if len(mine) == 1:
            return _decide(candidate, campaigns, status=M.ASSOCIATED, rule=M.RULE_5,
                           tier=M.TIER_5, associated_uid=mine[0].campaign_uid,
                           context=context_for(mine[0]))
        if len(mine) > 1:
            return _decide(candidate, campaigns, status=M.NEEDS_REVIEW, rule=M.RULE_5,
                           tier=M.TIER_5, candidates=[c.campaign_uid for c in mine],
                           review_reason="ticket/screenshot identity supports multiple campaigns")

    # ---------------- RULE 6: single compatible-campaign fallback (only no-instrument path) ----
    if not candidate.has_explicit_evidence():
        compat = [c for c in own if c.lifecycle_accepts(candidate.management_intent)]
        if len(compat) == 0:
            return _decide(candidate, campaigns, status=M.UNASSOCIATED, rule=M.RULE_NONE,
                           tier=M.TIER_NONE,
                           review_reason="no compatible open campaign for this provider")
        if len(compat) == 1:
            return _decide(candidate, campaigns, status=M.ASSOCIATED, rule=M.RULE_6,
                           tier=M.TIER_6, associated_uid=compat[0].campaign_uid,
                           context=M.CTX_DIRECT,
                           review_reason="single-compatible-campaign fallback (no explicit "
                                         "evidence; exactly one compatible open campaign)")
        # >1 — recency may ONLY order candidates for human review, never select
        ordered = [c.campaign_uid for c in
                   sorted(compat, key=lambda c: (c.opened_at or "", c.campaign_uid), reverse=True)]
        return _decide(candidate, campaigns, status=M.NEEDS_REVIEW, rule=M.RULE_NONE,
                       tier=M.TIER_NONE, candidates=ordered,
                       review_reason="multiple compatible open campaigns; evidence does not "
                                     "isolate one (recency used only to order for review)")

    return _decide(candidate, campaigns, status=M.UNASSOCIATED, rule=M.RULE_NONE,
                   tier=M.TIER_NONE,
                   review_reason="explicit evidence present but did not resolve a campaign")


def _by_linked(candidate, campaigns, message_uid, rule, tier, context_for):
    if not message_uid:
        return None
    match = [c for c in campaigns if message_uid in (c.linked_message_uids or ())]
    if not match:
        return None
    if all(c.provider_id != candidate.provider_id for c in match):
        return _decide(candidate, campaigns, status=M.REJECTED_PROVIDER_MISMATCH, rule=rule,
                       tier=tier, review_reason="linked/quoted message belongs to another provider")
    mine = [c for c in match if c.provider_id == candidate.provider_id]
    if len(mine) == 1:
        return _decide(candidate, campaigns, status=M.ASSOCIATED, rule=rule, tier=tier,
                       associated_uid=mine[0].campaign_uid, context=context_for(mine[0]))
    return _decide(candidate, campaigns, status=M.NEEDS_REVIEW, rule=rule, tier=tier,
                   candidates=[c.campaign_uid for c in mine],
                   review_reason="linked/quoted message resolves to multiple own campaigns")


def _instrument_matches(campaign, candidate):
    if candidate.explicit_instrument_id and campaign.canonical_instrument_id:
        return campaign.canonical_instrument_id == candidate.explicit_instrument_id
    return campaign.canonical_underlying_id == candidate.explicit_instrument_underlying
