# OAuth grant — plain-English steps (VIEW-ONLY, do this yourself)

You are granting a **view-only** ("accounts") permission to a **Pepperstone DEMO** cTrader
account. You are **not** granting trading access. Only you can do this — it is a browser
login. I never perform the grant, and the tool never requests a trading scope.

Do the whole thing in one terminal session so nothing is written to disk in the repo.

## Before you start
- Have your cTrader **app Client ID** and **Client Secret** ready (from the cTrader Open API
  application you registered). These are **not** in this repo and must never be pasted into a
  file here, a `.env`, a log, or a ledger.
- Store them once, encrypted with Windows DPAPI (only your Windows user can decrypt), outside
  the repo:
  ```
  python -c "from research.farouk_pilot.demo_lane.preflight import credentials as c; c.store_credentials('YOUR_CLIENT_ID','YOUR_CLIENT_SECRET')"
  ```
  (Alternatively set `CTRADER_CLIENT_ID` / `CTRADER_CLIENT_SECRET` as environment variables
  for this session only — never persisted.)

## Step 1 — get the authorization URL
```
set CTRADER_CLIENT_ID=YOUR_CLIENT_ID
set CTRADER_CLIENT_SECRET=YOUR_CLIENT_SECRET
python ctrader_auth.py url
```
This prints a URL. The tool builds it with **`scope=accounts`** and will hard-refuse to emit
a trading scope. Copy the URL.

## Step 2 — authorize in the browser (the important part)
1. Open the URL, log into your **cTrader ID**.
2. On the account-selection screen, pick your **Pepperstone DEMO** account (not a live one).
3. On the consent / permissions screen, **accept the permission that says account
   information / read-only / "accounts"**.

   **➜ ACCEPT: the view-only / "accounts" permission.**
   **➜ DO NOT ACCEPT any "trading" / "trade" / full-access permission.**

   If the only option offered is a trading / full-access grant, **stop and do not authorize**.
   That means the app registration is requesting the wrong scope; it must be fixed to request
   `accounts` before you proceed. Tell me and I will not go further.

4. After you approve, the browser redirects to `http://localhost/?code=XXXXXXXX`. The page may
   fail to load — that is fine. Copy the `code=` value from the address bar.

## Step 3 — exchange the code for a view-only token
```
python ctrader_auth.py token XXXXXXXX
```
This stores a token (gitignored, masked in any output). The secret is sent over TLS and never
logged.

## Step 4 — confirm the token is cached
```
python ctrader_auth.py status
```
You should see a masked access token and `scope: accounts (read-only enforced client-side)`.

## What happens next (NOT now, and NOT by me)
Verifying the **observed** granted scope, that `isLive` is False, that the account is the
allowlisted demo account, and reading the live XAUUSD metadata all require a view-only read
over the broker's protobuf socket. That read is the **separately-authorised activation
burn-in** — it is not part of this preflight tool and I do not perform it. Until then, the
preflight tool runs in dry-run against a mock and proves only its logic.

If at any point the consent screen, the status output, or the later burn-in shows the granted
permission is **SCOPE_TRADE (trading)**, the preflight tool refuses and instructs you to
**revoke the app authorization and re-grant `accounts` only**. Report as observed, never
assume the requested scope was the granted scope.
