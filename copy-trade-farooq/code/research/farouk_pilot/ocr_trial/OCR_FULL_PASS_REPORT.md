# OQ-10 FULL PASS — FIRST ACCURACY REPORT (2026-07-21)

Stats: {"images": 285, "ocr_errors": 0, "card_images": 52, "rows": 59, "recon_pass": 50, "recon_fail": 0, "leading_digit_suspect": 0, "no_result": 9, "non_card_images": 233}

Reconciliation gate: |dP| x 100 x volume vs displayed result (also catches dropped leading digits). Rows failing reconciliation are NOT trusted.

## Operator verification sample (10 random card images — check rows vs the stored image)
- msg 45736 @ 2026-07-14T15:30:47+00:00 sha f1b6c54b8d7e: [{"side": "buy", "volume_label": 1.0, "result_usd": 2611.25, "entry": 61890.88, "second_price": 64502.13, "reconciliation": "PASS"}]
- msg 44773 @ 2026-06-17T09:26:57+00:00 sha 0de266497ed3: [{"side": "buy", "volume_label": 1.0, "symbol": "XAUUSD-VIP", "result_usd": 1029.0, "entry": 4322.12, "second_price": 4332.41, "reconciliation": "PASS"}]
- msg 45099 @ 2026-06-24T14:53:20+00:00 sha 9440515473b3: [{"side": "sell", "volume_label": 1.0, "symbol": "XAUUSD-VIP", "result_usd": 2154.0, "entry": 4029.76, "second_price": 4008.22, "reconciliation": "PASS"}]
- msg 45816 @ 2026-07-16T15:09:46+00:00 sha ac46317aa4cd: [{"side": "sell", "volume_label": 1.0, "symbol": "XAUUSD-VIP", "result_usd": 1214.0, "entry": 4006.11, "second_price": 3993.97, "reconciliation": "PASS"}]
- msg 45103 @ 2026-06-24T15:21:25+00:00 sha a984be4bcef9: [{"side": "sell", "volume_label": 0.4, "symbol": "XAUUSD-STD", "entry": 4137.61, "second_price": 4130.74, "reconciliation": "NO_RESULT_FIELD"}]
- msg 45885 @ 2026-07-17T12:44:27+00:00 sha 3d9a685ad4c5: [{"side": "sell", "volume_label": 1.0, "symbol": "XAUUSD-VIP", "result_usd": 3055.0, "entry": 3997.52, "second_price": 3966.97, "reconciliation": "PASS"}, {"side": "sell", "volume_label": 1.0, "symbol": "XAUUSD-VIP", "result_usd": 3004.0, "entry": 3997.01, "second_price": 3966.97, "reconciliation": "PASS"}]
- msg 45028 @ 2026-06-23T14:15:36+00:00 sha 9aef2c100720: [{"side": "sell", "volume_label": 1.0, "symbol": "XAUUSD-VIP", "result_usd": 559.0, "entry": 4142.29, "second_price": 4136.7, "reconciliation": "PASS"}]
- msg 45210 @ 2026-06-26T14:35:17+00:00 sha f03786d7ad50: [{"side": "sell", "volume_label": 1.0, "symbol": "XAUUSD-VIP", "result_usd": 1165.0, "entry": 4091.8, "second_price": 4080.15, "reconciliation": "PASS"}]
- msg 44145 @ 2026-06-03T12:02:11+00:00 sha c5469fed9526: [{"side": "sell", "volume_label": 1.0, "symbol": "XAUUSD-VIP", "result_usd": 307.0, "entry": 4463.3, "second_price": 4460.23, "reconciliation": "PASS"}]
- msg 44836 @ 2026-06-18T10:50:15+00:00 sha 3a0014c61448: [{"side": "sell", "volume_label": 1.0, "symbol": "XAUUSD-VIP", "result_usd": 800.0, "entry": 4270.91, "second_price": 4262.91, "reconciliation": "PASS"}]

---
## OPERATOR VERIFICATION (2026-07-21 ~10:20Z)
The 10-image random sample was checked by the operator against the stored card images: ALL extracted rows match. Dataset marked **TRUSTED** for its designated use (mechanical entry-divergence comparison; survivorship-limited; never expectancy). Trust flag: operator_sample_verified.flag.
