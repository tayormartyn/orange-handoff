# PHASE 2 — OAuth grant (VIEW-ONLY). Plain-English steps for Martyn.

**Do this only when we move to Phase 2. Phase 1 (build + proof) is done and connects to nothing.**

You are granting a **view-only** permission to a **Pepperstone DEMO** cTrader account. You are
**not** granting trading access. Only you can do this — it is a browser login. I never perform
the grant, and the tool can only ever request the `accounts` (view-only) scope.

## Before you start
- Store your cTrader app **Client ID** and **Client Secret** once, encrypted with Windows DPAPI
  (only your Windows user can decrypt), **outside** the repo:
  ```
  python -c "from research.farouk_pilot.read_only_ctrader_preflight import credentials as c; c.store_credentials('YOUR_CLIENT_ID','YOUR_CLIENT_SECRET')"
  ```
  They are never written to the repo, `.env`, the command history, logs, or any report.

## Step 1 — open the authorization page
Use the app's authorize URL with **`scope=accounts`** (the tool never emits `trading`). Log in
to your **cTrader ID** and pick your **Pepperstone DEMO** account (not a live one).

## Step 2 — the permission screen (the important part)
> **➜ ACCEPT: the "account information" / read-only / `accounts` (VIEW-ONLY) permission.**
> **➜ REFUSE: any "trading" / "full access" permission.**
>
> **If the ONLY option offered is a trading / full-access grant — STOP. Do NOT authorise.**
> That means the app is registered for the wrong scope; it must be fixed to request `accounts`
> before you proceed. Tell me and I will not go further.

## Step 3 — after you approve (automatic, loopback listener)
You do **not** copy or paste the code. The exchange runs as a **loopback listener**: one command
starts a tiny local web server on the registered `http://localhost/` redirect, opens the consent
page, and when you click **Allow** the browser's redirect hits that listener, which captures the
`code=` automatically and exchanges it for a **view-only** token (stored via DPAPI, masked in
output). One command, one click:
```
$env:ORANGE_PREFLIGHT_CONNECT = "1"
python -m research.farouk_pilot.read_only_ctrader_preflight.loopback_exchange
```
A bad/expired/error response fails **loud** and stores nothing. Nothing runs unattended.

**If it prints `[BIND-FAILED]`** (port 80 is held on Windows), register a high-port redirect on
the app — e.g. `http://localhost:8123/` — then set it in the same window and re-run:
```
$env:ORANGE_PREFLIGHT_REDIRECT_URI = "http://localhost:8123/"
```

## The account allowlist is discovered, never guessed
The fail-closed guard checks the account against a **pinned** `ctidTraderAccountId` — cTrader's
internal id, which is **not** your login number 4257941. It starts **unpinned**, and while
unpinned the guard **refuses everything** (empty allowlist = no match = stop). On the first
account-list read in Phase 2 the tool shows you the id it got; you confirm it's your demo
account, and only then is it pinned. Nothing is hardcoded.

## What the tool does on the next (separately-authorised) run — and refuses
It connects to **demo.ctraderapi.com:5035 only** and performs **only** these reads: application
auth, account enumeration, demo-account session auth, account details, symbol list, XAUUSD
metadata, heartbeat. It then **fails closed** unless ALL of these hold — otherwise it stops with
a sanitised error and a non-zero exit:
`endpoint == demo.ctraderapi.com:5035` · `granted scope is view-only (SCOPE_VIEW, not SCOPE_TRADE)`
· `isLive == false` · `account == your allowlisted demo account` · `environment == Pepperstone demo`
· `XAUUSD resolves to exactly one symbol`. If the granted scope comes back **SCOPE_TRADE**, it
refuses and tells you to **revoke and re-grant `accounts` only**.

It never places, modifies, or cancels an order — there is no order code in the tool at all.
