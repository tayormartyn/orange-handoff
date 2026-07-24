# Signal Terminal — Paper Mode

A small program that takes a trading signal (the kind you paste from the Whale
Room feed), works out **what trade you *would* have taken** if you risked exactly
1% of your pot, and writes it to a spreadsheet file.

**It does not connect to any exchange. It does not place orders. It does not move
any money.** It is a notebook that does the maths for you, so that after a few
weeks you can look back and judge whether the signals are actually any good —
*before* you ever risk real cash.

---

## What you need (one-time setup)

### 1. Install Python

1. Go to <https://www.python.org/downloads/>
2. Download the latest Python for Windows and run the installer.
3. **Important:** on the first screen, tick the box that says
   **"Add Python to PATH"**, then click *Install Now*.

To check it worked, open **PowerShell** (press the Windows key, type
`powershell`, hit Enter) and type:

```
python --version
```

You should see something like `Python 3.12.x`. If you do, you're good.

### 2. Install the one add-on this needs

In the same PowerShell window, type:

```
pip install anthropic
```

This is the library that lets the program read your pasted signals.

### 3. Get an API key and set it

The signal-reading step uses Claude. You need an API key (a long secret password).

1. Get one from <https://console.anthropic.com/> (Settings → API Keys).
2. In PowerShell, set it for your current session by typing
   (replace `sk-...` with your real key):

```
$env:ANTHROPIC_API_KEY = "sk-ant-xxxxxxxxxxxxxxxxx"
```

> That sets the key for **this PowerShell window only**. If you close the window
> you'll need to set it again. To make it permanent you can add it in
> *Windows → Edit environment variables for your account*, but the line above is
> fine to get going.

---

## How to run it

1. Open PowerShell.
2. Go to the folder:

```
cd C:\Users\Marty\signal-terminal
```

3. Start it:

```
python run.py
```

Then:

- **Paste a signal** when it asks. Press **Enter on an empty line** when you've
  finished pasting.
- It shows you the numbers it read. **Check them — especially the stop-loss —**
  and type `y` if they're right, or `n` to throw it away.
- It prints the ticket: your size, the cash at risk, the risk as a % of your pot
  (should read about 1%), and the reward-to-risk of the first target.
- It saves that row to `paper_log.csv`.
- It then asks for the next signal. Type `quit` to stop.

---

## What `paper_log.csv` is for

Every confirmed signal becomes one row in `paper_log.csv`. You can open it in
Excel or Google Sheets. After a while you'll have a record of dozens of trades
you *would* have made. That's the whole point: it lets you measure whether the
signal feed has a real edge **without risking a penny**.

When a trade finishes, you fill in **how far it ran**. Everything else (size,
risk, the target prices, the R:R) was captured automatically when you logged it.

### When running the CPS profile (opt-in): the `tps_hit` column

CPS scales out of a trade in **thirds** — 1/3 off at TP1, 1/3 at TP2, 1/3 runner
to TP3 — so what matters is how far the trade got. Type **one** of these into
the `tps_hit` cell:

| Type this | Meaning |
|-----------|---------|
| `SL` (or `0`) | Stopped out before any target — a full loss (**−1R**) |
| `1` | Reached **TP1** then the rest stopped (nets **0R** — the 1/3 winner cancels the 2/3 stopped) |
| `2` | Reached **TP2**, runner stopped at breakeven (**+1.67R**) |
| `3` | Reached **TP3** — the full ladder ran (**+3.33R**) |

Leave it **blank** while the trade is still open. The review tool then works out
your real **R** and cash P&L for you — you don't do any maths.

### If you're running the DEFAULT profile instead: the `outcome` column

If you switch `RULE_PROFILE` to `DEFAULT` (one target, full position), use the
`outcome` column instead: `1`/`2`/`3`/`4` for the target it reached, `SL` for a
stop-out, `BE` for breakeven. (You can use this column under CPS too if you ever
exit the whole position at one target rather than scaling out.)

### When the entry never filled — `MISSED`

Sometimes a signal comes through, the price never reaches the entry, and **no
trade is taken**. That's not a win and it's not a loss — it's a *miss*. Mark it
by putting `MISSED` in the `outcome` column. A miss is recorded with zero profit
and zero R, and the review tool counts it **separately** so it never drags your
win rate or expectancy up or down. What it *does* feed is your **fill rate** —
how often the entries actually got hit (see the review section below).

The easy way to record one is the result tool (no editing the spreadsheet by
hand):

```
python outcome.py
```

It lists the trades waiting for a result and lets you pick one and choose
**`[m] Missed`**. You can also press **`[a]`** to *back-log* a signal you saw but
never entered — handy for filling in history. It just asks for the ticker (and,
optionally, direction, the entry it would have needed, and the date), then stores
it as `MISSED` for you.

### The optional context columns — `source`, `session`, `level_tf`

When you run `python run.py`, after you confirm a signal it asks three optional
questions: **who called it** (e.g. `WhaleRoom`), **which session** (`Asia` /
`New York` / `London`), and **which level timeframe** (`4H` / `Daily` / `Weekly`
/ `Monthly`). Press **Enter** to skip any of them — they never block logging.
Recording them lets the review tool show you whether your edge is concentrated in
a particular trader, session, or timeframe.

---

## Reviewing your edge — `python review.py`

Once you've filled in some outcomes, run:

```
python review.py
```

It reads `paper_log.csv` and prints a plain-English report:

- **Fill rate** — of every signal you saw, how many you actually got into
  (**filled**) versus how many got away (**missed**). For example, *50% (2 filled
  / 2 missed)* means half the signals never reached their entry. This is shown at
  the very top, before anything else, because a great-looking edge is worth a lot
  less if you can only get into half the trades. Misses are **never** counted as
  wins or losses — they only affect this fill rate.
  - It also shows two expectancy numbers side by side: **filled only** (your edge
    *when you do get in*) and **including misses** (each miss counted as a 0R
    no-trade — the real-world drag from entries you couldn't get).
- **Win rate** — what % of *filled* trades made money. (Misses are excluded —
  they aren't trades.)
- **Expectancy** — the headline number: average **realised R** per trade, worked
  out from how far each trade ran under the CPS scale-out. (One **R** is your risk
  on the trade, e.g. ~£140 at 1%. `+0.30 R` ≈ £42 made per trade on paper.
  Positive is good; negative means the feed lost money.) It also shows **net £**.
- **Total R** — added up across all your finished trades.
- **How far trades ran** — how many died at TP1 vs ran to TP2/TP3, so you can see
  whether the edge is in the runner.
- The same breakdown **split by asset class**, **by instrument** (gold alone,
  silver alone, each coin), **by trader**, **by session**, and **by level
  timeframe** — because a single blended number can hide where the edge really is.

**About sample size:** every section shows how many trades it's based on, and
**flags anything under 30 trades as "not enough to trust yet"**. A clean-looking
`+0.4 R` from 6 trades is noise — the tool tells you so rather than letting you
believe it.

---

## The CPS rule profile (Columbus Closing Price System)

The engine can run in one of two **rule profiles**, set by `RULE_PROFILE` in
`config.py`:

- **`DEFAULT`** (the default) — the original behaviour: a flat risk %, and it
  trades the signal's own targets.
- **`CPS`** (opt in by setting `RULE_PROFILE = "CPS"`) — speaks the same
  disciplined framework as the Columbus trader's journal: phase-based risk, a
  fixed 1:2 / 1:3 / 1:5 exit ladder scaled out in thirds, real metal contract
  specs, and daily/weekly loss limits.

Switching profiles changes nothing about the safety rails below — they always
apply. Here's what CPS adds:

**Phase-based risk.** Your risk per trade follows your account phase
(`TRADING_PHASE` in `config.py`): Phase 1 = 1%, Phase 2 = 2%, Phase 3 = up to 3%.
It is always clamped between 0.5% and a **hard 3% cap** — it can never exceed it.
Default is Phase 1 / 1%.

**The exit ladder.** Targets are placed at fixed reward-to-risk multiples from
your entry — TP1 at 1:2, TP2 at 1:3, TP3 at 1:5 — and the plan is to take 1/3 off
at each. After TP2, the stop moves to **breakeven** on the runner. The ticket
prints this ladder and plan every time.

**The stop rule.** A stop is set at entry and **never widened** — it may only move
toward profit. You can optionally use **fixed-distance stops** for metals
(`STOP_MODE = "FIXED"`): Gold $10–$20, Silver $1–$2 from entry (set in
`FIXED_STOP`). The engine refuses a distance outside the allowed band.

**Daily / weekly loss limits.** CPS stops trading after a bad run: 2% lost in a
day, or 10% in a week. The terminal **tracks your realised paper P&L** and prints
a clear **STOP** warning when a limit is hit — at the top of `run.py` each time,
and in a full audit you can run any time:

```
python limits.py
```

It lists every day that hit the 2% limit and every week that hit the 10% limit.
(In paper mode it only warns — it never blocks you.)

---

## The Signal Router — `python module_router.py`

The router is the part that **sorts and labels** a signal once it's been read. It
does **not** trade anything — it just looks at a signal and answers three
questions, then decides whether the signal is clean enough to act on or whether a
human should look first.

Think of it as the sorting desk in a mailroom: it reads the envelope and decides
which tray it belongs in. It never opens an account or sends any money.

For each signal it works out:

- **What is it?** The asset class. The engine sizes three classes today —
  **GOLD**, **SILVER**, **CRYPTO** (USDT/USDC pairs like FET, SOL, PEPE) and
  **FOREX** (currency pairs like EURUSD, GBPJPY, USDCAD). It also **recognises**
  three more it does **not** size yet — **OIL** (WTI/USOIL/BRENT…),
  **COMMODITIES** (NATGAS, COPPER, PLATINUM…) and **STOCKS** (AAPL, TSLA…) — and
  anything it can't place at all is **UNKNOWN**. All of the recognition rules
  live in `config.ASSET_CLASSES` (see *How assets are sized* below), so the
  classifier isn't hardcoded to gold.
- **Who called it?** The trader/source — matched against a list you control
  (`KNOWN_TRADERS` in `config.py`, e.g. `FAROUK`, `COLUMBUS`, `CHRIS`). Anything
  it doesn't recognise is tagged `UNKNOWN`. It's smart about suffixes, so
  `FAROUK-GOLD` and `FAROUK-LIMIT` both tag as `FAROUK`.
- **Where would it go later?** A **venue** label, from a mapping you control
  (`VENUE_MAP` in `config.py`): gold/silver/forex → `venue_A`, crypto → `venue_B`.
  **These are placeholder names on purpose** — you fill in the real venue names
  only when (and if) live trading is ever built. **Right now they are just
  labels. Nothing connects to any venue, and no order is ever placed.**

**The safety guard — the REVIEW bucket.** If the router can't tell what the asset
is (UNKNOWN), or the signal is **malformed** (no ticker, no entry, no stop-loss,
or a direction that isn't LONG/SHORT), it does **not guess**. It puts the signal
in a **REVIEW** bucket that means *"a human needs to look at this."* Better to ask
than to mis-route. (A signal that's fine but simply lists no take-profit targets
still routes — that's just noted, not bounced to review.)

It also sends a signal to REVIEW when the asset class is **recognised but not yet
calibrated for sizing** — OIL, COMMODITIES and STOCKS today. The message is
explicit: *"Asset class OIL recognised but not yet calibrated for sizing — human
review needed."* The engine would rather hand these to you than size them with
guessed maths. Turning one into a fully sized class later is a config change, not
a code change (below).

**Try it.** To watch it classify the real example signals (the crypto ones, gold,
silver, the Farouk gold calls) plus a few extra cases that show the FOREX and
REVIEW paths:

```
python module_router.py
```

It prints each signal's asset class, trader, venue, and ROUTE-or-REVIEW decision,
then a one-line summary. It reads nothing from the internet and changes nothing.

---

## How assets are sized — per-asset-class configuration

Different markets are sized with completely different maths. Gold moves in
dollars-per-point; forex is sized off **pip value**, which depends on the pair's
quote currency; crypto is sized as a **percentage of capital at risk**. The
engine keeps all of that in **one place** — the `ASSET_CLASSES` registry in
`config.py` — and the core code (the router that classifies, the risk calculator
that sizes) just **reads the registry and dispatches**. Nothing is hardcoded to
gold.

Each asset class entry declares:

- **`ledger_class`** — what gets written to the log's `asset_class` column
  (kept in the old METAL/CRYPTO/FOREX vocabulary so older logs still read).
- **`calibrated`** — `True` means the engine has trusted sizing for it and will
  size it in PAPER; `False` means *recognise it, but send it to human REVIEW*.
- **`sizing`** — the name of the sizing strategy to use (see below).
- **`params`** — the numbers that strategy needs (contract multiplier, pip /
  contract size, lot increments, minimum lot).
- **`slippage`** — the per-side price penalty modelled into the entry.
- **`verified` / `broker_note` / `flags`** — the honesty flags printed on the
  ticket (e.g. *CONFIRM WITH BROKER*).
- **`match`** — how the router recognises the class (a prefix like `XAU`, an
  explicit ticker list, or a structural rule for forex/crypto).

### The three sizing strategies today

| Strategy | Used by | How a position is sized |
|---|---|---|
| `dollar_per_point` | **GOLD**, **SILVER** | `risk ÷ (stop-distance × contract multiplier)`. Gold = 100 oz/lot ($100 per $1 move), silver = 5,000 oz/lot. **Unchanged from before.** Slippage $0.30/side gold, $0.03/side silver. |
| `pip_value` | **FOREX** | Sized in standard lots (1.0 lot = 100,000 units of the base currency). A pip's cash value is in the pair's **quote** currency, so it's converted to the account currency. **USD-quote pairs** (EURUSD…) use the engine's USD≈account 1:1 proxy. **Non-USD quotes** (USDCAD→CAD, crosses, JPY) are sized with an approximate rate and **loudly flagged `CONFIRM WITH BROKER`**, because the true pip value depends on a live FX rate the terminal doesn't know. |
| `percent_risk` | **CRYPTO** | Sized so a stop-out costs exactly your risk-% of the pot, in fractional coin **units** (no contract multiplier). Slippage is `0` for now and the ticket is flagged that **fees/spread aren't modelled yet**. |

> **Why USDCAD used to break.** It was being mis-tagged **CRYPTO** (the string
> `USDCAD` even contains `USDC`) and then sized with crypto maths — which
> produced ~28,000 "lots". The router now runs the structural **FOREX** check
> *before* crypto and matches crypto's stablecoin quote as a real quote *token*
> (not a substring), so `USDCAD` classifies FOREX and sizes to a sane ~0.28 lots.

### Adding a new asset class later

The future classes (**OIL**, **COMMODITIES**, **STOCKS**) are already recognised
and parked in REVIEW. To turn one — or a brand-new class — into a fully sized
class:

1. **Reuse an existing strategy?** Edit its entry in `config.ASSET_CLASSES`: set
   `"calibrated": True`, set `"sizing"` to one of `dollar_per_point` /
   `pip_value` / `percent_risk`, and fill in `"params"` (and `slippage`,
   `broker_note`, etc.). **That's it — no core code changes.** Add it to
   `VENUE_MAP` so it has a venue to route to.
2. **Need genuinely new maths?** Add one function to `SIZING_STRATEGIES` in
   `module_c_risk.py` (same shape as the three there), then name it in the class's
   `"sizing"` field.
3. **Recognising a brand-new class** is just another `ASSET_CLASSES` entry with a
   `"match"` rule (a ticker list for things like stocks, or `prefixes` for a
   family). Leave `"calibrated": False` until you trust its sizing — it'll route
   to REVIEW in the meantime.

Run `python test_multiasset.py` after any change — it checks USDCAD routes/sizes
as forex, gold still sizes exactly as before, crypto sizes by percentage, and oil
and stock tickers both land in REVIEW with the "not yet calibrated" message.

---

## The signal-quality filter — confidence tagging (`signal_quality.py`)

Traders usually tell you how much they trust their *own* call, right there in the
message. "A+ setup, 100% confident" is a very different shout from "high-risk, low
lot, against the trend — be careful". The quality filter reads those cues from the
raw signal text and tags every signal with a **confidence level**:

- **HIGH** — the trader signalled a strong, clean call (and no caution flags).
- **LOW** — the trader flagged caution/risk (and no strong flags).
- **NORMAL** — no cues found, or strong and caution cues cancel out. This is the
  default; a plain signal is NORMAL.

**It's a label, not a gatekeeper.** By default the filter is **information only**:
the confidence level is recorded on the logged trade, but it does **not** change
position size and does **not** block anything. The whole point is to *gather data
first* — so that later, `review.py` and `status.py` can show you whether the
trader's HIGH-confidence calls actually win more (and pay more) than their LOW
ones. You'll see a **BY CONFIDENCE** block, e.g.:

```
  BY CONFIDENCE  (the trader's own risk flags — do HIGH calls outperform LOW?)
    HIGH      ...  win rate 67%   +1.00 R/trade
    NORMAL    ...  win rate 50%   +0.00 R/trade
    LOW       ...  win rate 33%   +0.00 R/trade
    Read: HIGH +1.00 vs LOW +0.00 R/trade — HIGH is beating LOW.
```

**The keyword lists are yours to tune.** Both live in `config.py` as
`CONFIDENCE_LOW_CUES` (caution phrases → lower confidence) and
`CONFIDENCE_HIGH_CUES` (strong phrases → higher confidence). Add the exact words
your traders use. Matching is case- and hyphen-insensitive and works on whole
words/phrases, so `low lot` matches "low lot" and "low-lot" but not unrelated
text.

**The optional skip switch (off by default).** There's one more setting:

```
SKIP_LOW_CONFIDENCE = False     # in config.py
```

Leave it **False** (the default) and LOW signals are simply tagged and processed
like any other. If — and only if — your own review data later shows LOW-confidence
trades genuinely underperform, you can set it **True**: then the pipeline routes
LOW-confidence signals to the **human REVIEW bucket** instead of auto-processing
them. It's deliberately off to begin with, so you decide based on *your* numbers,
not a guess. (Even when on, nothing is executed — a routed trade is still only
sized and logged on paper.)

This is metadata only: it reads text and attaches a label. It sizes nothing,
moves no money, and never touches the LIVE stub. Run `python test_signal_quality.py`
to exercise it.

---

## The audit trail — the machine's black box (`python audit.py`)

Your terminal makes a lot of decisions — parse this, route that, circuit-breaker
pass or fail, sized or rejected, logged or stopped. The **audit trail** writes
every one of them down, permanently, so you can always answer *"why did the
machine do that?"* — even months later.

Every time a signal goes through `pipeline.py`, it writes **one entry** to
`audit_log.jsonl` recording the whole journey:

- **when** it happened (timestamp),
- the **raw signal** text that came in,
- the **parse** result (or parse failure),
- the **human confirm** (yes/no),
- the **routing** decision (asset / trader / venue, or REVIEW + why),
- the **circuit-breaker** verdict (pass, or blocked + reason),
- the **sizing** result (lots, entry, risk, R:R — or the rejection reason),
- the **final outcome** (logged, or stopped and exactly why).

So one line = one signal's complete story, the full chain of what happened and
why — for trades that went through *and* trades the machine refused.

**It is permanent and append-only.** The file is only ever *added to* — it never
overwrites and never deletes. **It is immutable: never edit it by hand.** That's
the whole point of a black box — a record you can trust precisely because it
can't be quietly changed after the fact. (It's also read-only with respect to
your `paper_log.csv`; it only writes its own file.)

**Why a serious system needs this.** When you've got months of history and you
ask *"why was that one rejected back in March?"* or *"what exactly happened the
day the circuit breaker fired?"*, the audit trail tells you, decision by decision.
Accountability, traceability, trust — a serious system can always show its
working.

**Review the history:**

```
python audit.py            # the last 20 entries, most recent first
python audit.py 50         # the last 50
```

Each entry prints as a clean, readable block. It's a viewer only — it reads the
log and prints; it changes nothing.

---

## The status dashboard — `python status.py`

Want the whole picture in one glance? Run:

```
python status.py
```

It's a **read-only** dashboard — it reads `paper_log.csv` and `config.py` and
prints; it changes nothing, logs nothing, and places nothing. In one screen it
shows:

- **Mode, pot, and risk per trade** — and the slippage model in force.
- **Execution status, loud and clear** — `EXECUTION_ENABLED = False` and
  `*** LIVE TRADING DISABLED — paper only ***`, so you're never in any doubt.
- **Circuit-breaker headroom** — today's and this week's realised P&L, and how
  much loss room is left before the 2% daily / 10% weekly stops, plus whether new
  trades are currently CLEAR or BLOCKED.
- **Your overall edge** — total trades logged (filled / missed / awaiting), win
  rate, expectancy (after modelled slippage), and net **R** and **£**.
- **A breakdown by trader/source** — sample size, fill rate, win rate, and
  expectancy for `FAROUK-GOLD`, `FAROUK-LIMIT`, etc., side by side so you can
  compare which feed is actually carrying your edge.
- **Trades awaiting an outcome** — how many logged trades are still unresolved
  (the "unclear / CONFIRM" ones) and how to record them.
- **A trust note** — anything built on fewer than 30 trades is marked `[<30]`,
  so a small, flattering sample never gets mistaken for a proven edge.

Every number is computed by reusing `review.py` and `limits.py`, so the dashboard
always agrees with those tools exactly.

---

## A visual view of a trade — `python chart.py`

`status.py` and `review.py` give you the numbers. `chart.py` gives you a **picture**
of a single trade — a clean image showing that trade's own levels on a price axis:
the **entry** line, the **stop-loss** line, and the **take-profit targets**, each
clearly labelled, with the trade's **direction** (LONG ▲ / SHORT ▼) and how it
finished. The risk side (entry→stop) is shaded red and the reward side
(entry→targets) green, and a light orange "illustrative path" runs from the entry
toward however the trade actually ended (win / stop / breakeven) just to make the
picture readable.

**This is a view of your PAPER trades — nothing more.** There is **no live market
data** here: it doesn't fetch a single price from anywhere. It only ever draws the
levels that are already logged in `paper_log.csv`. The orange line is **not real
price movement** — it's a drawn illustration, and it says so on the chart. Every
image is stamped **"PAPER TRADE — illustration only, not live."**

**Pick a trade the same way as `outcome.py`** — by number from a list, or just grab
the most recent:

```
python chart.py                 # show a numbered list (newest first), then pick
python chart.py last            # chart the most recent trade, no prompt
python chart.py 3               # chart trade #3 from the list
python chart.py 1,3,5           # chart a few at once
python chart.py last --out C:/somewhere   # choose where the image is saved
```

The images are saved as PNG files in a **`charts/`** folder next to the script
(one file per trade, e.g. `chart_01_XAUUSD_2026-06-25.png`), and the tool prints
the full path so you can open them. Trades with no take-profit targets logged just
show entry and stop (and say so); a `MISSED` signal shows its levels with no path,
because the entry never filled.

It needs the **matplotlib** charting library — if it isn't installed, the tool
says so in plain English (`pip install matplotlib`) and stops. Like the other
read-only tools, `chart.py` **only reads** `paper_log.csv` — it never writes to
it, connects to no broker, places no order, and never touches the LIVE stub.

> **Real broker charts are a later, post-proof step.** Drawing live candlesticks
> with actual market data (and, eventually, overlaying a real order) only makes
> sense once the paper record has shown a genuine edge and live trading is built
> deliberately, with guidance. For now this is exactly what it should be: a
> picture of the trades you've logged on paper.

---

## Assessing a trader — `python assess_trader.py`

> **This is an ADVISORY analyst aid — a judgment tool, NOT an automated decision.**
> It does **not** change sizing, block trades, route anything, or touch the
> pipeline or the LIVE stub. It writes you an honest opinion; **you** decide what
> to do with it.

Following someone's signals is a trust relationship, and trust should be earned
and re-checked. This tool reads a trader's track record from your paper log (and,
optionally, a file of their raw messages) and writes a plain-English assessment of
whether they still deserve your trust — flagging behavioural and integrity changes
over time.

It covers:

- **Discipline** — do they use stops and consistent sizing, and avoid FOMO? Any
  drift over time (e.g. "small size" → "going bigger", or "forget stops")?
- **Integrity / honesty** — do their *claims* ("20-0", "risk-free", "never lose")
  match their *actual logged loss record*? Mismatches are flagged explicitly.
- **Sales / marketing creep** — are they shifting from trading to *selling*
  (copy-bot funnels, "join my VIP", upsells, scarcity tactics)?
- **Edge trend** — is their logged win rate / expectancy improving, stable, or
  declining (first half vs second half of their trades)?
- **A verdict** — **KEEP FOLLOWING / WATCH CLOSELY / REDUCE TRUST**, with reasons.

**Grounded in your real numbers.** The integrity check isn't guesswork: the
**facts** (win rate, the exact loss dates, sizing over time, stop usage, edge
trend) are computed in Python straight from `paper_log.csv` — the same maths
`review.py` uses — and shown to you in the report. The written analysis is
produced by Claude (the same `ANTHROPIC_API_KEY` setup as the parser), reading
those facts plus any messages, and is told to treat the facts as ground truth and
never invent trades or losses.

How to run it:

```
python assess_trader.py                       # list the traders found in your log
python assess_trader.py FAROUK                # assess from logged trades
python assess_trader.py FAROUK --messages traders/farouk_messages.txt
python assess_trader.py FAROUK --facts-only   # just the computed facts, NO API call
python assess_trader.py FAROUK --out traders/farouk_assessment.txt
```

To analyse their *language* too, drop their raw messages into
`traders/<name>_messages.txt` (the tool auto-loads it; see `traders/README.md`).
Without messages it still assesses discipline, the edge trend, and integrity from
the log alone. The **`--facts-only`** mode needs no API key — it just prints the
computed track record, which is handy on its own.

**Read-only and safe.** It only ever *reads* `paper_log.csv` (it never writes to
it), and the optional `--out` saves the written report to a file you name —
nothing else. If `ANTHROPIC_API_KEY` isn't set it says so plainly and points you
at `--facts-only`. PAPER mode throughout; the LIVE stub is untouched. Treat its
verdict as a second opinion to inform your own — not a rule that acts on its own.

---

## Do they follow their own rules? — `python check_rules.py`

> **Advisory analysis only.** Like the assessor, this is a judgment aid. It is
> read-only, **not** part of the trade pipeline, and it changes no sizing and
> blocks no trade. It tells you whether a trader *practises what they preach* —
> and whether their rules actually correlate with profit.

A good trader has rules. This tool checks whether they **keep** them. You write a
trader's stated rules in a plain-English file (`traders/<name>_rules.json`), and
it measures their logged trades against those rules.

A FAROUK rule set is pre-populated (`traders/farouk_rules.json`) with his actual
stated rules — always use a stop, small/consistent size (0.5–1%), avoid high
leverage, move stop to breakeven once in profit, take partials, don't chase a
missed entry, no FOMO, "one good trade is enough", and don't trade emotional/on
high-impact news.

It reports three things:

1. **Rule adherence** — for each rule, how often the logged trades appear to
   follow it. **Crucially, where the data can't show it, it says so** ("can't
   determine from data") instead of guessing — and it never counts *absence of
   evidence* as a breach. (Leverage, for example, isn't in the log at all, so
   that rule is honestly marked undetectable.)
2. **Rule profitability** — do rule-**compliant** trades outperform rule-
   **breaking** ones? e.g. trades *with* a stop vs *without*; in-size vs
   oversized; one-trade days vs multi-entry days — each shown as sample size,
   win rate and expectancy, with small groups flagged.
3. **Plain-English summary** — which rules correlate with wins and which breaks
   correlate with losses, followed by an explicit **DATA LIMITS** section spelling
   out what the log simply can't show.

```
python check_rules.py                 # list traders + whether a rules file exists
python check_rules.py FAROUK          # check against traders/farouk_rules.json
python check_rules.py FAROUK --rules <path.json>   # use a different rules file
python check_rules.py FAROUK --out traders/farouk_rules_report.txt
```

**How rules are defined.** Each rule has a plain-English `statement` (edit it
freely) and a `check` telling the tool how to look for it: `stop_present`,
`risk_pct_band`, `notes_evidence` (scans your trade notes), `one_trade_per_day`,
`logs_misses_not_chase`, or `not_detectable` for anything the log can't show. The
file's own `_help` block lists them. Add your own rules the same way.

**No API key needed** — this is pure analysis of your own logged numbers (the R
and win rates come from the same maths as `review.py`). Read-only to
`paper_log.csv`; PAPER mode; the LIVE stub is untouched. As always: correlation
isn't proof, and this informs your judgment rather than acting on its own.

---

## The connected pipeline — `python pipeline.py`

Up to here, each part has been its own tool: the **parser** reads a signal, the
**router** sorts it, the **risk calculator** sizes it, the **logger** records it.
`pipeline.py` is the **conveyor belt that joins them all** so one signal flows
through every stage in a single go, and you can watch it move:

1. **PARSE** — read your pasted signal into structured numbers.
2. **HUMAN CONFIRM** (the amber step) — it shows you what it read and waits for
   your **y/n**. This safety catch stays — *you* approve the numbers (especially
   the stop-loss) before anything else happens.
3. **ROUTE** — classify the asset, trader, and intended venue. **If the router
   sends it to REVIEW** (unknown asset or a malformed signal), the pipeline
   **STOPS right here and tells you it needs human eyes** — it does *not* go on
   to sizing or logging.
4. **CIRCUIT BREAKER** — check today's and this week's realised losses against
   the loss limits (daily 2%, weekly 10% of the pot). **If a limit is already
   hit, the pipeline STOPS and refuses the trade** (see below). If you're *close*
   to a limit it prints a warning but lets the trade through.
5. **SIZE** — work out the hard-capped 1% position. **If it can't be sized**
   (e.g. the stop is too far and the size rounds to zero, or the stop is on the
   wrong side of the entry), it **STOPS** with the clear reason.
6. **LOG** — write the trade to `paper_log.csv`, now **including the routing
   tags** (trader, channel, venue, and the finer asset class), with the outcome
   left blank for you to fill in later via `python outcome.py`.

**It stops gracefully, never crashes.** If you say the numbers are wrong, or the
router flags REVIEW, or it can't be sized — the pipeline halts cleanly and prints
a plain-English reason. It never pushes a signal past a stop.

**Still PAPER only.** Nothing in the pipeline connects to an exchange, places an
order, or moves money. There is no live path; the LIVE stub is untouched.

**Run it on a real signal:**

```
python pipeline.py
```

Paste a signal, answer the amber `y/n`, and watch it travel through all five
stages. (It also asks a few optional questions — who called it, session,
timeframe, which channel — so the router can tag it; press Enter to skip any.)

**Watch the demo (no API key needed):**

```
python pipeline.py --test
```

This runs a real Farouk gold call through every stage end to end — parse →
confirm (auto-answered for the demo) → route → size → log — so you can see the
whole flow at once before pasting your own.

### The circuit breaker — your capital's kill-switch

Stage 4 is the **circuit breaker**, and it's the part that makes this behave like
a grown-up, institutional system rather than a toy.

**What it does.** Before any new trade is sized or logged, it adds up the losses
you've *actually* booked — **today** (for the daily limit) and **this week** (for
the weekly limit) — straight from `paper_log.csv`. If those losses have already
reached the limits, it **refuses the new trade** with a plain message:

```
CIRCUIT BREAKER: daily 2% loss limit reached (£-280.00 today) —
no new trades today. The machine is protecting your capital.
```

The limits are **2% of the pot in a day** and **10% in a week** (set in
`config.py`). A blocked trade is **not sized and not logged** — the machine simply
won't let you open it. If you're merely *close* to a limit (within 0.5% of the
pot of it), it prints a **warning** but still lets the trade through, so you get a
heads-up before the door shuts.

**Why an institutional system must have one.** The single fastest way a trading
account dies is *revenge trading* after a bad run — taking more, bigger trades to
"win it back," which usually digs the hole deeper. A circuit breaker removes that
decision from you in the heat of the moment: once you've lost your daily or weekly
cap, the system stops opening new trades, full stop. Every serious desk has hard
loss limits that halt trading automatically — it's not about predicting the
market, it's about guaranteeing you live to trade another day. This is that brick.

(It reads your *realised* results, so it reflects exactly what you've logged. In
PAPER mode the only thing it "stops" is the pipeline opening a new paper trade —
there is no live order to stop.)

**See it work:**

```
python pipeline.py --test-breaker
```

This seeds a throwaway log where today has already hit the 2% daily limit (two
stop-outs), then tries to push a fresh, valid gold signal through — and you'll
watch the pipeline refuse it at the circuit-breaker stage, before sizing or
logging. Your real `paper_log.csv` is left untouched.

> **`run.py` vs `pipeline.py`:** `run.py` is the original, simpler flow
> (parse → confirm → size → log) and still works. `pipeline.py` is the newer,
> fully **connected** flow that adds the **router** stage and the REVIEW safety
> stop in the middle. Use `pipeline.py` to get the routing tags in your log.

---

## Slippage — honest paper fills

When a signal says "enter at 5022", you almost never get filled at exactly 5022.
By the time your order actually executes, the price has usually moved a touch
against you — you get in a little **worse**. That gap is called **slippage**, and
it's real money on every single trade.

**Why paper-trading must model it.** If your paper log assumes perfect fills at
the exact signal price, your results will look **better than real life** — every
trade starts from a slightly-too-good entry, which quietly inflates your win rate
and expectancy. You'd think the edge is bigger than it is, then bleed the
difference when you go live. An honest paper system bakes slippage in from day
one, so the number you trust is the number you'll actually get.

**What this does.** When a trade is sized, the terminal **worsens the entry by a
per-side slippage estimate** before doing any maths. That makes the stop slightly
further away, the position slightly smaller, and the reward-to-risk slightly
lower — exactly what a realistic fill does. So the R:R on your ticket and the
**expectancy in `review.py` are already after slippage** — they don't flatter you.

You'll see it on every ticket, e.g.:

```
  Conservative entry  : 5022
  Slippage modelled   : $0.30 per side (worsens the fill)
  Sizing entry (used) : 5022.30   (after slippage — R:R below is honest)
```

and `review.py` says so plainly: *"expectancy +0.60 R/trade (avg realised R,
after modelled slippage)"*.

**It's an estimate — tune it.** Slippage is now set **per asset class**, right
next to that class's sizing, in the `ASSET_CLASSES` registry in `config.py`
(because gold and silver are priced very differently). For example:

```
ASSET_CLASSES = {
    "GOLD":   { ..., "slippage": "0.30", ... },  # $0.30 per side (tune to YOUR broker)
    "SILVER": { ..., "slippage": "0.03", ... },  # smaller price, smaller $/side
    "CRYPTO": { ..., "slippage": "0",    ... },  # 0 for now — fees/spread modelling pending
    "FOREX":  { ..., "slippage": "0",    ... },  # price units; tune per pair
}
```

(The old flat `SLIPPAGE = {"XAU": …}` table still exists for the dashboards, but
it's now **derived** from `ASSET_CLASSES` automatically, so the two can never
drift apart — edit the registry, not the derived table.)

Watch your real fills for a while, then set these to what you actually get. Higher
slippage = more honest (and more conservative) paper numbers. Still PAPER mode —
this only changes the maths on paper; it places no orders.

---

## The safety rules (built in, never weakened)

- **Hard risk cap.** No trade is ever sized above the active risk % (1% in Phase
  1; never more than the 3% hard cap). If the maths rounds, it rounds *down*.
- **Minimum lot.** If a trade can't be sized at or above the broker minimum
  (0.01 lot) within the risk budget, it's **skipped** with a clear message — the
  stop is simply too far for your pot. Protection, not a bug.
- **Bad signals are refused, loudly.** A stop on the wrong side of the entry zone
  is rejected and nothing is logged.
- **You eyeball every signal.** The parser shows you the numbers and waits for
  your `y`/`n` before anything proceeds. Real feeds have typos — the Columbus
  journal even had a trade where the SL/TPs had to be estimated from a typo'd
  signal — so a human checks the stop-loss *before* it's ever trusted.
- **Confirm metal specs with YOUR broker.** Gold/silver now use real contract
  numbers (Gold: 100 oz/lot, $1/point at 0.01 lot; Silver: 5,000 oz/lot, $50/$1
  move at 0.01 lot) — but the ticket still reminds you to confirm them with your
  own broker, because **Columbus uses VT Markets and yours (Bitget/other) may
  differ.**

---

## Checking the maths (optional)

To see the five real example signals sized and printed without pasting anything:

```
python module_c_risk.py
```

---

## The signal listener (Module A) — PREVIEW ONLY

Right now you capture signals by hand: you paste them into `python run.py`. The
**listener** is the piece that will eventually catch them *automatically* from
the Whale Room chat. It's built and ready — but it is deliberately **switched
off from the trading side**.

In **preview mode**, all the listener does is **print** each new message so you
can watch it catch them safely. It does **not** parse them, size them, log them,
or trade anything. It is not connected to `run.py` at all yet.

We'll connect it for real **later, together, on purpose** — only after you've run
at least one real signal through `run.py` by hand and confirmed which platform
the clean signals actually come from. It will never switch itself on.

> ### ⚠️ A warning about Discord
> Reading Discord with your **own user account** (your personal login) is called
> "self-botting", and it **breaks Discord's rules — accounts get banned for it.**
> The only allowed way is a *bot account that the group's admins add to the
> server*, which a private paid group almost certainly won't allow.
>
> So the Discord listener (`module_a_discord.py`) is **deliberately disabled** —
> it's just a warning if you run it. **Telegram is the safe automated route.**

> ### One more check before going live
> Before you ever switch the listener on, check the Whale Room's **own rules** on
> automated reading and re-sharing of their signals. Some paid groups forbid it.
> That's your call to make — the tool won't make it for you.

### Watching it work (Telegram, preview)

**1. Install the Telegram library.** In PowerShell:

```
pip install telethon
```

**2. Get your two Telegram credentials.**

- Go to <https://my.telegram.org> and log in with your Telegram phone number.
- Click **API development tools**.
- Fill in any app name (e.g. "signal terminal"), and it gives you two things:
  an **api_id** (a number) and an **api_hash** (a long code).

**3. Save those two as permanent environment variables** (same method as the
Anthropic key — `setx`, then open a fresh PowerShell):

```
setx TELEGRAM_API_ID "12345678"
setx TELEGRAM_API_HASH "your-long-api-hash-here"
```

**4. Tell it which channel to watch.** Open `config.py` and set `TELEGRAM_CHANNEL`:

```
TELEGRAM_CHANNEL = "@thewhaleroom"      # the channel's @username, or its numeric ID
```

To watch **more than one** channel at once, use a list:

```
TELEGRAM_CHANNEL = ["@thewhaleroom", "-1001234567890"]
```

**How to find a channel's @username or ID (plain English):**

- **The easy way — the @username.** Open the channel in Telegram and tap its name
  at the top to see its info. If it's a public channel you'll see a handle like
  `@thewhaleroom` (or a link `t.me/thewhaleroom` — the part after `t.me/` is the
  username). Put that, with the `@`, into the setting. This is all most channels
  need.
- **If there's no @username (a private channel)** you need its numeric ID instead.
  **The easiest way is the built-in helper** — once you've done the one-time login
  (step 5), run:

  ```
  python module_a_telegram.py --list
  ```

  It logs in and prints a **numbered list of every channel and group your account
  is in**, each with its **name and numeric ID**, like:

  ```
    1) The Whale Room
       ID: -1001234567890
    2) Gold Signals (private)
       ID: -1009876543210
  ```

  Find the one you want, copy its ID, and paste it (in quotes) into
  `TELEGRAM_CHANNEL`. This helper is **read-only** — it just lists your chats and
  exits; it watches nothing and changes nothing. Private-channel IDs look like
  `-1001234567890` (keep the leading `-100`).

**5. Run it in preview:**

```
python module_a_telegram.py
```

The first time, Telegram sends a **login code to your Telegram app** — type it in
when asked (and your 2-step password too, if you use one). After that it says
*"Listening..."* and every new message in the channel prints on screen, like:

```
[PREVIEW] Captured message at 2026-06-25 14:02:11
          Channel: The Whale Room
----------------------------------------------------------------
FET/USDT SHORT  zone 1.4334-1.4721  SL 1.5284 ...
----------------------------------------------------------------
```

Each catch shows **when** it arrived, **which channel** it came from, and the
**full message text**, tagged `[PREVIEW]`. Press **Ctrl+C** to stop. Nothing it
catches goes anywhere yet — it does **not** parse, size, log, or trade it. It's
purely a window into what the live version would see.

### "FloodWait" — and why the listener won't get you banned

**What it is.** Telegram protects itself from being hammered. If something logs
in or calls its API too often in a short time, Telegram replies with a
**FloodWaitError** that says, in effect, *"slow down — wait N seconds before you
try again."* It's a normal rate-limit cool-down, not a bug. The dangerous thing
is to **ignore it and keep retrying** — that's exactly what gets an account
temporarily restricted or banned.

**How this listener handles it (safely, by design).** The login/connection step
specifically watches for FloodWait, and:

- **Long waits (more than ~60 seconds, e.g. minutes or hours):** it does **not**
  sit there blocked and does **not** retry. It prints a plain-English message —
  *"Telegram has asked us to wait 2 hours before trying again. The script will NOT
  hammer the API. Stopping cleanly — try again after 2026-06-27 11:37."* — and
  exits. You simply come back and re-run the command after that time.
- **Short waits (under ~60 seconds):** it may wait that brief moment out **once**
  and then try **one** more time. If it's asked to wait again, it stops cleanly
  rather than looping.
- **It never retries in a rapid loop.** One clean attempt (plus, at most, that
  single short-wait retry). Any other login/auth error is reported clearly and
  the script stops — it never spins on the API.

So if you ever see the FloodWait message, nothing is broken: the listener is
deliberately backing off to keep your account safe. Wait for the time it prints,
then run it again. (Everything else is unchanged — it's still preview-only, the
`--list` helper still works, and no message is parsed, sized, logged, or traded.)

### Back-logging a channel's history — `--history`

The live preview only sees messages from *now* on. To study a channel's **past**
— e.g. to back-log a trader's history — use history mode:

```
python module_a_telegram.py --history 500
```

It pulls the last **N** messages from the configured channel, prints each one,
and shows what it **would** be classified as by the existing parser, router and
quality filter — **clean signal**, **commentary** (chatter), or **REVIEW**
(signal-shaped but needs a human/parse) — and writes a reviewable file,
`history_review.csv`. **It does not log anything to `paper_log.csv`.** You read
the list / the CSV and decide what, if anything, to do — nothing is auto-logged.

The review CSV has clean, **dedicated columns** so you can sort and filter it in
Excel:

```
Date, Sender, Asset, Direction, Entry, Stop, TP1, TP2, TP3, Classification,
Confidence, DetectedOutcome, OutcomeEvidence, RawMessage
```

Where a field can't be parsed it's left **blank** (it never guesses), and the full
original message is kept in the last column.

**It also captures OUTCOMES, not just entries.** Farouk posts follow-up
management/result messages after each entry ("tp1 hit", "sl to entry", "stopped
out", "+50 pips", "all tp hit", "no fill"). For each **clean entry signal**, the
puller looks at the later messages on the **same asset** — after that entry and
**before the next entry on that asset** — and fills two columns:

- **`DetectedOutcome`** — a **granular category** (see below) that rolls up to a
  coarse win / loss / breakeven / missed / unclear bucket via `outcome_group()`.
- **`OutcomeEvidence`** — the exact follow-up message it matched, so you can
  **verify** it.

The **granular categories** (each clean signal gets exactly one):

| Category | Bucket | How it's scored in `log_history.py` |
|---|---|---|
| `target_hit` | win | an **explicit hit** (or a bare take/now instruction with no pips) → R to that target; no price in the signal → fall back to stated pips |
| `managed_profit_confirmed` | win | a **stated pip** figure (with no explicit hit) → R from the pips vs risk, **capped at the furthest posted target**; preferred over a distant target that was only instructed |
| `profit_confirmed_r_unknown` | win | money was made but there's **no reconstructable quantity** (or the stop is **invalid**) → **0R** (never an assumed TP1) |
| `manual_loss` | loss | the **actual stated** loss (−pips vs risk); if the magnitude can't be stated, a negative loss **awaiting a manual −R** (never zero, never silently −1R) |
| `original_stop_loss` | loss | the original stop was hit → **−1R** |
| `breakeven` | breakeven | scratch / BE-stop → 0R |
| `missed` | missed | no fill (no trade) |
| `instruction_only` | unclear | in-context chatter/instructions, but no confirmed result |
| `unclear` | unclear | nothing to go on |

The cues map like this: a **named target** reached → `target_hit`; **stated pips**
of profit (with no named target) → `managed_profit_confirmed`; profit confirmed
with **no reconstructable quantity** ("closed in profit", "take tp", *"almost
reached tp1"*) → `profit_confirmed_r_unknown`; a **manual/net loss** ("cut for −40
pips", "closed for a loss", "count it as a loss overall", "close it for a small
loss", "1 win, 1 loss") → `manual_loss`; the **original stop** hit ("sl hit",
"stopped out") → `original_stop_loss`; "sl to entry" / "moved to breakeven" →
`breakeven` — deliberately **not** a loss; "no fill" / "didn't fill" → `missed`.
A **named target is preferred over a stated-pips figure** when both appear, because
the target reconstructs to a real price in the signal (Farouk's "pips" convention
is unreliable — "500 pips" is a ~50-point gold move). The win detection is broad
about how he phrases a result — *"tp1 hit"*, *"tp 1 now"*, *"take tp 1"*, a bare
*"tp 1"*, *"official tp1"*, *"small tp"*, *"we got 90 pips"*, *"all tp hit 500
pips"*, *"took profit"* — so genuine wins that used to slip through are caught.

**Two honesty fixes (these make the edge more conservative, never better):**

- **Manual / net losses are never dropped (P1).** A trade Farouk **cut by hand**
  ("cut for −40 pips", "closed for a loss", "manually closed") or declared a loss
  overall ("count the sequence as a loss") used to be mislabelled *missed* /
  *breakeven* / *unclear* and silently excluded from expectancy. It is now a
  `manual_loss`, scored at its **actual stated size** (−pips vs the trade's own
  risk) — **not** a flat −1R, **not** zero, and **never** dropped or relabelled.
  Only the **original stop** being hit is −1R (`original_stop_loss`).
- **R-unknown wins are not over-credited (P2).** A win with no reconstructable
  exit — "best layer closed in profit", *"almost reached tp1"* (which means TP1
  was **not** reached) — keeps its **win label** (money was made) but is scored
  **0R**, never an assumed TP1 R. "almost reached tp1" specifically must **not**
  credit TP1.

**Totals reconcile.** The history report prints a per-category count, the coarse
roll-up, and a **reconciliation line** — every clean-signal row is accounted for
(`wins + losses + breakevens + missed + r_unknown + instruction/unclear == total
clean signals`); any row that doesn't reconcile is flagged.

**Further accuracy corrections (a later audit — these move both ways, all toward truth):**

- **Evidence-link — store the strongest/latest confirmation.** When a trade has
  several follow-ups, `OutcomeEvidence` is now the **strongest** confirmation
  ("all TP hit 500 pips", "tp 1 official hit"), not the first instruction ("take
  tp 1"). A confirmed hit also outranks a later multi-trade recap that merely says
  *"almost hit TP1"*, so a trade's own win isn't displaced. This also un-buries
  reconstructable wins that were scoring 0R only because the first message was a
  bare instruction.
- **Reconstructable quantity ⇒ real R; only 0R when there's none.** If the
  evidence carries a stated pip figure **or** a named target with a price (or an
  exit price like "reached 63,900"), the **real R** is credited — 0R is reserved
  for a confirmed win with genuinely no stated quantity.
- **Manual/net-loss verdicts override an earlier partial.** Farouk's own closing
  word — "close it for a small loss", "1 win, 1 loss today", "some in profit, some
  in a loss … count it as a loss overall" — now reclassifies an otherwise
  r-unknown "win" to `manual_loss`. (A *day tally* that says "6 **trades**, 1 loss"
  is **not** a per-trade verdict and never flips a real tp win.)
- **A pip *range* is not a loss.** "still up **50-60 pips**" no longer reads the
  "-60" as a −60-pip manual loss; with the stop moved to entry and the entry-stop
  then hit and no banked partial, that trade is a **breakeven**.
- **A near-miss of the stop is not a missed entry.** "just missed our sl" is price
  nearly hitting the **stop**, not a no-fill — it's no longer counted as `missed`.
- **An invalid stop can't be scored.** A win on a trade whose stop is on the wrong
  side of entry (e.g. a LONG with the stop *above* entry) keeps its win label but
  is scored **0R** — a target R off an invalid stop would be meaningless.

**Score to the CONFIRMED result, never a distant unreached target (a later audit):**
A win is now sub-typed in three tiers — an explicit target **HIT** ("tp1 hit",
"all tp hit", "securing tp1") > a stated **PIP** figure ("we got 90 pips") > a bare
take/now **INSTRUCTION** ("take tp 1", "tp 1 now"). The consequences:

- **A pip figure outranks a bare instruction.** "50 pips tp 1" or "tp 1 we have 70
  pips" is scored to the **confirmed pips** (`managed_profit_confirmed`), not to a
  posted tp1/final target that was only *instructed*, never confirmed hit. When the
  confirmed pips are **smaller** than the target's R, the trade is scored to the
  pips — we never over-credit a distant target that wasn't reached.
- **An explicit HIT still gets full target R.** "all TP hit 500 pips" / "tp1 hit"
  stays `target_hit` at the target's R, even when a pip figure is also present.
- **Pip R is CAPPED at the furthest posted target.** A hyped "500 pips" on a gold
  trade whose furthest target is ~50 points away can never score more than that
  target's R — the unreliable gold "pip" can't inflate the edge.
- **The RE-ENTRY BOUNDARY cuts both ways (a later audit).** A parent trade is
  credited only with the result confirmed **before** the next *re-entry or new
  signal*; anything after the boundary belongs to the re-entry and must **not** leak
  backwards. So:
  - a trade that made **50 pips**, then "re-enter", then a **170-pip** result *after*
    the re-entry is scored to the **50 pips** only (the 170 belongs to the re-entry);
  - but a genuine pre-re-entry confirmation **is** credited — "**300 pips**" stated
    before any re-entry, on a signal with numerical targets, where 300 pips reaches
    **TP3**, is `target_hit` at TP3 (~+0.71R), not left as r-unknown.
  The attribution window therefore ends at the first re-entry marker **or** a fresh
  buy/sell-with-a-price, once the parent has a result.
- **Bare pip figures are read as confirmed results** ("300 pips", "50 pips",
  "50-60 pips") — but **unrealised** floats are excluded ("running 200 pips", "still
  up 50-60 pips", "after a 130-pip move", "almost 200 pips"). A bare float that then
  **scratches at the BE stop** with no banked partial stays a **breakeven**.
- **Gold "pips" are $0.10 increments.** Farouk's "300 pips" on gold is a ~30-**point**
  run, not 300 points; the detector converts pips→points (×0.1 for gold) before
  comparing to target distances and scoring R. This is what lets "300 pips" map to
  TP3 while "90 pips" / "50 pips" correctly stay small partials below the targets.
- **Evidence is the strongest confirmation BEFORE the boundary** — never borrowed
  from after a re-entry/new signal (so "300 pips" / "almost 200 pips" / "profit
  secured" is stored, not an earlier "TP1 now" / "take TP2" instruction).

These corrections change only **how wins are scored** (target_hit ⇄
managed_profit / r-unknown, all within the win bucket) — the win/loss/breakeven
roll-up is unchanged.

Guards that stop the breadth from over-crediting:

- **It won't read a TP *listing* as a hit.** Him *posting* the levels — "TP1 :
  4,334  TP2 : 4,329" or "take profit levels: …" — is not a result and scores
  nothing.
- **Asset / thread consistency.** A matched outcome must be the **same asset** as
  the entry (or carry no asset in the **same thread/section**). A gold trade is
  never scored from a "BTC tp1 hit" message, and a no-asset "tp1 hit" in a
  different channel section isn't borrowed.
- **Hypothetical win cues are suppressed (but the message is kept).** Educational
  or predictive posts — "if price breaks X you could see tp1", "I think we have a
  good chance of reaching…", "would have hit tp" — never read as a **win**. The
  message still enters the window, though, so a concrete verdict buried inside one
  ("…but better to close it for a small loss") is **not** lost.

**Chronological management — no retroactive breakeven.** The stop sits at its
**original** level until the message that actually moves it ("move SL to
entry/BE"). So the order of the follow-up messages matters:

- a stop being hit **before** any move-to-BE message → **loss** (the original
  stop) — it is *not* quietly turned into a breakeven just because he later moved
  to BE on a different occasion;
- a stop being hit **after** a move-to-BE message → **breakeven** (the BE stop);
- a move-to-BE with nothing after it → **breakeven** (protected/scratch);
- an explicit BE-stop hit ("SL at entry hit") → **breakeven**.

We can only approximate the timing from message **order** — so where we can't
tell, it stays **unclear**, never guessed.

**Verifiable outcomes only — credit STATED partials, never assumed ones.** It
scores what the messages actually state: "tp1 hit" = win **to tp1**, "all tp hit"
= full win, original-stop hit = loss, breakeven-stop = breakeven. Crucially, for a
trade where the runner later scratched at BE:

- if the follow-up **explicitly states a profit** was secured at a named level
  ("tp1 hit", "secured +40 pips", "took profit at X") *before* the scratch → it's
  a **small win to that stated level** (scored from the stated pips/target only);
- if the follow-up only says **"moved to BE" / "sl to entry" with no stated
  profit** → it **stays breakeven** — we can't verify any profit was made, so it's
  a scratch, honest by default.

It **never** assumes a 50% partial, and never invents a partial size or an exit
price the messages don't state. ("running 200 pips" is *unrealised*, and "secured
at breakeven" is *protected*, not profit — neither reads as a win.) Assuming
partials would flatter the edge (the vanity-metric trap), so we don't.

It is **conservative on purpose**: no follow-up, genuinely **ambiguous** ordering,
or an **overlapping** re-entry on the same asset before any result → **`unclear`**
with the evidence left **blank**. It never guesses, and it never auto-logs:
`DetectedOutcome` is an **aid you verify** (read `OutcomeEvidence`), then confirm
yourself in `log_history.py`. (Tests in `test_outcome_cues.py` lock down each cue,
the critical "sl to entry ≠ loss" distinction, the original-stop-before-BE-move =
loss vs BE-stop-after-move = breakeven chronology, the stated-partial = small win
rule, the honesty fixes — **manual loss never dropped**, *"almost reached tp1"*
**not** credited TP1 — the `original_stop_loss` vs `manual_loss` split, the
**reconciliation** invariant (every clean row → exactly one category), and the
later audit corrections — **evidence-link** (strongest confirmation stored, a
confirmed hit outranking a later "almost" recap), **net-loss verdicts** overriding
a partial ("close it for a small loss", "1 win, 1 loss"), a multi-trade *day tally*
**not** flipping a real win, a **pip range** ("50-60 pips") not read as a loss, a
**near-miss of the stop** not counted as missed, and an **invalid stop** kept as a
win but scored 0R — plus the **three-tier** scoring (explicit **hit** > stated
**pips** > bare **instruction**), the **pips-over-distant-target** rule, the
**furthest-target cap**, the **re-entry boundary** (post-re-entry / post-new-signal
results NOT leaked to the parent, while a genuine pre-boundary result IS credited),
**bare-pips** recognition with **unrealised floats excluded** (a float that then
scratches at BE → breakeven), the **gold $0.10 pip** conversion, and the guards
(TP-listings ignored, asset/thread mismatches rejected, hypothetical win cues
suppressed while the message is kept).
`test_log_history.py` checks the R-scoring: r-unknown / invalid-stop → 0R, a named
target with no signal price → stated pips, an exit price → R from price, gold pips
→ points (×0.1), pips **capped** at the furthest target, pips **smaller** than a
target → scored to the pips, an explicit hit → full target R, manual loss → its
real −R (or awaiting a manual −R when the magnitude can't be stated), original
stop → −1R.)

**Friction stays per asset class.** Slippage/spread is tied to the asset class in
`config.ASSET_CLASSES` — gold has its own value, forex/silver/crypto theirs — and
the sizing engine applies each class's own; **gold's spread is never applied to a
forex trade** (`test_multiasset.py` checks this).

Useful flags:

- **`--sender <name>`** — isolate one poster, e.g. `--sender farouk` to separate
  Farouk's posts from Columbus's and the general chatter. (On aggregator channels
  that prefix each post with "*name* Posted in …", it matches that name too, not
  just the Telegram sender.)
- **`--no-parse`** — skip the LLM and classify by a quick heuristic only (free, no
  API key needed). Signal-shaped messages are marked REVIEW with best-effort
  fields; chatter is `commentary`.
- **`--out <file>`** — write the review CSV somewhere other than
  `history_review.csv`.

```
python module_a_telegram.py --history 500 --sender farouk
python module_a_telegram.py --history 500 --no-parse
```

**Careful and safe by design.** It's **read-only** to Telegram (it only reads past
messages) and never writes to your paper log. The count is **capped** so a typo
can't ask for a giant fetch, and it makes **one careful fetch** that respects the
same **FloodWait** protection as the rest of the listener: small cool-downs are
waited out, a big one is reported and the fetch stops cleanly (saving whatever it
already pulled). To keep API use sane, obvious chatter is classified as
commentary without any parse, and clear one-line signals are read by the
**deterministic parser** (below) with **no API call at all** — the LLM is only a
fallback for messages that parser can't read confidently. So even with
`--no-parse` (or no key set) it still recognises clean signals. PAPER mode
throughout; the LIVE stub is untouched.

### Entry zones (ranges) and the conservative fill

Traders' formatting drifts. The deterministic parser reads it all with flexible,
**case-insensitive** regex — no guessing, no LLM needed:

- **Asset:** `XAUUSD` / `GOLD` / `Gold` / `gold` → **XAUUSD**; `SILVER`/`Silver` →
  **XAGUSD**.
- **Direction & order type:** `buy` / `buy now` / `buy limit`, `sell` / `sell now`
  / `sell limit` (market vs limit is recorded too).
- **Flexible entry:** the marker may be `@`, `at`, or just a space — a single
  price (`@ 2311`, `@2311`, `2311`) **or** a hyphen range (`@ 2312 - 2309`,
  `2312-2309`, any spacing). A range **keeps both ends** (`entry_low`/`entry_high`)
  so nothing is lost, and records a single **primary entry for sizing = the
  conservative end** (BUY → the *higher* price, SELL → the *lower* price), **never
  the midpoint** — so sizing/expectancy is never flattered. (Shown on the confirm
  readout as "Primary entry".)
- **Lax punctuation:** `SL:`, `SL-`, `SL`, `sl` and `TP1`/`tp1:`/`tp1-` are all
  read regardless of spacing/punctuation (and the `1` in `tp1` is never mistaken
  for a target price).

**Classification — management never auto-promotes.** A message becomes a **clean
signal** only when it has **asset + direction + entry + a stop** *and* contains no
management/update phrase. A **management phrase** — `tp hit`, `tp1 hit`, `running`,
`in profit`, `move sl`, `sl to entry`, `move to breakeven`, `close half`,
`take partial`, `X pips` — is **never** auto-promoted to a fresh signal. Then:

- **Pure management** (a phrase but *no* complete fresh entry) → **commentary**.
  e.g. *"we got 100 pips on gold, move sl to 2312"*, *"gold tp1 hit, move sl to
  entry"*, *"close half the position"*.
- **Re-entry** (a management phrase **and** a complete fresh signal — direction +
  entry zone + stop, even if the asset is implied) → **REVIEW**, not commentary.
  e.g. *"SL to entry was hit again. BUY Entry: 4339-4330 SL: 4318"*. These often
  *are* a real new trade, so they're **surfaced for your review** rather than
  buried — but still **never auto-logged**.
- A message that mentions an asset and numbers but lacks a stop or a direction →
  **REVIEW** (incomplete; a human should look).

So `GOLD buy @ 2315 sl 2305` and `XAUUSD Sell 2345 SL:2360` become clean signals;
pure updates stay commentary; and a re-entry lands in REVIEW where you'll see it.
`test_parser_zone.py` locks all of this down.

### Logging reviewed history into the paper log — `python log_history.py`

`--history` produces `history_review.csv` (a list of past signals, classified) but
**logs nothing**. When you're ready to turn the good ones into real paper trades —
with outcomes, and without duplicates — this helper walks you through them **one at
a time** instead of hand-editing the CSV:

```
python log_history.py                  # walk the "clean signal" rows
python log_history.py --include-review   # also walk the REVIEW rows
```

For each signal it shows the full details (date, asset, direction, entry zone,
conservative primary entry, stop, targets, raw message), then asks you two things:

1. **NEW, DUPLICATE, or SKIP?** It first **auto-checks** `paper_log.csv` for a
   likely match (same asset + direction + same day + a nearby entry) and **warns**
   *"this looks like it may already be logged"*, showing the matching row(s) — but
   **you** decide.
2. **Outcome?** `win / loss / breakeven / missed / unclear / skip` — the same
   vocabulary as `outcome.py`.

Only the ones you confirm are written, and they go through the **normal engine** —
`module_router` for the routing tags and `module_c_risk` for sizing — so the
**conservative entry, slippage and the 1% cap are applied exactly as everywhere
else**. The trade is logged under its **original (historical) date**, not today.

A *win* is scored at its **real R from the trade's own levels**, from the STATED
outcome only — **not +1R flat**:

- evidence that a named target was reached ("tp1 hit") → the **R from entry to
  that target** (so a *tp1-then-scratched* small win logs at the small R to TP1,
  e.g. +0.12R, not +1R);
- "all tp" / all targets → the **full R** to the furthest target;
- if the stated info can't give an R (only "+X pips", or the signal had no target
  prices) → it **asks you** which target / the R, or **marks the row for manual
  entry** — it never assumes a partial size or a guessed exit price.

*loss* → stop-out (−1R); *breakeven* → 0R; *unclear* is logged but left awaiting.

Safe by design:

- It makes a **timestamped backup** of `paper_log.csv` before it starts (and
  prints the path, so you can always undo).
- It **never logs without your per-trade confirmation**; duplicates and skips are
  never written.
- It shows a **running tally** (logged / skipped / duplicates) and a final summary.
- Signals it can't size through the engine (e.g. no stop, or an uncalibrated asset)
  are reported and left for you — never logged with guessed maths.

PAPER mode throughout; read-only to `history_review.csv`; the LIVE stub is
untouched. When you're done, `python review.py` / `python status.py` show the
updated numbers.

### What changes to go live (later, together)

When you've proven the manual flow and confirmed the source, going live is a
single, clearly-marked line inside `module_a_telegram.py` (search for
`ENABLE TO GO LIVE`) that hands each caught message to the parser. We'll enable
that line and set `LISTENER_MODE = "LIVE"` in `config.py` **deliberately, with
guidance** — it never happens by itself.

---

## The permanent archive — `python archive.py` (Phase 1)

The history back-log above reads a **shifting** 1500-message window: pull again a
week later and old messages have scrolled off the end. That's fine for a spot
check, but it can't be a permanent record. The archive fixes that. It is a
**permanent, append-only store** where **SQLite is the source of truth** and CSV is
an **export only**. Nothing is ever silently lost or overwritten.

  * **PAPER mode, read-only to Telegram.** It never touches `paper_log.csv` or the
    LIVE stub. The DB lives at `data/signal_archive.db` (WAL mode, foreign keys on,
    UTC timestamps, one transaction per import — success commits, failure rolls
    back with **no partial batch**).
  * **Append-only where it matters.** Raw messages, outcome evidence, and manual
    overrides are **never updated or deleted**. If Telegram *edits* a message (same
    key, new content hash) a **new version is appended**, never overwritten.
    Outcome **projections** are the one derived table — fully rebuildable from raw
    messages + signals + overrides.

**Eight tables (the lean Phase 1 core plus the v2 timing capture):** `schema_meta` (version, for safe future
migrations), `import_batches` (one row per pull: counts + status + code/detector
version), `raw_message_versions` (every message version, `UNIQUE(message_key,
content_hash)`), `signals` (parsed entries, `UNIQUE(source_message_key,
source_signal_index)` — **not** deduped on date+asset+price, since legitimate
signals can collide), `outcome_evidence` (append-only; **rejected** evidence is
recorded too — `accepted=false` with a reason like `POST_REENTRY_BOUNDARY` or
`WRONG_ASSET` — so nothing is silently ignored), `outcome_projections` (the current
calculated result per signal), `manual_overrides` (append-only; never edited —
**superseded** by a new row), and `signal_timing` (append-only timestamp +
price-context capture — see below).

**Projection precedence:** active manual override **>** verified deterministic
evidence **>** accepted automatic evidence **>** unknown. An auto-run may **report**
a conflict with an override (stored in `override_conflict`) but **never replaces**
it.

### Timestamp + price-context capture (groundwork for shadow mode)

`signal_timing` (added in schema v2) is **foundational groundwork** for a future
**shadow mode** — it RECORDS the raw timing and price data shadow mode will need,
**without building shadow mode itself**. It computes **no** shadow result. For each
captured signal it stores, append-only (one row per signal, captured once, never
overwritten — `INSERT OR IGNORE`):

  * **Per-stage timestamps (UTC):** `telegram_posted_at` (the message's own
    timestamp), `listener_received_at` (when our listener took the message off the
    fetch), and `parsed_at` (when parsing completed). Whatever is available is
    captured — historical back-fills (the baseline) only have the telegram
    timestamp, so the later stages are left blank.
  * **Processing delays:** `received_minus_posted_sec` (capture latency — small for
    live, ≈ message age for back-fills) and `parsed_minus_received_sec` (parse
    processing time), each `NULL` when an endpoint is missing. These let us later
    see **where** latency occurs.
  * **`price_context` (JSON):** the prices available at capture — the signal's own
    entry/stop levels and any prices found in the message — **plus a clearly
    labelled, currently-`null` `market_price` slot**. The real broker/market price
    is **NOT** integrated yet: it is captured and the shadow result calculated **in
    the shadow-mode phase, a separate future build**. Nothing here reads a live
    price or computes a fill.

`archive-status` reports timing coverage and the average parse delay / capture lag;
`integrity-check` verifies every signal has a timing row. Tests cover stage capture,
exact delay calculation (incl. the historical format), the `null` market-price
placeholder, and append-only idempotency.

**The re-entry boundary is preserved.** The matcher only credits a signal with
evidence **after the source signal and before the first re-entry / new-signal
boundary** (the signed-off boundary logic). Post-boundary evidence is still
stored — as `accepted=false` — so the audit trail is complete. A follow-up TP that
arrives in a **later** pull simply appends a new evidence row and recalculates
**that one** signal's projection, without duplicating the signal.

**Commands:**

```
python archive.py import [--csv FILE | --limit N --sender NAME]  # a pull into the archive
python archive.py rebuild-projections      # re-derive every projection (idempotent)
python archive.py export-csv [--out FILE]  # deterministic per-signal CSV (export only)
python archive.py backup                   # consistent timestamped DB copy -> data/backups/
python archive.py integrity-check          # PRAGMA integrity + FK check + invariants
python archive.py archive-status           # counts, distribution, gold known-R average
python archive.py baseline                 # one-time: build + VERIFY the signed-off baseline
```

**Baseline.** `python archive.py baseline` imports the signed-off sample
(`history_review_FINAL_SIGNOFF.csv`) — all 386 raw messages and the 28 stable
primary signals — runs the detector, adds manual overrides **only** where the
signed-off audit differs from the automatic result (currently **none**: the archive
reproduces the detector exactly), rebuilds projections, exports the CSV, and
**verifies it reproduces the signed-off baseline**: **24 win / 3 loss / 1
breakeven**, gold known-R average **≈ +0.34R** (n=17). It writes a tamper-evident
**manifest** to `data/audit_snapshots/baseline_<date>.json` (signal count,
distribution, source-CSV hash, logical DB hash, detector/calc versions, test count,
date). The build **exits non-zero** if verification fails.

**Eight acceptance tests** (`python test_archive.py`) lock the guarantees: import
the same pull twice → no duplicates; an overlapping pull → only new messages added;
the window slides → archived signals **remain**; a later TP → updates the right
signal's projection with **no duplicate signal**; a post-re-entry TP → **not**
leaked into the parent (stored `accepted=false`); a manual override → **survives** a
parser re-run; a crash mid-import → **rolls back**, no partial batch; two exports of
an unchanged DB → **identical**.

*Deferred to Phase 2 (not built yet):* versioned signal revisions, full
candidate-link scoring, channel sync-state, scheduled backups, gap detection,
re-entry entities, an audit UI, and a Postgres backend.

---

## Shadow mode — Phase 1a: the price-data foundation

**What this is.** The `market_price` slot above used to be a `null` placeholder.
Phase 1a builds — and *proves* — the piece that fills it: a real historical
**gold tick-price source**, so a future shadow calculation can ask *"what was the
market actually doing when this signal was posted?"* Phase 1a does **only** quote
lookup and quality measurement. It computes **no** shadow result, **no** R, **no**
ledger, **no** expectancy, **no** no-chase. PAPER mode, read-only, `EXECUTION_ENABLED`
stays `False`, the LIVE stub is untouched.

**The data source (proven reachable).** Dukascopy historical tick data, fetched
over plain HTTPS, stdlib only (no API key, no third-party packages):

```
GET https://datafeed.dukascopy.com/datafeed/XAUUSD/{YYYY}/{MM0}/{DD}/{HH}h_ticks.bi5
```

`{MM0}` is the **zero-indexed** month (Jan = 00). The body is LZMA-compressed
20-byte big-endian records `>IIIff` = (ms-into-hour, ask×1000, bid×1000, ask-vol,
bid-vol); XAU/USD prices are points ÷ 1000 (3 dp). Observed responses, used to
tell *closed* from *missing*: **200 + body** = ticks; **200 + zero bytes** = an
empty hour (market closed or a gap); **404** = the hour is not published
(`DATA_MISSING`). Verified live: an active hour returns ~37k clean ticks, ask ≥ bid
on every record, sub-second stamps, spreads ~$0.4–0.8.

**Two grades, kept separate.** Every lookup reports a **timestamp grade** (how well
we know *when*) and a **price grade** (how well-quoted that instant was):

| Timestamp | meaning | | Price | meaning |
|-----------|---------|-|-------|---------|
| **T-A** | receipt, ms precision | | **P-A** | bracketing ticks ≤ 1s apart |
| **T-B** | receipt, second precision | | **P-B** | ≤ 5s apart |
| **T-C** | **posted-only** (message's own time) | | **P-C** | > 5s (or a 5s-candle source) |
| **T-U** | unknown | | **P-D** | minute / midpoint only |
| | | | **P-U** | no usable price |

> **The archive's 28 timestamps are all `telegram_posted_at` — posted-only, minute
> resolution — so every one is T-C. By rule, a T-C result can *never* be called
> "exact executable":** you cannot claim an executable price for a time you only
> know to the minute. The price grade still measures how well-quoted the instant
> was; the timestamp grade caps what you may claim about it.

**No interpolation, no forward-fill.** A lookup returns the two **real** bracketing
ticks (the tick *before* and the tick *after*, each with bid, ask and gap-ms). It
never invents a single price between them, and it never carries a stale price across
an empty/closed hour. If only one side exists, the price grade is **P-U** — we
refuse to forward-fill the single side.

**Closed ≠ missing.** `gold_calendar.py` knows the spot-gold session: weekends
(Fri 17:00 ET → Sun 18:00 ET), the daily settlement break (Mon–Thu 17:00–18:00 ET,
seasonal — 21–22 UTC in summer, 22–23 UTC in winter, computed from the US DST rule
with **no** tz-database dependency), and US holidays. Holidays are **advisory**:
spot metals trade *thin* (often an early close) on most US holidays rather than
shutting — Dukascopy returns a full hour of ticks on Memorial Day — so the actual
data presence arbitrates, and a holiday is used to *explain* a gap, never to
fabricate a closure.

**Immutable, hashed, reproducible cache.** `price_cache.py` stores each hour under
`data/price_cache/` with the **SHA-256** of the exact compressed body plus the
normalised ticks. A repeat download reproduces **byte-identical** normalised ticks;
re-decoding the cached bytes must match the stored ticks (`verify_cached`). If a
re-fetch of an already-cached hour has a *different* hash, that is raised loudly as
`HashChangedError` — history is **never** silently overwritten.

**Secondary cross-check (pluggable, optional).** `secondary_source.py` can compare
the Dukascopy mid against an **OANDA 5s-candle** mid on sampled timestamps, to catch
a systematic scale/instrument/timezone error. It needs an `OANDA_API_TOKEN`. In this
environment the OANDA host is reachable but no token is set, so the cross-check
reports `unavailable` — by design this does **not** fail the GO/NO-GO; we simply say
we could not corroborate rather than pretending we did.

**Coverage runner + frozen GO/NO-GO.** `python shadow_price_runner.py` runs the
lookup over all 28 signal timestamps (plus a sampled set of management-message
timestamps), prints the coverage report (market-open count, P-A/P-B/P-C-D counts,
closed-market, unexplained-missing, median + worst quote gap, spread distribution,
secondary comparison), verifies every touched hour is hashed + reproducible, then
evaluates **GO/NO-GO gates whose thresholds are frozen as constants at the top of the
file** (so the bar cannot be moved after seeing the numbers). It writes the full
machine-readable report to `data/shadow_phase1a_report.json` and exits non-zero on
NO-GO. The eight gates: every hour hashed + reproducible; no silent
interpolation/forward-fill; every normal-session signal returns a valid result or an
explained error; **≥ 90 %** of normal-session signals are P-A/P-B; no unresolved
timezone/decimal/scaling discrepancy; identical re-downloads; no unexplained
secondary divergence; weekends/breaks/holidays correctly identified.

**Acceptance tests:** `python test_price_foundation.py` — 13 deterministic, offline
tests (synthetic `.bi5`, injected sources, no network): before/after tick return, no
interpolation, no forward-fill, closed-vs-missing, anomaly detection, truncated-stream
rejection, hash reproducibility + immutability, instrument/scaling validation,
secondary cross-check (both paths), the T-C "never exact-executable" rule, and the
price-grade thresholds.

**Commands:**

```
python dukascopy_adapter.py 2026-06-25T14   # fetch + decode one hour (smoke test)
python price_cache.py       2026-06-25T14   # cache + verify reproducibility of one hour
python gold_calendar.py     2026-06-25T14:42  # session status for an instant
python quote_lookup.py      2026-06-25T14:42 T-C   # before/after tick + grades
python shadow_price_runner.py               # full coverage report + GO/NO-GO
python test_price_foundation.py             # the 13 acceptance tests
```

*Phase 1b (built — see next section)* consumes these graded quotes to compute the
executable edge.

---

## Shadow mode — Phase 1b: the executable-edge calculation

**What this answers.** For every gold signal it computes THREE ledgers, kept strictly
separate, and then the money question — **edge retention**: how much of the provider's
reported edge survives a realistic, delayed, spread-and-slippage execution.

| Ledger | What it is |
|--------|-----------|
| **A — provider-reported R** | read from the signed-off archive projection; never recomputed |
| **B — independent theoretical R** | advertised entry + original stop/targets replayed on the Phase 1a tick path, NO delay, NO spread, NO slippage — *did the market support the claim?* |
| **C — shadow-executable R** | realistic fill at `posted+delay` on executable bid/ask + adverse slippage |

**Why the historical answer is a RANGE, not a number.** All 28 archived signals are
T-C (posted-time only — Phase 1a). So Phase 1b runs **delay scenarios** (posted +0/+2/
+5/+10/+30 s) crossed with a **slippage sweep** ($0.10/$0.30/$0.60 a side) and labels
every historical result `RECONSTRUCTED_DELAY_SCENARIO`. By the Phase 1a rule, none is
ever "exact executable." Future signals with real receipt timestamps (T-A/T-B) get
`OBSERVED_RECEIPT_TIME`, kept strictly separate.

**Executable-fill discipline.** LONG enters on ASK, exits a target on BID, stop fills
on BID − adverse slippage; SHORT mirrors. Ticks already carry bid AND ask, so spread is
taken from the tick and **never double-counted**; slippage only ever **worsens** a fill.
The fill uses the first valid tick at/after the effective time; if it is further than
the quote-gap limit → `NO_EXECUTABLE_QUOTE` (no guessed fill). NO interpolation, NO
forward-fill. With genuine tick data each tick is a single price, so stop/target
ordering is **unambiguous**; the `PATH_AMBIGUOUS` pessimistic/optimistic bounds are the
primitive for coarse/candle-fallback data.

**Category-honest exits.** `managed_profit_confirmed` / `manual_loss` / `breakeven` and
any **no-target** signal exit at the **management message time** (stop-protected — if
the stop was hit before the managed close, the follower was stopped), never by copying
the provider's stated pips. `profit_confirmed_r_unknown` stays unquantifiable unless the
independent data resolves it, and an unknown is **never** silently converted into a
target hit. Clean `target_hit` / `original_stop_loss` get a chronological replay.

**Edge-leakage metrics.** Reporting gap = provider − theoretical; execution leakage =
theoretical − shadow; total gap = provider − shadow; edge-retention % = shadow ÷
theoretical (only when theoretical expectancy is strictly positive). Expectancy is
reported BOTH conservative (unknowns = 0R over all signals) AND quantified-only
(unknowns excluded from both sides). The **leakage decomposition** attributes the drop
in R to each friction step in a fixed, documented order (reference → bid/ask → receipt
delay → parser → approval → slippage → management).

**No-chase diagnostics (measure, don't enforce).** Signed entry `deterioration_R` and
the TP1 reward-remaining fraction are logged per signal; candidate thresholds
(0.05/0.10/0.15/0.20R adverse) are recorded as **non-decision-making challengers** with
a frozen rule-selection-date + data-cutoff — **no winner is selected on this 28-signal
sample** (that is deferred to prospective testing on NEW signals). A signal a candidate
rule would reject is still replayed in a counterfactual ledger.

**Frozen config + storage.** `shadow_config.py` is the versioned, content-hashed
assumption set (**Shadow Config v0**). Results live in a SEPARATE `data/shadow.db`
(`shadow_configs`, `shadow_runs`, `shadow_results` — one row per signal×scenario —
`shadow_gate_evaluations`), kept apart from the immutable archive so the source of truth
is never at risk; everything is rebuildable from archive evidence + the immutable
Phase 1a price files + the frozen config, and every result row carries its config hash
and price-source hours.

**BTC is deferred.** Phase 1a proved only the gold feed, so the 1 BTC signal is reported
in a separate `DEFERRED` section — it needs its own validated feed before any shadow
calc, by the same "don't build on an unproven source" rule.

**Run + tests:**

```
python shadow_config.py        # print + hash the frozen assumption set
python shadow_run.py           # full three-ledger run + report + persist to shadow.db
python shadow_run.py --no-persist   # report only
python test_shadow.py          # 13 deterministic, offline acceptance tests
```

The headline is always a range across delay×slippage with its coverage grade — by
design. *Deferred to a later phase:* prospective no-chase rule selection on live
(T-A/T-B) signals, and a validated BTC feed.

---

## Files

| File | What it is |
|------|-----------|
| `run.py` | The original flow: log a signal (parse → confirm → size → log). |
| `pipeline.py` | The **connected pipeline**: parse → confirm → **route** → size → log, with a REVIEW safety stop. Logs routing tags too. |
| `outcome.py` | Records how a trade finished (target / stop / breakeven / **missed**) without editing the CSV by hand; also back-logs missed signals. |
| `log_history.py` | Walks the reviewed signals in `history_review.csv` **one at a time** — dedup-checks against `paper_log.csv`, asks NEW/DUPLICATE/SKIP + outcome, and logs only the confirmed ones through the normal engine. Backs up the log first; never auto-logs. |
| `review.py` | Reads the log and reports fill rate, win rate, expectancy, and edge by asset/ticker/trader/session/timeframe. |
| `status.py` | **Read-only dashboard** — whole operation at a glance: mode, risk, breaker headroom, edge, per-trader breakdown, execution status. |
| `chart.py` | **Read-only visual view** — draws a logged paper trade's entry / stop / target levels on a price chart (PNG in `charts/`). No live data, no broker. Needs `matplotlib`. |
| `audit.py` | **The black box** — append-only, permanent record of every pipeline decision (`audit_log.jsonl`), plus a viewer. Never edited by hand. |
| `limits.py` | Tracks daily (2%) and weekly (10%) loss limits and warns when one is hit. |
| `module_a_telegram.py` | The listener (Telegram) — **preview only**, prints caught messages, not connected. Also `--list` (find channel IDs) and `--history N` (read-only back-log of past messages → `history_review.csv`, classified, nothing logged). Exposes `pull_for_archive()` for the archive. |
| `archive.py` | **The permanent archive (Phase 1)** — SQLite (`data/signal_archive.db`) as the source of truth, append-only, CSV export only. Commands: `import`, `rebuild-projections`, `export-csv`, `backup`, `integrity-check`, `archive-status`, `baseline`. PAPER mode, read-only to Telegram. Replaces the shifting 1500-message window with a permanent, growing record. |
| `dukascopy_adapter.py` | **Shadow Phase 1a — the gold tick source.** Fetches one Dukascopy XAU/USD hour over HTTPS (stdlib only), LZMA-decodes the 20-byte records, normalises to exact ticks (points ÷ 1000), and validates instrument/scaling/UTC + per-tick anomalies. Distinguishes TICKS / EMPTY (closed) / MISSING (404). Read-only. |
| `price_cache.py` | **Shadow Phase 1a — the immutable hashed cache.** Stores each hour's raw `.bi5` + SHA-256 + normalised ticks under `data/price_cache/`. Reproduces byte-identical ticks on re-decode; raises `HashChangedError` rather than overwrite a changed hour. |
| `gold_calendar.py` | **Shadow Phase 1a — the session calendar.** Weekend / daily settlement break (seasonal, US-DST rule, no tz-db) / US-holiday-advisory. Tells `MARKET_CLOSED` from `DATA_MISSING`; data presence arbitrates. Pure, no I/O. |
| `quote_lookup.py` | **Shadow Phase 1a — the timestamped quote lookup.** For any UTC instant: the real tick *before* + *after* (bid/ask/gap-ms), market status, a **separate** timestamp grade (T-A/B/C/U) and price grade (P-A/B/C/D/U). No interpolation, no forward-fill; T-C can never be "exact executable". |
| `secondary_source.py` | **Shadow Phase 1a — pluggable secondary cross-check.** OANDA 5s-candle mid vs the primary mid (needs `OANDA_API_TOKEN`); reports `unavailable` honestly when no source is configured. Read-only. |
| `shadow_price_runner.py` | **Shadow Phase 1a — coverage runner + frozen GO/NO-GO.** Runs the lookup over all 28 signal timestamps (+ management sample), prints the coverage report, verifies hash reproducibility, evaluates the frozen gates, writes `data/shadow_phase1a_report.json`. Exits non-zero on NO-GO. |
| `shadow_config.py` | **Shadow Phase 1b — frozen assumption set (Config v0).** Versioned + content-hashed: delay scenarios, slippage sweep, quote-gap limit, no-chase candidate thresholds, leakage-decomposition order, rule-selection-date/data-cutoff. |
| `shadow_db.py` | **Shadow Phase 1b — storage** (separate `data/shadow.db`): `shadow_configs`, `shadow_runs`, `shadow_results` (one row per signal×scenario), `shadow_gate_evaluations`. Append-only; aborts stale runs. Keeps the archive immutable. |
| `shadow_replay.py` | **Shadow Phase 1b — tick-path replay engine.** Executable-fill discipline (ask-in/bid-out, slippage worsens, spread from tick), chronological stop/target resolution, managed (stop-protected) exits, `NO_EXECUTABLE_QUOTE`, and the coarse-data `ambiguity_bounds` primitive. |
| `shadow_inputs.py` | **Shadow Phase 1b — archive reader.** Loads each signal's levels, conservative reference entry, provider R (Ledger A), posted time, re-entry boundary, management time, and whether a validated feed exists. |
| `shadow_ledgers.py` | **Shadow Phase 1b — the three ledgers** (A provider / B theoretical / C executable) with category-honest exit routing. |
| `shadow_nochase.py` | **Shadow Phase 1b — no-chase diagnostics.** Signed deterioration_R, TP1 reward-remaining, logged candidate thresholds (no winner selected), counterfactual. |
| `shadow_run.py` | **Shadow Phase 1b — orchestrator + report.** Runs all gold signals × scenarios, edge-leakage metrics, fixed-order leakage decomposition, coverage/grades (gold/BTC separate), persists to `shadow.db`, evaluates sanity gates, writes `data/shadow_phase1b_report.json`. |
| `backfill_audit.py` / `audit_packages.py` / `gold_clean_report.py` | **Read-only gold validation diagnostics** — frozen flagging of the 296 gold signals, audit packages, and the honest clean-vs-broken aggregate. Advisory; no scoring changes. Artifacts under `data/audit/`. |
| `recover_stops.py` / `recovered_rescore.py` | **LLM stop-recovery (data cleaning).** Re-parses missing-stop gold signals with the configured parser model (`config.PARSER_MODEL`) to recover stops genuinely present in the message (never invented; validated; append-only to a separate `data/parser_revisions.db`), then re-scores via the EXISTING scorer. Reads archived raw text only (no Telegram); archive + signed-off 28 + LIVE stub untouched. |
| `capture_recall_full.py` | **Fuller anti-flattery capture-recall** — blind random days, dumps raw vs DB, hunts missed signals/losses. Surfaced the dropped "market-call" entries. Read-only; dumps in `data/audit/cr_full/`. |
| `coverage_waterfall.py` | **Coverage waterfall** — accounts for every gold candidate record (340) into ONE mutually-exclusive terminal category by priority (dup / re-entry / commentary / garbled / recoverable / no-outcome / quantified=123); arithmetic reconciles exactly. Classifies excluded genuine trades by outcome HINT (loss/win/breakeven/contradictory/no-usable-hint — never calls unknown 'neutral') to detect loss-skew. CSV at `data/audit/coverage_waterfall.csv`. Read-only, no scoring changes. |
| `ctrader_config.py` / `ctrader_auth.py` | **Read-only cTrader Open API connection (Pepperstone DEMO).** OAuth helper (stdlib) to authenticate and cache a token; `CTRADER_EXECUTION_ENABLED=False` hard lock; NO order code. Live protobuf reads are the next stage (after browser auth). Secrets from env, never logged; token gitignored. |
| `recover_market_calls.py` / `marketcall_allin_report.py` | **Market-call recovery + ALL-IN edge.** LLM-recovers the no-entry-price gold "market-call" entries (direction/SL/TP, genuine-only) and prices them at a realistic MARKET fill on real Dukascopy ticks (executable bid/ask + slippage; pip-TPs at $0.10; no-TP→stop within a session horizon, losses included). Reports CLEAN limit-zone edge (+0.28R) vs ALL-IN (+~0.17R) side by side. Scorer unchanged; archive + signed-off 28 + LIVE stub untouched. |
| `module_a_discord.py` | Disabled Discord stub — explains the self-botting ban risk. |
| `config.py` | Settings: pot size, the 1% rule, PAPER/LIVE flag, listener settings, and the **`ASSET_CLASSES`** per-asset-class registry (sizing, specs, slippage). |
| `models.py` | The shared shape of a signal and a ticket. |
| `asset_classes.py` | The **per-asset-class brain**: turns a ticker into an asset class and looks up its spec from `config.ASSET_CLASSES`. Shared by the router and the risk calculator. Metadata only. |
| `signal_quality.py` | The **confidence tagger**: reads the trader's own risk flags in the signal text and tags it HIGH / NORMAL / LOW (cue lists in `config.py`). Metadata only — tags, never blocks. |
| `assess_trader.py` | **Advisory analyst aid** (read-only): assesses a trader's discipline, integrity (claims vs real loss record), sales-creep, and edge trend, with a KEEP/WATCH/REDUCE verdict. Not part of the pipeline; makes no automated decisions. |
| `check_rules.py` | **Advisory rule-adherence tool** (read-only, no API): checks a trader's logged trades against their own stated rules (`traders/<name>_rules.json`) — adherence, whether compliant trades outperform breaking ones, and what the data can't show. |
| `traders/` | Per-trader files for the advisory tools: editable rule configs (`<name>_rules.json`, tracked) and optional raw-message files (`<name>_messages.txt`, git-ignored). See `traders/README.md`. |
| `module_b_parser.py` | Reads a pasted signal into numbers. A **deterministic** parser handles common one-liners incl. entry **ranges** (keeps both zone ends + a conservative primary entry); the LLM is the fallback for anything it can't read. |
| `module_router.py` | Sorts a parsed signal: tags its asset class, trader, and intended venue, and flags unclear ones for review. Metadata only — no execution. |
| `module_c_risk.py` | The risk calculator (the 1% rule lives here) — sizes each asset class via its own strategy (`dollar_per_point` / `pip_value` / `percent_risk`). |
| `module_d_logger.py` | Writes each trade to `paper_log.csv`. |
| `test_multiasset.py` | Tests for the multi-asset engine: forex routing/sizing, gold unchanged, crypto percentage sizing, oil/stocks → REVIEW. Run with `python test_multiasset.py`. |
| `test_signal_quality.py` | Tests for the confidence filter: cue detection, the NORMAL default, the optional skip switch, and the BY CONFIDENCE breakdowns. Run with `python test_signal_quality.py`. |
| `test_parser_zone.py` | Tests for entry-**range** parsing: the real Farouk formats become clean signals, the conservative primary entry is used, and no-stop/management chatter stays REVIEW/commentary. Run with `python test_parser_zone.py`. |
| `test_outcome_cues.py` | Tests for the history puller's **outcome detection**: win/loss/breakeven/missed cues, the "sl to entry ≠ loss" distinction, and conservative matching (no/conflicting cues → unclear). Run with `python test_outcome_cues.py`. |
| `test_log_history.py` | Tests that a back-logged **win is scored at its real STATED R** (tp1 → R to TP1, all-tp → full R, never +1R flat) and that un-derivable cases are marked for manual entry. Run with `python test_log_history.py`. |
| `test_archive.py` | The **eight Phase-1 archive acceptance tests** (idempotent imports, window-slide persistence, later-TP recalculation, re-entry-boundary rejection, override survival, crash rollback, deterministic export). Run with `python test_archive.py`. |
| `module_execution.py` | **Disabled scaffold** for a future broker-execution step. Builds/previews a would-be order but cannot place one (three locks, no engine). |
| `paper_log.csv` | Your growing record of paper trades (created on first run). |
| `data/` | The permanent archive: `signal_archive.db` (SQLite source of truth), `signal_archive_export.csv` (export), `audit_snapshots/` (baseline manifests), `backups/` (timestamped DB copies). Created by `archive.py`. |

---

## Read-only broker connection — cTrader Open API (Pepperstone DEMO)

A **read-only** link to a Pepperstone Europe **DEMO** cTrader account, to *prove we
can authenticate and read* (live gold quote, balance/equity, open positions, contract
spec) — with **no ability to place, modify, or cancel anything**.

**Read-only by construction.** No order placement/modification/cancellation code
exists in this build — the protobuf order messages are never imported or sent — and
`ctrader_config.CTRADER_EXECUTION_ENABLED` is a hard lock (stays `False`), mirroring
the engine's `EXECUTION_ENABLED`. The existing PAPER safeties (`MODE=PAPER`,
`EXECUTION_ENABLED=False`, `LISTENER_MODE=PREVIEW`) and the LIVE stub are untouched.

**Connection route (proven reachable):** OAuth host `https://openapi.ctrader.com`
(HTTP 200) for authorization/token; the live read channel is a **TLS protobuf socket**
at `demo.ctraderapi.com:5035` (TLS 1.3 OK). The Open API is protobuf-over-socket, not
REST — the live reads need `ctrader-open-api` (Twisted + protobuf), added in the next
stage once a token exists.

**Auth — the manual step (only you can do it).** cTrader uses OAuth 2.0
authorization-code; obtaining a token requires a browser login you must perform:
```
# 1) Ensure these are set IN THIS ENVIRONMENT (never hard-coded/logged):
#    CTRADER_CLIENT_ID, CTRADER_CLIENT_SECRET   (+ optional CTRADER_REDIRECT_URI)
python ctrader_auth.py status     # shows config (secrets masked) + what's missing
python ctrader_auth.py url        # prints the authorize URL
#  -> open it, log into your cTrader ID (Pepperstone DEMO), authorize,
#     copy the ?code=... from the redirect
python ctrader_auth.py token <CODE>   # exchanges code -> access+refresh token
python ctrader_auth.py refresh        # later: renew access token (no browser)
```
The token is stored gitignored at `data/ctrader_token.json` (never committed/logged).

**Scope honesty.** cTrader scopes are `accounts` (account list only) and `trading`
(everything else, incl. trading). Reading quotes/balance/positions needs `trading` —
there is **no market-data-only scope** — so the *token* is trade-capable at the API
level; read-only here is enforced **client-side** (no order code + the disabled-
execution lock), not by the scope.

**Status:** auth helper built and verified (URL builder + masked status). The live
protobuf reads (gold bid/ask, balance/equity/free-margin, positions, contract spec)
are the next stage — wired up and verified once you complete the browser authorization
above and a token is cached.

## The execution bridge — a deliberately DISABLED scaffold

`module_execution.py` is the **skeleton** of the piece that would, one distant
day, hand a finished trade to a broker to actually place. It exists so the shape
of that step is mapped out — but it **cannot place an order**, by design.

**Why build a scaffold that does nothing?** So the structure is ready and
reviewed *before* any live capability is bolted on — and so there's one obvious,
clearly-guarded place where execution would live, instead of it being improvised
later. The safest time to design the kill-switches is while the engine is still
unplugged.

**What it can do (safe):** take a fully sized, routed, circuit-breaker-checked
ticket and build a *description* of the order that would be sent
(`prepare_order`), and **print** that description as a dry run (`preview_order`).
Both are pure — they contact nothing and change nothing.

**What it cannot do:** place an order. Three independent locks stand in the way,
all off by default:

1. **`EXECUTION_ENABLED`** in `config.py` is `False`.
2. **`MODE`** must be `"LIVE"` — and it's `"PAPER"`.
3. **There is no broker client at all.** The one function where a real order
   would be sent (`submit_order`) just raises an error where that code would go.

Flipping any *one* of these still places nothing — even flipping the first two,
the third (no engine exists) makes submission impossible. Going live would be a
separate, deliberate, guided step that *replaces* that disconnected chokepoint —
never a casual flag flip.

It also leaves the older LIVE stub in `module_d_logger.py` exactly as it was —
this is a separate, clearer home for the execution step.

**See it work (it refuses):**

```
python module_execution.py
```

It builds a would-be gold order, previews it, shows all three locks BLOCKING, and
then attempts to submit — which is refused. Nothing is sent.

---

## A note on going live

This build is **paper only, on purpose.** There is no live-trading code in it.
Don't change `MODE` in `config.py` to `LIVE` — there's nothing behind it, and the
whole reason this exists is to gather evidence first. When you've reviewed enough
paper data and decided the edge is real, that's the moment to build the live path
carefully — as a separate, deliberate step.
