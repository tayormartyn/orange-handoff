"""Credentials + token for the preflight. NOTHING is stored in the repo, .env, args, history,
stdout, stderr, reports, or ledgers. Client id/secret AND the OAuth access/refresh token are
read from / written to Windows DPAPI (CryptProtectData/CryptUnprotectData, CurrentUser) via
stdlib ctypes (zero third-party dependency); the encrypted blobs live OUTSIDE the repository tree
(%LOCALAPPDATA%\\Orange). No unattended refresh service exists here. Account identity in any
returned/printed value is redacted to a SHA-256 hash plus the last four chars; the token is
redacted to scope + expiry + last four chars of the access token only.
"""
import ctypes
import hashlib
import json
import os
from ctypes import wintypes

_ENV_DIR = "ORANGE_PREFLIGHT_STORE_DIR"    # test/override hook; default %LOCALAPPDATA%\Orange
CRYPTPROTECT_UI_FORBIDDEN = 0x1
_ENTROPY = b"orange-ctrader-preflight-v0_1"
_TOKEN_ENTROPY = b"orange-ctrader-preflight-token-v0_1"


def _store_dir():
    return os.environ.get(_ENV_DIR) or os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Orange")


def cred_blob_path():
    return os.path.join(_store_dir(), "ctrader_preflight_credentials.dpapi")


def token_blob_path():
    return os.path.join(_store_dir(), "ctrader_preflight_token.dpapi")


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _to_blob(data):
    buf = ctypes.create_string_buffer(bytes(data), len(data))
    return _DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))


def _from_blob(blob):
    return ctypes.string_at(blob.pbData, blob.cbData)


def dpapi_protect(plaintext, entropy=_ENTROPY):
    out = _DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(_to_blob(plaintext)), u"orange_ctrader_preflight",
        ctypes.byref(_to_blob(entropy)), None, None, CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(out))
    if not ok:
        raise OSError("CryptProtectData failed")
    try:
        return _from_blob(out)
    finally:
        ctypes.windll.kernel32.LocalFree(out.pbData)


def dpapi_unprotect(blob, entropy=_ENTROPY):
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
    """Operator-run once: encrypt {client_id, client_secret} to the DPAPI blob OUTSIDE the repo."""
    os.makedirs(_store_dir(), exist_ok=True)
    blob = dpapi_protect(f"{client_id}\x00{client_secret}".encode("utf-8"))
    path = cred_blob_path()
    with open(path, "wb") as f:
        f.write(blob)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path


def load_credentials():
    """Return (client_id, client_secret) or None. NEVER logged/printed. Phase-2 only."""
    path = cred_blob_path()
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        payload = dpapi_unprotect(f.read()).decode("utf-8")
    cid, _, secret = payload.partition("\x00")
    return cid, secret


def store_token(token):
    """Phase-2: encrypt the OAuth token dict to a DPAPI blob OUTSIDE the repo. NEVER logged."""
    os.makedirs(_store_dir(), exist_ok=True)
    blob = dpapi_protect(json.dumps(token).encode("utf-8"), entropy=_TOKEN_ENTROPY)
    path = token_blob_path()
    with open(path, "wb") as f:
        f.write(blob)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path


def load_token():
    """Return the token dict or None. NEVER logged/printed in full. Phase-2 only."""
    path = token_blob_path()
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return json.loads(dpapi_unprotect(f.read(), entropy=_TOKEN_ENTROPY).decode("utf-8"))


def redact_token(token):
    """The ONLY representation of a token safe to return/print: scope + expiry + last4 of the
    access token. The access/refresh token values themselves are NEVER included."""
    at = str(token.get("accessToken") or token.get("access_token") or "")
    return {"granted_scope": token.get("scope") or token.get("tokenType"),
            "expires_in": token.get("expiresIn") or token.get("expires_in"),
            "access_token_last4": at[-4:] if at else None,
            "redacted": True}


def redact_account(account_id):
    """Redact an account identity to SHA-256(hash) + last four chars only."""
    s = str(account_id)
    return {"sha256": hashlib.sha256(s.encode("utf-8")).hexdigest(), "last4": s[-4:], "redacted": True}


def store_is_outside_repo(repo_root):
    return not os.path.abspath(_store_dir()).startswith(os.path.abspath(repo_root) + os.sep)
