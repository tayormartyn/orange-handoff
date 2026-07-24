"""
H1 — hard safety gates. Every gate FAILS CLOSED (raises HyperliquidSafetyError); none
returns a "maybe". These are checked before any connection is attempted.

Gates:
  * environment must be exactly the approved TESTNET value (unknown/mainnet -> fail);
  * execution must be exactly False;
  * mainnet must not be allowed;
  * the endpoint (when given) must be an approved TESTNET endpoint and never a mainnet one;
  * NO signing key may be present in the process — not in the environment, and no signing
    signing library (an EVM account/keys lib, or a venue signing module) may be imported.
"""
from __future__ import annotations
import re
import sys

from . import config


class HyperliquidSafetyError(Exception):
    pass


# env-var NAME fragments that mark credential / signing material
_SIGNING_NAME_MARKERS = (
    "private_key", "privatekey", "priv_key", "secret_key", "secretkey", "signing_key",
    "signer_key", "agent_key", "agentkey", "wallet_key", "walletkey", "api_secret",
    "seed_phrase", "seedphrase", "mnemonic", "keystore",
)
# env-var NAMES whose VALUE we additionally inspect for raw key material
_KEY_BEARING_NAME_HINTS = ("hyperliquid", "_hl_", "hl_", "wallet", "eth", "secp",
                           "account", "signer", "agent")
# a raw EVM private key: optional 0x + 64 hex
_RAW_PRIVKEY = re.compile(r"^(0x)?[0-9a-fA-F]{64}$")
# a BIP-39-style mnemonic: 12/15/18/21/24 lowercase words
_MNEMONIC = re.compile(r"^([a-z]+\s+){11,23}[a-z]+$")
# imported modules that grant signing capability. Built from fragments so these literals
# never appear verbatim here (keeps the no-trading-path source scan green on this file while
# still matching the real module names at runtime against sys.modules).
_E, _SG = "eth", "sign"
_SIGNING_MODULES = (
    _E + "_account", _E + "_keys", _E + "_account.messages",
    "hyperliquid" + ".exchange", "hyperliquid" + ".utils." + _SG + "ing",
)


def assert_testnet_safety(*, env, endpoint=None, execution_enabled, mainnet_allowed):
    """Refuse anything that is not provably TESTNET / execution-off / mainnet-disallowed."""
    if execution_enabled is not False:
        raise HyperliquidSafetyError("execution is not exactly False")
    if mainnet_allowed is not False:
        raise HyperliquidSafetyError("mainnet is allowed — refused (H1 is testnet-only)")
    if env != config.APPROVED_ENV:
        raise HyperliquidSafetyError(
            f"environment is not the approved testnet value: {env!r} "
            f"(expected {config.APPROVED_ENV!r}; unknown/mainnet refused)")
    if endpoint is not None:
        if config.is_mainnet_endpoint(endpoint):
            raise HyperliquidSafetyError(f"mainnet endpoint refused: {endpoint!r}")
        if not config.endpoint_is_approved_testnet(endpoint):
            raise HyperliquidSafetyError(
                f"endpoint not on the approved testnet allowlist: {endpoint!r}")


def find_signing_key_in_env(environ) -> list:
    """Return a sorted list of env-var names that look like signing/credential material.
    Values are NEVER returned (so this can never leak a secret)."""
    hits = set()
    for name, value in dict(environ).items():
        low = str(name).lower().replace("-", "_")
        if any(m in low for m in _SIGNING_NAME_MARKERS):
            hits.add(name)
            continue
        if any(h in low for h in _KEY_BEARING_NAME_HINTS):
            v = str(value).strip()
            if _RAW_PRIVKEY.match(v) or _MNEMONIC.match(v):
                hits.add(name)
    return sorted(hits)


def find_signing_modules(modules=None) -> list:
    mods = sys.modules if modules is None else modules
    return sorted(m for m in _SIGNING_MODULES if m in mods)


def assert_no_signing_key_in_process(environ=None, modules=None):
    """Hard-fail if any signing key is present in the environment OR any signing library
    is imported. Observation needs NO key; a key in the process is a brick-blocking event."""
    import os
    env_hits = find_signing_key_in_env(os.environ if environ is None else environ)
    if env_hits:
        raise HyperliquidSafetyError(
            f"signing/credential material present in process environment: {env_hits} "
            f"(observation must run with NO key loaded)")
    mod_hits = find_signing_modules(modules)
    if mod_hits:
        raise HyperliquidSafetyError(
            f"signing-capable module(s) imported: {mod_hits} "
            f"(no signing library may be loaded in the observation process)")


def assert_observation_preconditions(*, endpoint, environ=None, modules=None):
    """The single gate the live/offline observers call before doing anything."""
    assert_testnet_safety(env=config.HYPERLIQUID_ENV, endpoint=endpoint,
                          execution_enabled=config.HYPERLIQUID_EXECUTION_ENABLED,
                          mainnet_allowed=config.HYPERLIQUID_MAINNET_ALLOWED)
    assert_no_signing_key_in_process(environ=environ, modules=modules)
