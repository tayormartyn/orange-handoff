"""
VISION V1 — candidate-only screenshot reader (Milestone 2). Fail-closed, layer-isolated.

Vision may PROPOSE what it can visibly read. It must NEVER decide truth, create trades/campaign
events, write accepted campaign state, compute R/expectancy, record provider-displayed profit as
Martyn's result, or infer/repair unclear numbers.

Three strictly separated layers (no code path or DB permission from 1 -> 3):
  1 VISION CANDIDATES        -> data/media_candidates_v1.db
  2 HUMAN-APPROVED MEDIA FACTS -> data/media_reviews_v1.db
  3 ACCEPTED CAMPAIGN EVENTS  -> NOT in this package (firewalled out)
"""
VISION_VERSION = "vision-v1.0"
EXTRACTOR_VERSION = "vision-v1-mock.0"

REGION_TYPES = ("INSTRUMENT_HEADER", "TICKET_1", "TICKET_2", "CHART", "COMMENTARY_TEXT", "OTHER")
FIELD_TYPES = ("INSTRUMENT", "DIRECTION", "ENTRY_PRICE", "EXIT_PRICE", "LOT_SIZE", "STOP_PRICE",
               "TICKET_ID", "PROVIDER_DISPLAYED_PNL", "COMMENTARY_TEXT", "MANAGEMENT_INSTRUCTION")
# high-impact numerics ALWAYS require human confirmation regardless of confidence
HIGH_IMPACT_NUMERIC = ("ENTRY_PRICE", "EXIT_PRICE", "STOP_PRICE", "LOT_SIZE", "PROVIDER_DISPLAYED_PNL")
EVIDENCE_DOMAINS = ("VISIBLE_TRADE_FACT", "PROVIDER_DISPLAYED", "COMMENTARY")
REVIEW_STATUSES = ("PENDING", "AMBIGUOUS_DIGITS", "CONFIRMED", "CORRECTED", "REJECTED",
                   "UNREADABLE", "WRONG_FIELD", "WRONG_INSTRUMENT", "NOT_A_TRADE_FACT")
DUAL_STATES = ("READERS_AGREE", "READERS_DISAGREE", "ONE_READER_ONLY", "UNREADABLE")
SEMANTICS = ("ENTRY_SIGNAL", "POSITION_MANAGEMENT", "POSITION_SNAPSHOT", "ANALYSIS_COMMENTARY",
             "UNKNOWN")
REVIEW_DECISIONS = ("CONFIRM", "CORRECT", "REJECT", "UNREADABLE", "WRONG_FIELD", "WRONG_INSTRUMENT",
                    "NOT_A_TRADE_FACT")
