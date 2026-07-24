"""Credential handling for the preflight tool. NOTHING is stored in the repo, .env, logs,
or ledgers. Client id/secret are encrypted at rest with Windows DPAPI (CryptProtectData,
CurrentUser scope) via stdlib ctypes — zero third-party dependency — and the blob lives
OUTSIDE the repository tree (%LOCALAPPDATA%\Orange). Account identity in any returned
package is redacted to a SHA-256 hash plus the last four characters only.
"""
import ctypes
import hashlib
import os
from ctypes import wintypes

# DPAPI blob store, deliberately OUTSIDE the repo tree.
_STORE_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Orange")
CRED_BLOB_PATH = os.path.join(_STORE_DIR, "preflight_credentials.dpapi")
CRYPTPROTECT_UI_FORBIDDEN = 0x1


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _to_blob(data):
    buf = ctypes.create_string_buffer(bytes(data), len(data))
    return _DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))


def _from_blob(blob):
    return ctypes.string_at(blob.pbData, blob.cbData)


def dpapi_protect(plaintext, entropy=b"orange-preflight-v0_1"):
    """Encrypt bytes with DPAPI (CurrentUser). Only this Windows user can decrypt."""
    out = _DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(_to_blob(plaintext)), u"orange_preflight", ctypes.byref(_to_blob(entropy)),
        None, None, CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(out))
    if not ok:
        raise OSError("CryptProtectData failed")
    try:
        return _from_blob(out)
    finally:
        ctypes.windll.kernel32.LocalFree(out.pbData)


def dpapi_unprotect(blob, entropy=b"orange-preflight-v0_1"):
    out = _DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(_to_blob(blob)), None, ctypes.byref(_to_blob(entropy)),
        None, None, CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(out))
    if not ok:
        raise OSError("CryptUnprotectData failed")
    try:
        return _from_blob(out)
    finally:
        ctypes.windll.kernel32.LocalFree(out.pbData)


def store_credentials(client_id, client_secret):
    """Encrypt {client_id, client_secret} to the DPAPI blob store outside the repo."""
    os.makedirs(_STORE_DIR, exist_ok=True)
    payload = f"{client_id}\x00{client_secret}".encode("utf-8")
    blob = dpapi_protect(payload)
    with open(CRED_BLOB_PATH, "wb") as f:
        f.write(blob)
    try:
        os.chmod(CRED_BLOB_PATH, 0o600)
    except OSError:
        pass
    return CRED_BLOB_PATH


def load_credentials():
    """Decrypt and return (client_id, client_secret). Never logged. Returns None if absent."""
    if not os.path.exists(CRED_BLOB_PATH):
        return None
    with open(CRED_BLOB_PATH, "rb") as f:
        payload = dpapi_unprotect(f.read()).decode("utf-8")
    cid, _, secret = payload.partition("\x00")
    return cid, secret


def redact_account(account_id):
    """Redact an account identity to SHA-256(hash) + last four chars only."""
    s = str(account_id)
    return {
        "sha256": hashlib.sha256(s.encode("utf-8")).hexdigest(),
        "last4": s[-4:],
        "redacted": True,
    }


def store_is_outside_repo(repo_root):
    """Proof helper: the credential blob path is NOT under the repository tree."""
    return not os.path.abspath(CRED_BLOB_PATH).startswith(os.path.abspath(repo_root) + os.sep)
