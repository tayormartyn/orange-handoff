# Gate G — Event Frequency Analysis

**Offline, read-only (2026-07-09).** 74 Gate G ANY_ALERT captures over ~11.6 h.

## Firing rate

- **~74 events / 11.6 h ≈ 6.4 events/hour** on average; peaks up to **14/hour**.
- Hourly (UTC): 22h=5, 23h=4, 00h=11, 01h=1, 02h=7, 03h=3, 04h=11, 05h=14, 06h=5, 07h=6, 08h=1, 09h=6.
- **Verdict:** the ANY_ALERT composite is **very high-volume** — one A+ SHORT-window mirror already
  flooded R2 with 74 objects overnight. **Not suitable for continuous mirroring.**

## Which events fired repeatedly (noise)

| Family | Count | % | Read |
|---|---|---|---|
| Engulfing (bull 13 / bear 14) | 27 | 36% | **Noisy context** — fires on many bars; low standalone value |
| A SHORT / A LONG | 24 | 32% | **Noisy** — directional bias prints; context, not a graded call |
| BPR tapped | 8 | 11% | Management/context (a tap, not a formed level) |
| Sweep high / low | 10 | 14% | Liquidity context |
| CHoCH up / down | 5 | 7% | **Structure shift** — lower volume, more meaningful |
| A+ / A+ or better | 0 | 0% | **Trade-quality grade — rare (none in 11.6 h)** |

## Classification for mirroring decisions

- **Context-only (do NOT mirror continuously):** Engulfing, A LONG/SHORT, BPR tapped, and the ANY_ALERT
  composite itself. High volume, low standalone signal → they'd flood R2 and add little.
- **Candidate trade-quality (worth mirroring, low volume):** **A+ / "A+ or better"** (grade trigger —
  rare, high signal; = H1), **CHoCH up/down** (structure shifts), and **BPR formed** (0 seen → very rare,
  high value if it fires).
- **Moderate / optional:** Sweep high/low (liquidity context; ~10/12 h — moderate).

## Implication

- Keep continuous capture to **low-volume, high-signal dedicated alerts** (A+, CHoCH, maybe Sweep/BPR
  formed), each duplicate-first and disable-after-proof (see
  `GATE_H_LOW_VOLUME_ALERT_RECOMMENDATIONS.md`).
- Avoid re-mirroring ANY_ALERT for ongoing capture — use it only for one-shot breadth if ever needed.
