"""
Brick 3 — secret-field rejection / redaction.

Any record bound for a database, log, report, fixture, or trace that contains a
secret-named field must be REJECTED (default) or deterministically redacted before
persistence. A non-reversible correlation hash is the only credential-derived value
allowed to be stored.
"""
import hashlib

# substrings (normalised) that mark a field as secret material
_SECRET_MARKERS = (
    "client_secret", "access_token", "refresh_token", "authorisation_code",
    "authorization_code", "auth_code", "raw_token_response", "token_response",
    "bearer", "oauth_verifier", "verifier", "password", "secret", "token",
)


class SecretLeak(Exception):
    pass


def is_secret_key(key: str) -> bool:
    k = str(key).lower().replace("-", "_").replace(" ", "_")
    return any(m in k for m in _SECRET_MARKERS)


def safe_record(record: dict, redact: bool = False) -> dict:
    """Return a record safe to persist. By default REJECT (raise) if any secret-named
    field is present; with redact=True, deterministically replace its value."""
    leaks = sorted(k for k in record if is_secret_key(k))
    if leaks:
        if not redact:
            raise SecretLeak(f"secret-named field(s) refused before persistence: {leaks}")
        return {k: ("[REDACTED]" if is_secret_key(k) else v) for k, v in record.items()}
    return dict(record)


def safe_correlation_hash(credential: str) -> str:
    """Irreversible 16-hex correlation id derived from a credential. Cannot reveal it."""
    return hashlib.sha256(("ctrader-ro::" + str(credential)).encode("utf-8")).hexdigest()[:16]
