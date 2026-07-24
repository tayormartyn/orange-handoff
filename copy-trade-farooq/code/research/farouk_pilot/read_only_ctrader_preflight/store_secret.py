"""Operator-run, INTERACTIVE credential entry for the read-only preflight. One command, no args.

  * CLIENT_ID is typed at a VISIBLE prompt (paste it; it is fine to see on screen).
  * CLIENT_SECRET is typed at a HIDDEN getpass prompt - never echoed to the screen, never placed
    in shell history, never passed as a process argument.

Both are stored together in ONE encrypted DPAPI blob, OUTSIDE the repository tree. The command
prints ONLY the blob path and a "stored OK" line - NEITHER value is printed.

Run:  python -m research.farouk_pilot.read_only_ctrader_preflight.store_secret
"""
import getpass
import sys

from . import credentials


def main():
    print("cTrader VIEW-ONLY app credentials. The secret is hidden (no echo, no history).\n")
    client_id = input("Client ID (visible, paste it): ").strip()
    client_secret = getpass.getpass("Client Secret (hidden): ").strip()
    if not client_id or not client_secret:
        print("[ABORT] empty value; nothing stored.")
        return 2
    credentials.store_credentials(client_id, client_secret)
    print("\n[STORED OK] encrypted DPAPI blob written outside the repo:")
    print(f"            {credentials.cred_blob_path()}")
    print("            (neither the client id nor the secret is printed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
