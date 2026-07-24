"""
ASSOC-1 — offline, deterministic management-message association engine (DECISION-ONLY).

Decides which provider campaign a management-message candidate belongs to. It returns an
association decision and NOTHING else: it never alters a campaign, closes a leg, moves a
stop, records realised R, changes provider performance, creates an order, contacts a broker,
or infers that an instructed action actually occurred.

Fully isolated: its own append-only DB (assoc/data/association_decisions_v1.db), its own
primitives, and NO import of any campaign-mutation repository, reducer, broker, exchange, or
credential path (enforced by a source/dependency scan).
"""
ENGINE_VERSION = "assoc-1.0"
SCHEMA_VERSION = "assoc-1.0"
