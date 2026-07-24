# traders/ — per-trader files for the advisory analysis tools

This folder holds two kinds of optional, per-trader files:

- **`<name>_rules.json`** — a trader's stated trading rules, for `check_rules.py`
  (the rule-adherence / rule-profitability tool). `farouk_rules.json` is
  pre-populated as a worked example. Edit the plain-English `statement` of each
  rule freely; the `check` field tells the tool how to look for it in the log
  (use `not_detectable` for anything the data can't show). See the `_help` block
  inside that file for the available checks.
- **`<name>_messages.txt`** — a trader's raw messages, for `assess_trader.py` (the
  advisory trader-assessment analyst). They let the tool analyse a trader's
  *language* — discipline talk, honesty of their claims, and any drift toward
  selling — on top of their logged track record.

## How to use it

Save a trader's raw messages as:

```
traders/<name>_messages.txt
```

where `<name>` is the trader/source name you use in the log, lower-cased — e.g.
`traders/farouk_messages.txt` for `FAROUK`. Then run:

```
python assess_trader.py FAROUK
```

It auto-loads `traders/farouk_messages.txt` if it exists (or pass a path
explicitly with `--messages <file>`). Just paste the messages in — one per line
or in blocks, however you copied them. Dates/tags are optional but help the
analyst spot change over time.

See `example.txt` for the shape (that file is a template and is **not**
auto-loaded).

## Privacy

Real message dumps and generated reports (`*_messages.txt`, `*_assessment*.txt`,
`*_rules_report*.txt`) are **git-ignored** so they never get committed. The
editable rule configs (`<name>_rules.json`), this README, and `example.txt` are
tracked on purpose.

## Reminder

`assess_trader.py` and `check_rules.py` are **advisory judgment aids**, read-only
to `paper_log.csv`. They are not part of the trade pipeline and make no automated
decisions.
