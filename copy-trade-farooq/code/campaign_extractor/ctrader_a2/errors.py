"""A2 error types. RateLimited429 carries the stage where the 429 occurred."""
from __future__ import annotations


class A2Error(Exception):
    pass


class TokenMissing(A2Error):
    """No cached view-only token — clean stop. A2 does NOT mint or request one."""


class RateLimited429(A2Error):
    def __init__(self, stage=None):
        self.stage = stage
        super().__init__(f"HTTP 429 rate-limited at stage={stage} — stopping immediately, no retry")


class ScopeRejected(A2Error):
    """Returned permission scope is not exactly SCOPE_VIEW."""


class LiveAccountRejected(A2Error):
    """An isLive=true (real-money) account was present/selected — rejected."""


class NoDemoAccount(A2Error):
    """No isLive=false demo account available."""


class LiveTransportNotRun(A2Error):
    """The real Twisted transport is finalised/verified only at the A2 connection step."""


class BrokerError(A2Error):
    """A non-429 broker error response (e.g. invalid token). Carries the non-secret code+stage."""
    def __init__(self, stage=None, code=None):
        self.stage = stage
        self.code = code
        super().__init__(f"broker error at stage={stage} code={code}")
