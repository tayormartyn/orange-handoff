"""Masking helpers — nothing sensitive is ever rendered in full."""
from __future__ import annotations


def mask_account_id(account_id):
    s = str(account_id)
    return "****" if len(s) <= 4 else ("*" * (len(s) - 4) + s[-4:])


def mask_secret(_value=None):
    return "***MASKED***"
