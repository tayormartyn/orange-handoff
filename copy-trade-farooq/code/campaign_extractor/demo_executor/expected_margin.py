"""
Expected-margin verification from ProtoOAExpectedMarginRes (mocked this phase). A proposal may not be
armed when margin validation is missing, stale or rejected. Records request/response timestamps,
moneyDigits, the BUY/SELL value used and the converted display value.
"""
from __future__ import annotations

MARGIN_STALE_MS = 10_000


def verify(*, get_margin_res, side, request_ts_ms, response_ts_ms=None, now_ms=None,
           source="ProtoOAExpectedMarginRes"):
    """get_margin_res() -> {"buy": raw, "sell": raw, "moneyDigits": n} or None. No secrets involved."""
    res = None
    try:
        res = get_margin_res()
    except Exception as e:                              # noqa: BLE001
        return {"ok": False, "reason": "MARGIN_REQUEST_FAILED", "detail": type(e).__name__, "source": source}
    if not res:
        return {"ok": False, "reason": "MARGIN_MISSING", "source": source}
    money_digits = res.get("moneyDigits", 2)
    raw = res.get("buy") if str(side).upper() == "BUY" else res.get("sell")
    if raw is None:
        return {"ok": False, "reason": "MARGIN_SIDE_MISSING", "source": source}
    resp_ts = response_ts_ms if response_ts_ms is not None else request_ts_ms
    if now_ms is not None and (now_ms - resp_ts) > MARGIN_STALE_MS:
        return {"ok": False, "reason": "MARGIN_STALE", "source": source,
                "request_timestamp_ms": request_ts_ms, "response_timestamp_ms": resp_ts}
    return {"ok": True, "source": source, "request_timestamp_ms": request_ts_ms,
            "response_timestamp_ms": resp_ts, "money_digits": money_digits, "side": str(side).upper(),
            "raw_margin_value": raw, "converted_display_value": round(raw / (10 ** money_digits), 2)}
