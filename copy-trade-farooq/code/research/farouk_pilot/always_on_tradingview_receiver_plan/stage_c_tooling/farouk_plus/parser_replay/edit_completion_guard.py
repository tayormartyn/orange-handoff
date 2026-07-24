"""LOOK-AHEAD GUARD for the LIVE_EDIT_COMPLETION_CREATES_NO_CAMPAIGN fix (D-106) - the SAFETY HEART.

An edit that COMPLETES a previously-quarantined message into a valid parseable signal may create a
campaign (with a T=0 freeze at the edit-completion time) ONLY IF the edit is genuinely pre-outcome.

This guard is what prevents a SLOW edit (a message edited into a valid signal AFTER a TP/close/BE
has already been reported) from manufacturing a FAKE-PROSPECTIVE campaign. Without it, the fix is a
backdating hole. Fail-closed: any doubt -> NOT prospective -> the edit stays quarantined/retrospective.

Pure and deterministic: no I/O. The caller supplies the timestamps of any terminal / outcome /
management / orphan-management evidence for the same gold channel (association pre-campaign is
impossible, so the caller passes ALL gold-channel outcome-class evidence in scope - fail-closed
conservatism: one plausibly-related outcome in the window blocks creation).
"""


def edit_completion_is_prospective(*, original_post_ts, edit_completion_ts, outcome_evidence_ts):
    """Return True iff the completing edit is genuinely PRE-outcome.

    original_post_ts     : epoch seconds the original (quarantined) message was posted.
    edit_completion_ts   : epoch seconds the completing edit was received/observed.
    outcome_evidence_ts  : iterable of epoch-second timestamps of outcome/management/terminal
                           evidence (TP/BE/close/take-%/result-card) on the same gold channel.

    Rule (fail-closed): if ANY outcome-class evidence exists in the half-open window
    (original_post_ts, edit_completion_ts], the edit is retrospective -> return False. An outcome
    that lands strictly AFTER the edit completed (F008: edit 14:04:00 < TP1 14:06:18) does NOT block.
    Malformed / non-ordered inputs -> fail closed (False).
    """
    try:
        p = float(original_post_ts)
        e = float(edit_completion_ts)
    except (TypeError, ValueError):
        return False
    if e < p:                       # edit before the post is nonsensical -> fail closed
        return False
    for ts in (outcome_evidence_ts or ()):
        try:
            t = float(ts)
        except (TypeError, ValueError):
            return False            # unparseable outcome ts -> fail closed
        if p < t <= e:              # an outcome arrived after the post, at/before the edit completed
            return False
    return True
