# PASS / FAIL CRITERIA (P1)

The integration verdict stays **NOT_INTEGRATION_READY** unless **all** criteria below PASS, per condition.
Any FAIL keeps that condition (and overall integration) blocked.

## Per-condition criteria
| # | Criterion | PASS | FAIL |
|---|---|---|---|
| C1 | **Reliable timing** | named-condition alert arrives only **at/after bar close** (Once per bar close honoured), delta small & consistent | any intrabar fire, or erratic/large delay |
| C2 | **Identifiable events** | `exact_message` uniquely identifies the condition + direction; safely parseable | ambiguous/empty/garbled payload |
| C3 | **Acceptable duplicates** | each bar's event fires **once** (no intrabar/refresh repeats), or duplicates are deterministic & dedupable by (condition,level,bar_close_time) | non-deterministic duplicates |
| C4 | **Stable post-alert state** | marker/panel/objects **unchanged** at +1 and +5 candles (no repaint/mutation) | REPAINTED / moved / disappeared |
| C5 | **Safely parseable payload** | payload is plain-text or structured but **deterministic & bounded**; no injection/ambiguity | unparseable / unbounded / inconsistent |

## Any alert() function call (extra)
| C6 | **Script-timing characterised** | its timing (bar-close vs intrabar) and payload are **observed and documented**, and it is known whether it **matches a named condition** | behaviour undocumented/unpredictable |

## Grades
| C7 | **Grade stability** | A+/A+++ grade at close does **not** silently change at +1/+5, OR the change rule is characterised | grade flips with no rule |

## Overall gate
- ALL of C1–C5 PASS for a condition → that condition is *eligible* for a future integration proposal (still
  requires separate authorisation; still no QST here).
- Any FAIL, or any UNKNOWN left unresolved → **NOT_INTEGRATION_READY** stands.
- Minimum sample: characterise across **multiple firings per condition** (not a single event) before declaring PASS.
