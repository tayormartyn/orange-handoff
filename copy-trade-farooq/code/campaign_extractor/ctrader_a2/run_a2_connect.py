"""
Single controlled A2 VIEW-ONLY connection driver. Run under .venv-ctrader.

Loads the cached token + client credentials locally (never printed), runs connect_and_read
ONCE (one Twisted reactor lifecycle, no retry, 429/error stops immediately), and prints a
SANITISED result (masked account id; no token/secret). Optional arg: a selected demo account
id (used only after a human selection when >1 demo account was found).
"""
from __future__ import annotations
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_CE = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_CE)
for p in (_HERE, _CE, _ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from ctrader_a1 import dotenv_loader as DL
import token_loader
import live_transport


def main():
    env = DL.load_ctrader_env()
    cid = env.get("CTRADER_CLIENT_ID")
    csec = env.get("CTRADER_CLIENT_SECRET")
    tok = token_loader.load_cached_token()
    if not tok or not tok.get("access_token"):
        print("STOP: no cached access token"); return 2
    if not cid or not csec:
        print("STOP: client credentials not present in .env"); return 2

    selected = sys.argv[1] if len(sys.argv) > 1 else None
    result = live_transport.connect_and_read(
        tok["access_token"], client_id=cid, client_secret=csec, selected_account_id=selected)

    # result is already sanitised by the transport (masked account id; no token/secret).
    safe = {k: v for k, v in result.items() if k not in ("access_token",)}
    print("=== A2 CONTROLLED CONNECTION RESULT (sanitised) ===")
    print(json.dumps(safe, indent=2, sort_keys=True, default=str))
    return 0 if result.get("status") in ("READ_OK", "NEEDS_HUMAN_SELECTION") else 1


if __name__ == "__main__":
    sys.exit(main())
