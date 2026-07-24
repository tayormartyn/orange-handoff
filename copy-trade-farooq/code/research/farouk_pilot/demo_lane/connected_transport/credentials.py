"""Credential PROVIDER interface + a FAKE provider only. NO real token, client id, or secret is
present in source, .env, argv, or logs anywhere in this package. The transport receives credentials
ONLY through a provider object; this build ships exactly one implementation — an in-memory fake for
tests. The real DPAPI-backed provider is a later, separately-reviewed deploy step (the preflight
lane already demonstrates the DPAPI pattern); it is deliberately NOT imported here.
"""
import hashlib


class CredentialProvider:
    """Interface. A provider yields the app + account credentials the auth state machine needs, and
    guarantees they never appear in repr/str/logs. Implementations must NOT read argv/env for the
    secret in a way that could echo it."""
    def app_credentials(self):                       # -> (client_id, client_secret)
        raise NotImplementedError

    def account_access_token(self):                  # -> str
        raise NotImplementedError

    def ctid_trader_account_id(self):                # -> int
        raise NotImplementedError


class FakeCredentialProvider(CredentialProvider):
    """Test-only. Holds obviously-fake values; refuses to render them. IS_FAKE marks it so the
    production composition can assert it is NEVER used on a real path."""
    IS_FAKE = True

    def __init__(self, client_id="FAKE_CLIENT_ID", client_secret="FAKE_CLIENT_SECRET",
                 access_token="FAKE_ACCESS_TOKEN", ctid=None):
        # stored private; no attribute exposes the secret verbatim through repr
        self.__client_id = client_id
        self.__client_secret = client_secret
        self.__access_token = access_token
        self.__ctid = ctid

    def app_credentials(self):
        return (self.__client_id, self.__client_secret)

    def account_access_token(self):
        return self.__access_token

    def ctid_trader_account_id(self):
        return self.__ctid

    def __repr__(self):
        return "<FakeCredentialProvider secrets=REDACTED>"
    __str__ = __repr__


# ---- redaction / sanitisation used by alarms + logs --------------------------------------------
_SECRET_MARKERS = ("token", "secret", "password", "access_token", "client_secret", "authorization")


def redact_secret(value):
    """A secret -> SHA-256 prefix + length only; never the plaintext."""
    s = str(value)
    return f"REDACTED(sha256={hashlib.sha256(s.encode()).hexdigest()[:12]},len={len(s)})"


def sanitise(obj):
    """Deep-copy a dict/list for logging with any secret-looking field redacted. Used by every
    alarm and log line the transport emits — no raw credential can reach a log."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if any(m in str(k).lower() for m in _SECRET_MARKERS):
                out[k] = redact_secret(v)
            else:
                out[k] = sanitise(v)
        return out
    if isinstance(obj, (list, tuple)):
        return [sanitise(v) for v in obj]
    return obj
