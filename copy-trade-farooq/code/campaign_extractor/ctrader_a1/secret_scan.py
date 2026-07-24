"""
cTrader secret-safety scan. Searches project source/reports/logs/test-output/databases for
accidental exposure of the ACTUAL credential values, WITHOUT ever printing a value.

Reports only: (file_path, secret_category, exposure_status). The authorised local .env and the
gitignored token cache are excluded from being treated as exposures (they are intended holders).
"""
from __future__ import annotations
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))

# files/paths that are AUTHORISED to hold secrets (excluded from exposure findings)
_AUTHORISED = {
    os.path.abspath(os.path.join(PROJECT_ROOT, ".env")),
    os.path.abspath(os.path.join(PROJECT_ROOT, "data", "ctrader_token.json")),
}
_SCAN_EXT = (".py", ".md", ".json", ".jsonl", ".csv", ".log", ".txt", ".ini", ".cfg", ".yaml",
             ".yml", ".db")
_SKIP_DIRS = {".git", "__pycache__", "node_modules", "price_cache", "backups"}


def _iter_files(root):
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in _SKIP_DIRS]
        for f in files:
            if f.endswith(_SCAN_EXT):
                yield os.path.join(d, f)


def scan_for_secret_values(secret_values, root=None):
    """secret_values: dict {category: value}. Returns list of (path, category, 'EXPOSED').
    Values are searched as bytes to also catch databases; never printed."""
    root = root or PROJECT_ROOT
    needles = {cat: v.encode("utf-8") for cat, v in secret_values.items() if v}
    findings = []
    for fp in _iter_files(root):
        if os.path.abspath(fp) in _AUTHORISED:
            continue
        try:
            with open(fp, "rb") as fh:
                data = fh.read()
        except OSError:
            continue
        for cat, needle in needles.items():
            if len(needle) >= 12 and needle in data:     # ignore short/ambiguous values
                findings.append((os.path.relpath(fp, root), cat, "EXPOSED"))
    return findings


def env_is_gitignored():
    gi = os.path.join(PROJECT_ROOT, ".gitignore")
    if not os.path.exists(gi):
        return False
    txt = open(gi, encoding="utf-8").read().splitlines()
    return any(line.strip() in (".env", "*.env") for line in txt)


def is_git_repo():
    return os.path.isdir(os.path.join(PROJECT_ROOT, ".git"))
