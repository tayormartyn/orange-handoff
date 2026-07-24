"""
H1 — secret-field rejection before persistence/logging.

Any record bound for the observation DB, a log, a fixture, or a trace that contains a
secret/signing-named field is REJECTED by default (or deterministically redacted). No
credential-derived value other than a non-reversible correlation hash may ever be stored.
Because H1 loads no key, this is defence-in-depth: it guarantees that even a mistaken
record cannot carry key material into the store.
"""
import hashlib

_SECRET_MARKERS = (
    "private_key", "privatekey", "secret_key", "secretkey", "signing_key", "signer_key",
    "agent_key", "wallet_key", "api_secret", "client_secret", "access_token",
    "refresh_token", "bearer", "seed_phrase", "seedphrase", "mnemonic", "keystore",
    "signature", "secret", "password", "token", "seed", "privkey",
)


class SecretLeak(Exception):
    pass


def is_secret_key(key: str) -> bool:
    k = str(key).lower().replace("-", "_").replace(" ", "_")
    return any(m in k for m in _SECRET_MARKERS)


def safe_record(record: dict, redact: bool = False) -> dict:
    """Reject (default) or deterministically redact any secret-named field before persistence."""
    leaks = sorted(k for k in record if is_secret_key(k))
    if leaks:
        if not redact:
            raise SecretLeak(f"secret-named field(s) refused before persistence: {leaks}")
        return {k: ("[REDACTED]" if is_secret_key(k) else v) for k, v in record.items()}
    return dict(record)


def safe_correlation_hash(value: str) -> str:
    """Irreversible 16-hex correlation id. Cannot reveal its input."""
    return hashlib.sha256(("hl-obs::" + str(value)).encode("utf-8")).hexdigest()[:16]
