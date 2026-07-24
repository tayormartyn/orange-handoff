#!/usr/bin/env python3
"""
Sybil's Hearth — Airtable "Hearthside Ledger" builder.

Creates every table, field, select option, and link relationship from the
Agent Build Brief, via the Airtable Web API.

RUN BY: the human operator (not an agent) — it needs a real key + base.

PREREQUISITES (the operator does these once, by hand):
  1. Create a free/paid Airtable account and an EMPTY base named
     "Hearthside Ledger" in a workspace.
  2. Create a Personal Access Token (PAT) with scopes:
        schema.bases:write  ·  schema.bases:read  ·  data.records:read
     and grant it access to that base.
  3. Copy the base ID (starts with "app...") from the base's API docs/URL.
  4. Set env vars, then run:  python3 setup_airtable.py

     export AIRTABLE_PAT="pat_xxx"
     export AIRTABLE_BASE_ID="appXXXXXXXXXXXXXX"

This script is idempotent-ish: it skips tables that already exist by name.
It does NOT touch any paid render/voice/publish API. Safe to run first.
"""

import os, sys, time, requests

PAT = os.environ.get("AIRTABLE_PAT")
BASE_ID = os.environ.get("AIRTABLE_BASE_ID")
if not PAT or not BASE_ID:
    sys.exit("Set AIRTABLE_PAT and AIRTABLE_BASE_ID environment variables first.")

API = "https://api.airtable.com/v0/meta/bases/" + BASE_ID
H = {"Authorization": f"Bearer {PAT}", "Content-Type": "application/json"}

# ---- select-option colour helper (Airtable palette names) -------------------
def sel(*names):
    palette = ["blueLight2", "cyanLight2", "tealLight2", "greenLight2",
               "yellowLight2", "orangeLight2", "redLight2", "pinkLight2",
               "purpleLight2", "grayLight2"]
    return {"choices": [{"name": n, "color": palette[i % len(palette)]}
                        for i, n in enumerate(names)]}

# ---- table definitions (links added in a 2nd pass) --------------------------
TABLES = {
    "Submissions": [
        {"name": "Raw Dream Text", "type": "multilineText"},
        {"name": "Source", "type": "singleSelect",
         "options": sel("form", "pinned_comment", "manual")},
        {"name": "Submitter Handle", "type": "singleLineText"},
        {"name": "Consent to Feature", "type": "checkbox",
         "options": {"icon": "check", "color": "greenBright"}},
        {"name": "Safety Flag", "type": "checkbox",
         "options": {"icon": "flag", "color": "redBright"}},
        {"name": "Status", "type": "singleSelect",
         "options": sel("new", "screened", "care_queue", "scripted")},
        {"name": "Created At", "type": "createdTime",
         "options": {"result": {"type": "dateTime",
                                "options": {"dateFormat": {"name": "iso"},
                                            "timeFormat": {"name": "24hour"},
                                            "timeZone": "Europe/London"}}}},
    ],
    "Scripts": [
        {"name": "Character", "type": "singleSelect",
         "options": sel("nan_sybil", "maeve", "jesse", "family")},
        {"name": "Format", "type": "singleSelect",
         "options": sel("hero_dream_short", "validation_moment",
                        "fireside_tale", "dream_of_the_week", "multi_character")},
        {"name": "Script JSON", "type": "multilineText"},
        {"name": "Safety Flag", "type": "checkbox",
         "options": {"icon": "flag", "color": "redBright"}},
        {"name": "Status", "type": "singleSelect",
         "options": sel("needs_review", "approved", "rejected")},
        {"name": "Reviewer Notes", "type": "multilineText"},
        {"name": "Version", "type": "number", "options": {"precision": 0}},
    ],
    "Assets": [
        {"name": "Type", "type": "singleSelect",
         "options": sel("audio", "video", "final")},
        {"name": "Speaker", "type": "singleSelect",
         "options": sel("nan_sybil", "maeve", "jesse")},
        {"name": "Tool", "type": "singleSelect",
         "options": sel("elevenlabs", "heygen", "higgsfield", "runway", "assembly")},
        {"name": "File URL", "type": "url"},
        {"name": "Render Cost", "type": "number", "options": {"precision": 2}},
        {"name": "Status", "type": "singleSelect",
         "options": sel("queued", "rendering", "ready", "failed")},
    ],
    "Videos": [
        {"name": "Platform", "type": "singleSelect",
         "options": sel("youtube", "tiktok", "reels")},
        {"name": "Publish At", "type": "date",
         "options": {"dateFormat": {"name": "iso"}}},
        {"name": "Published URL", "type": "url"},
        {"name": "AI Label Set", "type": "checkbox",
         "options": {"icon": "check", "color": "greenBright"}},
        {"name": "Status", "type": "singleSelect",
         "options": sel("scheduled", "published")},
        {"name": "Retention %", "type": "number", "options": {"precision": 1}},
        {"name": "Comment Rate", "type": "number", "options": {"precision": 3}},
    ],
    "Ideas": [
        {"name": "Theme", "type": "multipleSelects",
         "options": sel("water", "chase", "grief", "flying", "teeth",
                        "falling", "home", "voice", "other")},
        {"name": "Notes", "type": "multilineText"},
        {"name": "Status", "type": "singleSelect",
         "options": sel("backlog", "queued", "used")},
    ],
}

# Link fields to add in pass 2:  (table, field name, linked table)
LINKS = [
    ("Scripts", "Submission", "Submissions"),
    ("Assets", "Script", "Scripts"),
    ("Videos", "Script", "Scripts"),
    ("Videos", "Final Asset", "Assets"),
    ("Ideas", "Source Dream", "Submissions"),
]

def existing_tables():
    r = requests.get(API + "/tables", headers=H); r.raise_for_status()
    return {t["name"]: t["id"] for t in r.json()["tables"]}

def create_table(name, fields):
    # first field becomes the primary field; use a text primary field
    primary = {"name": f"{name[:-1] if name.endswith('s') else name} ID",
               "type": "singleLineText"}
    payload = {"name": name, "fields": [primary] + fields}
    r = requests.post(API + "/tables", headers=H, json=payload)
    if r.status_code >= 300:
        print(f"  ! {name}: {r.status_code} {r.text}"); r.raise_for_status()
    print(f"  ✔ created table: {name}")
    return r.json()["id"]

def add_link(table_id, field_name, linked_table_id):
    payload = {"name": field_name, "type": "multipleRecordLinks",
               "options": {"linkedTableId": linked_table_id}}
    r = requests.post(f"{API}/tables/{table_id}/fields", headers=H, json=payload)
    if r.status_code >= 300:
        print(f"  ! link {field_name}: {r.status_code} {r.text}"); return
    print(f"  ✔ linked {field_name} → {linked_table_id}")

def main():
    print("Building the Hearthside Ledger…")
    ids = existing_tables()
    # pass 1: tables + plain fields
    for name, fields in TABLES.items():
        if name in ids:
            print(f"  · {name} already exists — skipping"); continue
        ids[name] = create_table(name, fields); time.sleep(0.3)
    # pass 2: link relationships
    print("Adding relationships…")
    for table, field, linked in LINKS:
        add_link(ids[table], field, ids[linked]); time.sleep(0.3)
    print("\nDone. Now create these VIEWS by hand in the Airtable UI:")
    print("  • 'Needs Review'  (Scripts where Status = needs_review)")
    print("  • 'Care Queue'    (Submissions where Safety Flag = checked)")
    print("  • 'Render Queue'  (Assets where Status = rendering)")
    print("  • 'Schedule'      (Calendar view on Videos → Publish At)")
    print("\nThe ledger is ready. Point the coding agent at W1 next.")

if __name__ == "__main__":
    main()
