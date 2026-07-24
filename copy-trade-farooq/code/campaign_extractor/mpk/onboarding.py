"""
MPK-2A provider-onboarding service — deterministic, insert-only, transactional.

All state changes are append-only records or administrative events. There are NO public
UPDATE/DELETE methods. Identity is always a stable provider_id + immutable platform/
channel/sender IDs; display names / usernames / channel titles / nicknames are display
metadata only and never identity. Conflicting identity assignments fail closed (block,
return NEEDS_REVIEW) and leave no partial rows.

Imports nothing from the live listener / broker / exchange / credential paths.
"""
from __future__ import annotations
import hashlib
import os

import sys as _sys
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)
from appendonly import canonical_hash
from registry_db import RegistryDB, SCHEMA_VERSION as REGISTRY_SCHEMA_VERSION
import gates as G


class OnboardingConflict(Exception):
    """Fail-closed: a conflicting/ambiguous identity operation (NEEDS_REVIEW)."""


def _det(prefix, *parts):
    return prefix + hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:16]


class OnboardingService:
    def __init__(self, reg: RegistryDB):
        self.reg = reg
        self.con = reg.con

    # -- internal: admin event (no commit; caller controls the transaction) ---
    def _admin(self, etype, *, subject_provider_id=None, payload=None, effective_from=None,
               actor="system", key=""):
        self.reg.append_administrative_event(
            admin_event_id=_det("adm_", etype, subject_provider_id, key, effective_from),
            admin_event_type=etype, subject_provider_id=subject_provider_id, payload=payload,
            effective_from_utc=effective_from, actor=actor, created_at_utc=effective_from,
            commit=False)

    # =========================================================== providers
    def register_provider(self, *, provider_id, display_name, effective_from, actor="martyn",
                          notes=None):
        existing = self.con.execute(
            "SELECT display_name FROM providers WHERE provider_id=?", (provider_id,)).fetchone()
        if existing is not None:
            if existing[0] != display_name:
                raise OnboardingConflict(
                    f"provider {provider_id} exists with different display_name "
                    f"{existing[0]!r}; identity is provider_id — refusing overwrite")
            return "ALREADY_PRESENT"
        self.reg.begin()
        try:
            self.reg.append_provider(provider_id=provider_id, display_name=display_name,
                                     added_at_utc=effective_from, notes=notes, commit=False)
            self.reg._append("provider_status_events", self._status_rec(
                provider_id, G.STATUS_ACTIVE, effective_from, "registered"), commit=False)
            self._admin("PROVIDER_REGISTERED", subject_provider_id=provider_id,
                        payload=f"display_name={display_name}", effective_from=effective_from,
                        actor=actor)
            self.reg.commit()
        except Exception:
            self.reg.rollback()
            raise
        return "REGISTERED"

    def _status_rec(self, provider_id, status, effective_from, reason):
        rec = {"status_event_id": _det("pst_", provider_id, status, effective_from),
               "provider_id": provider_id, "status": status, "effective_from": effective_from,
               "reason": reason, "created_at": effective_from}
        rec["event_hash"] = canonical_hash(rec)
        return rec

    def pause_provider(self, *, provider_id, effective_from, reason=None, actor="martyn"):
        self._require_provider(provider_id)
        self.reg.begin()
        try:
            self.reg._append("provider_status_events",
                             self._status_rec(provider_id, G.STATUS_PAUSED, effective_from, reason),
                             commit=False)
            self._admin("PROVIDER_PAUSED", subject_provider_id=provider_id,
                        effective_from=effective_from, actor=actor, key="pause")
            self.reg.commit()
        except Exception:
            self.reg.rollback(); raise

    def retire_provider(self, *, provider_id, effective_from, reason=None, actor="martyn"):
        self._require_provider(provider_id)
        self.reg.begin()
        try:
            self.reg._append("provider_status_events",
                             self._status_rec(provider_id, G.STATUS_RETIRED, effective_from, reason),
                             commit=False)
            self._admin("PROVIDER_RETIRED", subject_provider_id=provider_id,
                        effective_from=effective_from, actor=actor, key="retire")
            self.reg.commit()
        except Exception:
            self.reg.rollback(); raise

    def _require_provider(self, provider_id):
        if self.con.execute("SELECT 1 FROM providers WHERE provider_id=?",
                            (provider_id,)).fetchone() is None:
            raise OnboardingConflict(f"unknown provider {provider_id}")

    # =========================================================== aliases / sender IDs
    def add_alias(self, *, provider_id, platform, sender_identifier, verification_status,
                  effective_from, actor="martyn"):
        self._require_provider(provider_id)
        # an immutable sender identity may not silently switch providers
        other = self.con.execute(
            "SELECT provider_id FROM provider_aliases WHERE platform=? AND sender_identifier=? "
            "AND provider_id<>? AND effective_to_utc IS NULL", (platform, sender_identifier,
                                                                provider_id)).fetchone()
        if other is not None:
            raise OnboardingConflict(
                f"alias {sender_identifier!r} already active for {other[0]} — NEEDS_REVIEW")
        self.reg.begin()
        try:
            self.reg.append_provider_alias(
                alias_id=_det("ali_", provider_id, platform, sender_identifier, effective_from),
                provider_id=provider_id, platform=platform, sender_identifier=sender_identifier,
                verification_status=verification_status, effective_from_utc=effective_from,
                commit=False)
            self._admin("PROVIDER_ALIAS_ADDED", subject_provider_id=provider_id,
                        payload=f"{platform}:{sender_identifier}", effective_from=effective_from,
                        actor=actor, key=sender_identifier)
            self.reg.commit()
        except Exception:
            self.reg.rollback(); raise

    def assign_sender_id(self, *, provider_id, platform, immutable_sender_id, effective_from,
                         effective_to=None, actor="martyn"):
        self._require_provider(provider_id)
        active_other = self.con.execute(
            "SELECT provider_id FROM provider_sender_assignments WHERE platform=? "
            "AND immutable_sender_id=? AND effective_to IS NULL AND provider_id<>?",
            (platform, immutable_sender_id, provider_id)).fetchone()
        if active_other is not None:
            raise OnboardingConflict(
                f"sender {immutable_sender_id} already assigned to {active_other[0]} — NEEDS_REVIEW")
        rec = {"assignment_id": _det("snd_", provider_id, platform, immutable_sender_id,
                                     effective_from),
               "provider_id": provider_id, "platform": platform,
               "immutable_sender_id": immutable_sender_id, "effective_from": effective_from,
               "effective_to": effective_to, "created_at": effective_from}
        rec["assignment_hash"] = canonical_hash(rec)
        self.reg.begin()
        try:
            self.reg._append("provider_sender_assignments", rec, commit=False)
            self._admin("PROVIDER_SENDER_ID_ASSIGNED", subject_provider_id=provider_id,
                        payload=f"{platform}:{immutable_sender_id}", effective_from=effective_from,
                        actor=actor, key=immutable_sender_id)
            self.reg.commit()
        except Exception:
            self.reg.rollback(); raise

    # =========================================================== channels
    def assign_channel(self, *, provider_id, platform, immutable_channel_id, effective_from,
                       channel_title=None, effective_to=None, actor="martyn"):
        self._require_provider(provider_id)
        # one active immutable channel cannot belong to two providers at the same effective time
        active_other = self.con.execute(
            "SELECT provider_id FROM provider_channels WHERE platform=? AND immutable_channel_id=? "
            "AND effective_to_utc IS NULL AND provider_id<>?",
            (platform, immutable_channel_id, provider_id)).fetchone()
        if active_other is not None:
            raise OnboardingConflict(
                f"channel {immutable_channel_id} already active for {active_other[0]} — NEEDS_REVIEW")
        self.reg.begin()
        try:
            self.reg.append_provider_channel(
                channel_assignment_id=_det("chn_", provider_id, platform, immutable_channel_id,
                                           effective_from),
                provider_id=provider_id, platform=platform,
                immutable_channel_id=immutable_channel_id,
                channel_title_for_display_only=channel_title, effective_from_utc=effective_from,
                effective_to_utc=effective_to, commit=False)
            self._admin("PROVIDER_CHANNEL_ASSIGNED", subject_provider_id=provider_id,
                        payload=f"{platform}:{immutable_channel_id}", effective_from=effective_from,
                        actor=actor, key=immutable_channel_id)
            self.reg.commit()
        except Exception:
            self.reg.rollback(); raise

    # =========================================================== permissions (two gates)
    def _latest_snapshot(self, provider_id, channel_id):
        row = self.con.execute(
            "SELECT capture_status, tracking_status FROM channel_permission_events "
            "WHERE provider_id=? AND immutable_channel_id=? "
            "ORDER BY effective_from_utc DESC, created_at_utc DESC, permission_event_id DESC "
            "LIMIT 1", (provider_id, channel_id)).fetchone()
        return row if row else (G.DEFAULT_CAPTURE, G.DEFAULT_TRACKING)

    def _record_permission(self, provider_id, channel_id, capture_status, tracking_status,
                           platform, effective_from, reason, etype, actor):
        if capture_status not in G.CAPTURE_STATES:
            raise OnboardingConflict(f"invalid capture_status {capture_status!r}")
        if tracking_status not in G.TRACK_STATES:
            raise OnboardingConflict(f"invalid tracking_status {tracking_status!r}")
        self.reg.begin()
        try:
            self.reg.append_channel_permission_event(
                permission_event_id=_det("prm_", provider_id, channel_id, capture_status,
                                         tracking_status, effective_from),
                provider_id=provider_id, platform=platform, immutable_channel_id=channel_id,
                capture_status=capture_status, tracking_status=tracking_status,
                effective_from_utc=effective_from, reason=reason, created_at_utc=effective_from,
                commit=False)
            self._admin(etype, subject_provider_id=provider_id,
                        payload=f"capture={capture_status} tracking={tracking_status} ch={channel_id}",
                        effective_from=effective_from, actor=actor,
                        key=f"{channel_id}:{capture_status}:{tracking_status}")
            self.reg.commit()
        except Exception:
            self.reg.rollback(); raise

    def record_capture_permission(self, *, provider_id, capture_status, effective_from,
                                  channel_id=G.PROVIDER_WIDE, platform="TELEGRAM", reason=None,
                                  actor="martyn"):
        # change ONLY capture; carry current tracking forward (gates are independent)
        _, cur_tracking = self._latest_snapshot(provider_id, channel_id)
        self._require_provider(provider_id)
        self._record_permission(provider_id, channel_id, capture_status, cur_tracking, platform,
                                effective_from, reason, "CAPTURE_PERMISSION_CHANGED", actor)

    def record_tracking_permission(self, *, provider_id, tracking_status, effective_from,
                                   channel_id=G.PROVIDER_WIDE, platform="TELEGRAM", reason=None,
                                   actor="martyn"):
        # change ONLY tracking; carry current capture forward
        cur_capture, _ = self._latest_snapshot(provider_id, channel_id)
        self._require_provider(provider_id)
        self._record_permission(provider_id, channel_id, cur_capture, tracking_status, platform,
                                effective_from, reason, "TRACKING_PERMISSION_CHANGED", actor)

    # =========================================================== source-candidate intake
    def record_source_candidate(self, *, platform, immutable_sender_id=None,
                                immutable_channel_id=None, observed_display_name=None,
                                observed_username=None, observed_channel_title=None,
                                evidence_reference=None, first_observed_at, actor="system"):
        candidate_uid = _det("cand_", platform, immutable_sender_id, immutable_channel_id)
        rec = self._candidate_rec(
            candidate_uid=candidate_uid, platform=platform,
            immutable_sender_id=immutable_sender_id, immutable_channel_id=immutable_channel_id,
            observed_display_name=observed_display_name, observed_username=observed_username,
            observed_channel_title=observed_channel_title, first_observed_at=first_observed_at,
            last_observed_at=first_observed_at, evidence_reference=evidence_reference,
            proposed_provider_id=None, identity_status="UNVERIFIED", review_status="NEEDS_REVIEW",
            supersedes_rowseq=None)
        self.reg.begin()
        try:
            self.reg._append("source_candidates", rec, commit=False)
            self._admin("SOURCE_CANDIDATE_RECORDED", payload=f"{platform}:{immutable_sender_id}",
                        effective_from=first_observed_at, actor=actor, key=candidate_uid)
            self.reg.commit()
        except Exception:
            self.reg.rollback(); raise
        return candidate_uid

    def _current_candidate(self, candidate_uid):
        return self.con.execute(
            "SELECT rowseq, identity_status, review_status, proposed_provider_id FROM "
            "source_candidates WHERE candidate_uid=? ORDER BY rowseq DESC LIMIT 1",
            (candidate_uid,)).fetchone()

    def _candidate_rec(self, **f):
        rec = {k: f.get(k) for k in (
            "candidate_uid", "platform", "immutable_sender_id", "immutable_channel_id",
            "observed_display_name", "observed_username", "observed_channel_title",
            "first_observed_at", "last_observed_at", "evidence_reference", "proposed_provider_id",
            "identity_status", "review_status", "supersedes_rowseq")}
        rec["created_at"] = f.get("first_observed_at")
        rec["schema_version"] = REGISTRY_SCHEMA_VERSION
        rec["candidate_hash"] = canonical_hash(rec)
        return rec

    def verify_source_candidate(self, *, candidate_uid, proposed_provider_id, effective_from,
                                actor="martyn"):
        cur = self._current_candidate(candidate_uid)
        if cur is None:
            raise OnboardingConflict(f"unknown candidate {candidate_uid}")
        base = self.con.execute("SELECT * FROM source_candidates WHERE rowseq=?",
                                (cur[0],)).fetchone()
        names = [d[0] for d in self.con.execute(
            "SELECT * FROM source_candidates WHERE rowseq=?", (cur[0],)).description]
        b = dict(zip(names, base))
        rec = self._candidate_rec(
            candidate_uid=candidate_uid, platform=b["platform"],
            immutable_sender_id=b["immutable_sender_id"],
            immutable_channel_id=b["immutable_channel_id"],
            observed_display_name=b["observed_display_name"],
            observed_username=b["observed_username"],
            observed_channel_title=b["observed_channel_title"],
            first_observed_at=b["first_observed_at"], last_observed_at=effective_from,
            evidence_reference=b["evidence_reference"], proposed_provider_id=proposed_provider_id,
            identity_status="VERIFIED", review_status="VERIFIED", supersedes_rowseq=cur[0])
        self.reg.begin()
        try:
            self.reg._append("source_candidates", rec, commit=False)
            self._admin("SOURCE_IDENTITY_VERIFIED", subject_provider_id=proposed_provider_id,
                        payload=candidate_uid, effective_from=effective_from, actor=actor,
                        key=f"{candidate_uid}:verify")
            self.reg.commit()
        except Exception:
            self.reg.rollback(); raise

    def reject_source_candidate(self, *, candidate_uid, effective_from, reason=None,
                                actor="martyn"):
        cur = self._current_candidate(candidate_uid)
        if cur is None:
            raise OnboardingConflict(f"unknown candidate {candidate_uid}")
        base = self.con.execute("SELECT * FROM source_candidates WHERE rowseq=?",
                                (cur[0],)).fetchone()
        names = [d[0] for d in self.con.execute(
            "SELECT * FROM source_candidates WHERE rowseq=?", (cur[0],)).description]
        b = dict(zip(names, base))
        rec = self._candidate_rec(
            candidate_uid=candidate_uid, platform=b["platform"],
            immutable_sender_id=b["immutable_sender_id"],
            immutable_channel_id=b["immutable_channel_id"],
            observed_display_name=b["observed_display_name"], observed_username=b["observed_username"],
            observed_channel_title=b["observed_channel_title"],
            first_observed_at=b["first_observed_at"], last_observed_at=effective_from,
            evidence_reference=b["evidence_reference"], proposed_provider_id=None,
            identity_status="REJECTED", review_status="REJECTED", supersedes_rowseq=cur[0])
        self.reg.begin()
        try:
            self.reg._append("source_candidates", rec, commit=False)
            self._admin("SOURCE_IDENTITY_REJECTED", payload=candidate_uid,
                        effective_from=effective_from, actor=actor, key=f"{candidate_uid}:reject")
            self.reg.commit()
        except Exception:
            self.reg.rollback(); raise

    # -- read helpers ---------------------------------------------------------
    def distinct_source_candidates(self):
        return self.con.execute(
            "SELECT COUNT(DISTINCT candidate_uid) FROM source_candidates").fetchone()[0]
