"""
Append-only EXTENSION store for the image bridge: data/image_bridge_observations_v1.db. References
a row in the unchanged paper_observations DB and holds the image-specific metadata (source type,
intake id, hashes, three time-anchor results, latencies, provenance). UPDATE/DELETE prohibited.
Contains NO outcome/R/provider-P&L columns.
"""
from __future__ import annotations
import json
import os
import sqlite3
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DB = os.path.join(_ROOT, "data", "image_bridge_observations_v1.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS image_bridge_observations (
  rowseq INTEGER PRIMARY KEY AUTOINCREMENT,
  bridge_obs_id TEXT NOT NULL UNIQUE,
  paper_observation_id TEXT,
  source_type TEXT NOT NULL, source_platform TEXT NOT NULL,
  intake_id TEXT, original_image_sha256 TEXT, crop_hashes_json TEXT,
  review_decision_ids_json TEXT, timestamp_provenance TEXT,
  provider_post_result_json TEXT, manual_import_result_json TEXT,
  human_confirmed_actionable_result_json TEXT,
  capture_latency_s TEXT, import_latency_s TEXT, actionable_latency_s TEXT,
  observation_only INTEGER NOT NULL DEFAULT 1, paper_only INTEGER NOT NULL DEFAULT 1,
  not_a_fill INTEGER NOT NULL DEFAULT 1, not_an_outcome INTEGER NOT NULL DEFAULT 1,
  persisted_utc TEXT);
CREATE TRIGGER IF NOT EXISTS ibo_no_update BEFORE UPDATE ON image_bridge_observations
  BEGIN SELECT RAISE(ABORT, 'append-only: image_bridge_observations UPDATE prohibited'); END;
CREATE TRIGGER IF NOT EXISTS ibo_no_delete BEFORE DELETE ON image_bridge_observations
  BEGIN SELECT RAISE(ABORT, 'append-only: image_bridge_observations DELETE prohibited'); END;
"""


class ImageBridgeDB:
    def __init__(self, path=None):
        self.path = path or DEFAULT_DB
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def record(self, *, bridge_obs_id, paper_observation_id, intake_id, original_image_sha256,
               crop_hashes, review_decision_ids, timestamp_provenance, provider_post_result,
               manual_import_result, human_confirmed_actionable_result, latencies):
        self.conn.execute(
            "INSERT INTO image_bridge_observations (bridge_obs_id,paper_observation_id,source_type,"
            "source_platform,intake_id,original_image_sha256,crop_hashes_json,review_decision_ids_json,"
            "timestamp_provenance,provider_post_result_json,manual_import_result_json,"
            "human_confirmed_actionable_result_json,capture_latency_s,import_latency_s,"
            "actionable_latency_s,persisted_utc) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (bridge_obs_id, paper_observation_id, "IMAGE_CONFIRMED", "DISCORD", intake_id,
             original_image_sha256, json.dumps(crop_hashes), json.dumps(review_decision_ids),
             timestamp_provenance, json.dumps(provider_post_result, default=str),
             json.dumps(manual_import_result, default=str),
             json.dumps(human_confirmed_actionable_result, default=str),
             str(latencies.get("capture_latency_s")), str(latencies.get("import_latency_s")),
             str(latencies.get("actionable_latency_s")),
             time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
        self.conn.commit()
        return bridge_obs_id

    def count(self):
        return self.conn.execute("SELECT COUNT(*) FROM image_bridge_observations").fetchone()[0]

    def close(self):
        self.conn.close()
