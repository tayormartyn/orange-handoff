"""ASSOC-1 domain model: inputs, snapshots, ordinal evidence tiers, and compatibility."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

# ---- association statuses (closed set; no generic "probably associated") ----
ASSOCIATED = "ASSOCIATED"
NEEDS_REVIEW = "NEEDS_REVIEW"
UNASSOCIATED = "UNASSOCIATED"
REJECTED_PROVIDER_MISMATCH = "REJECTED_PROVIDER_MISMATCH"
REJECTED_UNTRACKED_PROVIDER = "REJECTED_UNTRACKED_PROVIDER"
STATUSES = (ASSOCIATED, NEEDS_REVIEW, UNASSOCIATED, REJECTED_PROVIDER_MISMATCH,
            REJECTED_UNTRACKED_PROVIDER)

# ---- ordinal evidence tiers (NO probabilistic confidence) ----
TIER_1 = "TIER_1_EXPLICIT_REFERENCE"
TIER_2 = "TIER_2_REPLY_LINK"
TIER_3 = "TIER_3_QUOTED_IDENTITY"
TIER_4 = "TIER_4_EXPLICIT_INSTRUMENT"
TIER_5 = "TIER_5_SCREENSHOT_TICKET"
TIER_6 = "TIER_6_SINGLE_CAMPAIGN_FALLBACK"
TIER_NONE = "NONE"

# ---- rules ----
RULE_1 = "RULE_1_EXPLICIT_CAMPAIGN_REFERENCE"
RULE_2 = "RULE_2_DIRECT_REPLY_LINKAGE"
RULE_3 = "RULE_3_QUOTED_MESSAGE_IDENTITY"
RULE_4 = "RULE_4_EXPLICIT_INSTRUMENT_UNIQUE_CAMPAIGN"
RULE_5 = "RULE_5_SCREENSHOT_OR_TICKET_IDENTITY"
RULE_6 = "RULE_6_SINGLE_COMPATIBLE_CAMPAIGN_FALLBACK"
RULE_NONE = "NONE"

# ---- association context ----
CTX_DIRECT = "DIRECT"
CTX_RETROSPECTIVE = "RETROSPECTIVE_EVIDENCE"

# ---- tracking permission (Gate B; supplied at message time by deterministic upstream) ----
TRACKED_PROVIDER = "TRACKED_PROVIDER"

# ---- lifecycle ----
OPEN, PENDING, CLOSING, CLOSED = "OPEN", "PENDING", "CLOSING", "CLOSED"

# ---- recognised management intents + the lifecycle states that can logically accept them ----
INTENT_COMPATIBLE_STATES = {
    "MOVE_STOP_TO_ENTRY": {OPEN},
    "PARTIAL_CLOSE_INSTRUCTION": {OPEN},
    "HOLD_REMAINDER": {OPEN},
    "RISK_FREE_CLAIM": {OPEN},
    "CLOSE_POSITION_INSTRUCTION": {OPEN, CLOSING},
    "CAMPAIGN_EXIT_REPORTED": {OPEN, CLOSING},
    "TP_HIT_REPORTED": {OPEN, CLOSING},
    "STOP_HIT_REPORTED": {OPEN, CLOSING},
    "CANCEL_PLAN": {PENDING},
}
RECOGNISED_INTENTS = frozenset(INTENT_COMPATIBLE_STATES)


@dataclass
class ManagementCandidate:
    source_message_uid: str
    provider_id: str
    management_intent: str
    source_message_timestamp: str
    immutable_channel_id: Optional[str] = None
    immutable_sender_id: Optional[str] = None
    source_platform: str = "TELEGRAM"
    # Gate B tracking status AS IT WAS at message time (never the provider's current status)
    provider_tracking_status_at_message_time: str = "DENIED"
    # Precondition C: immutable sender+channel approved for this provider at message time
    source_identity_approved: bool = False
    raw_message_reference: Optional[str] = None
    # evidence (all optional; supplied by deterministic upstream fixtures)
    explicit_campaign_reference: Optional[str] = None
    reply_to_message_uid: Optional[str] = None
    quoted_message_uid: Optional[str] = None
    screenshot_or_ticket_identity: Optional[str] = None
    # INST-1 result (already resolved upstream): a single supportable underlying, optional instrument
    explicit_instrument_underlying: Optional[str] = None
    explicit_instrument_id: Optional[str] = None
    evidence_references: list = field(default_factory=list)
    provenance: str = "FIXTURE"
    parser_or_candidate_version: str = "fixture-0"

    def has_explicit_evidence(self):
        return any((self.explicit_campaign_reference, self.reply_to_message_uid,
                    self.quoted_message_uid, self.screenshot_or_ticket_identity,
                    self.explicit_instrument_underlying))


@dataclass
class CampaignSnapshot:
    campaign_uid: str
    provider_id: str
    lifecycle_status: str = OPEN
    canonical_underlying_id: Optional[str] = None
    canonical_instrument_id: Optional[str] = None
    direction: Optional[str] = None
    origin_channel_id: Optional[str] = None
    provider_campaign_reference: Optional[str] = None
    linked_message_uids: tuple = ()
    ticket_identities: tuple = ()
    opened_at: Optional[str] = None

    def lifecycle_accepts(self, intent):
        return self.lifecycle_status in INTENT_COMPATIBLE_STATES.get(intent, set())
