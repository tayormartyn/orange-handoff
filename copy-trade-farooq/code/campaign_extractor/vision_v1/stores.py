"""
Layer 1 (CandidateDB -> data/media_candidates_v1.db) and Layer 2 (ReviewDB ->
data/media_reviews_v1.db). Strictly separate SQLite files. Neither opens or references any
campaign database. Typed CHECK constraints reject unknown enums / evidence domains (fail closed).
"""
from __future__ import annotations
import json
import os
import sqlite3
import time

from __init__ import (REGION_TYPES, FIELD_TYPES, EVIDENCE_DOMAINS, REVIEW_STATUSES, DUAL_STATES,
                      SEMANTICS, REVIEW_DECISIONS)

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CANDIDATES_DB = os.path.join(_ROOT, "data", "media_candidates_v1.db")
REVIEWS_DB = os.path.join(_ROOT, "data", "media_reviews_v1.db")


def _in(vals):
    return "(" + ",".join(f"'{v}'" for v in vals) + ")"


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


_CANDIDATE_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS ingested_images (
  media_id TEXT PRIMARY KEY, source_message_id TEXT, source_timestamp TEXT,
  original_path TEXT NOT NULL, sha256 TEXT NOT NULL UNIQUE, mime_type TEXT,
  file_size INTEGER, pixel_width INTEGER, pixel_height INTEGER, ingested_at TEXT);
CREATE TABLE IF NOT EXISTS derived_artifacts (
  artifact_id TEXT PRIMARY KEY, media_id TEXT NOT NULL, original_sha256 TEXT NOT NULL,
  artifact_type TEXT NOT NULL, sha256 TEXT NOT NULL, region_id TEXT);
CREATE TABLE IF NOT EXISTS regions (
  region_id TEXT PRIMARY KEY, media_id TEXT NOT NULL,
  region_type TEXT NOT NULL CHECK (region_type IN {_in(REGION_TYPES)}),
  bbox TEXT, crop_path TEXT, crop_sha256 TEXT, detection_confidence REAL, extractor_version TEXT);
CREATE TABLE IF NOT EXISTS field_candidates (
  candidate_field_id TEXT PRIMARY KEY, media_id TEXT NOT NULL, region_id TEXT NOT NULL,
  field_type TEXT NOT NULL CHECK (field_type IN {_in(FIELD_TYPES)}),
  raw_visible_text TEXT, candidate_value_string TEXT, accepted_normalised_value TEXT,
  bbox TEXT, crop_sha256 TEXT, extractor_confidence REAL, alternative_readings TEXT,
  extraction_method_version TEXT,
  review_status TEXT NOT NULL DEFAULT 'PENDING' CHECK (review_status IN {_in(REVIEW_STATUSES)}),
  evidence_domain TEXT NOT NULL CHECK (evidence_domain IN {_in(EVIDENCE_DOMAINS)}),
  dual_reading_state TEXT CHECK (dual_reading_state IS NULL OR dual_reading_state IN {_in(DUAL_STATES)}),
  eligible_for_shadow_outcome INTEGER NOT NULL DEFAULT 0,
  eligible_for_demo_outcome INTEGER NOT NULL DEFAULT 0,
  eligible_for_account_r INTEGER NOT NULL DEFAULT 0,
  eligible_for_expectancy INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS image_semantics (
  media_id TEXT PRIMARY KEY,
  classification TEXT NOT NULL CHECK (classification IN {_in(SEMANTICS)}),
  management_candidates TEXT, has_clean_entry_range INTEGER NOT NULL DEFAULT 0,
  is_clean_new_entry_signal INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS crops (
  crop_id TEXT PRIMARY KEY, media_id TEXT NOT NULL, original_sha256 TEXT NOT NULL,
  region_type TEXT NOT NULL, parent_region_id TEXT, field_type TEXT,
  bbox TEXT NOT NULL, crop_path TEXT NOT NULL, crop_sha256 TEXT NOT NULL UNIQUE,
  crop_width INTEGER, crop_height INTEGER, crop_created_at TEXT, crop_tool_version TEXT);
CREATE TABLE IF NOT EXISTS second_readings (
  reading_id TEXT PRIMARY KEY, crop_sha256 TEXT NOT NULL, requested_field_type TEXT,
  raw_returned_string TEXT, candidate_normalised_value TEXT, confidence REAL,
  reader_engine TEXT, reader_version TEXT, read_at TEXT, errors TEXT);
CREATE TABLE IF NOT EXISTS reader_comparisons (
  comparison_id TEXT PRIMARY KEY, candidate_field_id TEXT NOT NULL, crop_sha256 TEXT,
  primary_raw TEXT, primary_confidence REAL, second_raw TEXT, second_confidence REAL,
  comparison_state TEXT NOT NULL CHECK (comparison_state IN {_in(DUAL_STATES)}),
  disagreement_reason TEXT, alternative_readings TEXT, accepted_value TEXT);
"""

_REVIEW_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS reviews (
  review_id TEXT PRIMARY KEY, candidate_field_id TEXT NOT NULL, media_id TEXT,
  reviewer_ref TEXT, decision TEXT NOT NULL CHECK (decision IN {_in(REVIEW_DECISIONS)}),
  confirmed_value TEXT, reviewed_at TEXT, review_note TEXT, source_crop_sha256 TEXT);
CREATE TABLE IF NOT EXISTS approved_media_facts (
  approved_fact_id TEXT PRIMARY KEY, candidate_field_id TEXT NOT NULL, media_id TEXT NOT NULL,
  field_type TEXT NOT NULL, confirmed_value TEXT NOT NULL,
  source_original_sha256 TEXT NOT NULL, source_region_id TEXT NOT NULL,
  source_crop_sha256 TEXT, evidence_domain TEXT NOT NULL, approved_at TEXT);
"""


class CandidateDB:
    def __init__(self, path=None):
        self.path = path or CANDIDATES_DB
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.executescript(_CANDIDATE_SCHEMA)
        self.conn.commit()

    def insert_image(self, **f):
        cols = ("media_id", "source_message_id", "source_timestamp", "original_path", "sha256",
                "mime_type", "file_size", "pixel_width", "pixel_height", "ingested_at")
        self.conn.execute(f"INSERT INTO ingested_images ({','.join(cols)}) VALUES "
                          f"({','.join('?' for _ in cols)})", [f.get(c) for c in cols])
        self.conn.commit()

    def get_image_by_sha(self, sha):
        cur = self.conn.execute("SELECT media_id, sha256 FROM ingested_images WHERE sha256=?", (sha,))
        r = cur.fetchone()
        return {"media_id": r[0], "sha256": r[1]} if r else None

    def insert_derived(self, **f):
        self.conn.execute("INSERT INTO derived_artifacts (artifact_id,media_id,original_sha256,"
                          "artifact_type,sha256,region_id) VALUES (?,?,?,?,?,?)",
                          (f["artifact_id"], f["media_id"], f["original_sha256"],
                           f["artifact_type"], f["sha256"], f.get("region_id")))
        self.conn.commit()

    def insert_region(self, **f):
        self.conn.execute("INSERT INTO regions (region_id,media_id,region_type,bbox,crop_path,"
                          "crop_sha256,detection_confidence,extractor_version) VALUES (?,?,?,?,?,?,?,?)",
                          (f["region_id"], f["media_id"], f["region_type"], json.dumps(f.get("bbox")),
                           f.get("crop_path"), f.get("crop_sha256"), f.get("detection_confidence"),
                           f.get("extractor_version")))
        self.conn.commit()

    def insert_candidate(self, **f):
        cols = ("candidate_field_id", "media_id", "region_id", "field_type", "raw_visible_text",
                "candidate_value_string", "accepted_normalised_value", "bbox", "crop_sha256",
                "extractor_confidence", "alternative_readings", "extraction_method_version",
                "review_status", "evidence_domain", "dual_reading_state",
                "eligible_for_shadow_outcome", "eligible_for_demo_outcome",
                "eligible_for_account_r", "eligible_for_expectancy")
        row = dict(f)
        row["alternative_readings"] = json.dumps(f.get("alternative_readings"))
        row["bbox"] = json.dumps(f.get("bbox"))
        for elig in ("eligible_for_shadow_outcome", "eligible_for_demo_outcome",
                     "eligible_for_account_r", "eligible_for_expectancy"):
            row[elig] = int(row.get(elig) or 0)        # never outcome-eligible by default
        self.conn.execute(f"INSERT INTO field_candidates ({','.join(cols)}) VALUES "
                          f"({','.join('?' for _ in cols)})", [row.get(c) for c in cols])
        self.conn.commit()

    def insert_semantics(self, **f):
        self.conn.execute("INSERT OR REPLACE INTO image_semantics (media_id,classification,"
                          "management_candidates,has_clean_entry_range,is_clean_new_entry_signal) "
                          "VALUES (?,?,?,?,?)",
                          (f["media_id"], f["classification"], json.dumps(f.get("management_candidates")),
                           int(bool(f.get("has_clean_entry_range"))),
                           int(bool(f.get("is_clean_new_entry_signal")))))
        self.conn.commit()

    def candidate(self, cfid):
        cur = self.conn.execute("SELECT * FROM field_candidates WHERE candidate_field_id=?", (cfid,))
        cols = [d[0] for d in cur.description]
        r = cur.fetchone()
        return dict(zip(cols, r)) if r else None

    def insert_crop(self, **f):
        cols = ("crop_id", "media_id", "original_sha256", "region_type", "parent_region_id",
                "field_type", "bbox", "crop_path", "crop_sha256", "crop_width", "crop_height",
                "crop_created_at", "crop_tool_version")
        row = dict(f)
        row["bbox"] = json.dumps(f.get("bbox"))
        self.conn.execute(f"INSERT OR IGNORE INTO crops ({','.join(cols)}) VALUES "
                          f"({','.join('?' for _ in cols)})", [row.get(c) for c in cols])
        self.conn.commit()

    def insert_second_reading(self, **f):
        cols = ("reading_id", "crop_sha256", "requested_field_type", "raw_returned_string",
                "candidate_normalised_value", "confidence", "reader_engine", "reader_version",
                "read_at", "errors")
        self.conn.execute(f"INSERT OR REPLACE INTO second_readings ({','.join(cols)}) VALUES "
                          f"({','.join('?' for _ in cols)})", [f.get(c) for c in cols])
        self.conn.commit()

    def insert_comparison(self, **f):
        cols = ("comparison_id", "candidate_field_id", "crop_sha256", "primary_raw",
                "primary_confidence", "second_raw", "second_confidence", "comparison_state",
                "disagreement_reason", "alternative_readings", "accepted_value")
        row = dict(f)
        row["alternative_readings"] = json.dumps(f.get("alternative_readings"))
        self.conn.execute(f"INSERT OR REPLACE INTO reader_comparisons ({','.join(cols)}) VALUES "
                          f"({','.join('?' for _ in cols)})", [row.get(c) for c in cols])
        self.conn.commit()

    def set_candidate_crop(self, cfid, crop_sha256):
        self.conn.execute("UPDATE field_candidates SET crop_sha256=? WHERE candidate_field_id=?",
                          (crop_sha256, cfid))
        self.conn.commit()

    def regions_of_type(self, media_id, rtype):
        return [r[0] for r in self.conn.execute(
            "SELECT region_id FROM regions WHERE media_id=? AND region_type=?", (media_id, rtype))]

    def count(self, table):
        return self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def close(self):
        self.conn.close()


class ReviewDB:
    def __init__(self, path=None):
        self.path = path or REVIEWS_DB
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.executescript(_REVIEW_SCHEMA)
        self.conn.commit()

    def insert_review(self, **f):
        self.conn.execute("INSERT INTO reviews (review_id,candidate_field_id,media_id,reviewer_ref,"
                          "decision,confirmed_value,reviewed_at,review_note,source_crop_sha256) "
                          "VALUES (?,?,?,?,?,?,?,?,?)",
                          (f["review_id"], f["candidate_field_id"], f.get("media_id"),
                           f.get("reviewer_ref"), f["decision"], f.get("confirmed_value"),
                           f.get("reviewed_at") or _now(), f.get("review_note"),
                           f.get("source_crop_sha256")))
        self.conn.commit()

    def insert_approved_fact(self, **f):
        cols = ("approved_fact_id", "candidate_field_id", "media_id", "field_type", "confirmed_value",
                "source_original_sha256", "source_region_id", "source_crop_sha256", "evidence_domain",
                "approved_at")
        self.conn.execute(f"INSERT INTO approved_media_facts ({','.join(cols)}) VALUES "
                          f"({','.join('?' for _ in cols)})",
                          [f.get(c) if c != "approved_at" else (f.get("approved_at") or _now())
                           for c in cols])
        self.conn.commit()

    def count(self, table):
        return self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def approved_for(self, cfid):
        return self.conn.execute(
            "SELECT COUNT(*) FROM approved_media_facts WHERE candidate_field_id=?", (cfid,)).fetchone()[0]

    def close(self):
        self.conn.close()
