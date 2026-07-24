"""connected_transport — OFFLINE cTrader-DEMO connected transport (Chuck-authorised,
TRANSPORT_BUILD_AUTHORISED). Separate package: the executor imports NEITHER this package NOR the
mapper; this package MAY import the approved demo_lane.protobuf_mapper. Nothing here connects to a
live endpoint, requests OAuth, holds a real credential, or flips a gate. See README.md."""
from . import transport_config  # noqa: F401  (re-reads the single-source gates; no redefinition)

TRANSPORT_VERSION = transport_config.TRANSPORT_VERSION
