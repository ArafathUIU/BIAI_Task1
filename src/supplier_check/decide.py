"""Decision node: combine extraction verification and rule results."""

from __future__ import annotations

from .rules import apply_rules
from .schemas import GraphState


def decide(state: GraphState) -> GraphState:
    """Set the final decision using deterministic precedence."""
    if (
        state.extraction_status != "ok"
        or not state.pr_match_ok
        or state.extraction is None
        or state.pr_row is None
    ):
        reasons = ["Could not reliably extract or verify the document."]
        if not state.pr_match_ok:
            reasons.append("No matching purchase-request row for the extracted item code.")
        reasons.extend(state.extraction_issues)
        state.decision = "Needs a person to check"
        state.reasons = reasons
        state.evidence = []
        state.human_review_required = True
        return state

    rule_result = apply_rules(
        state.extraction, state.pr_row, state.price_over_max_pct
    )
    state.rule_result = rule_result
    state.decision = rule_result.decision
    state.reasons = rule_result.reasons
    state.evidence = rule_result.evidence
    state.human_review_required = state.decision == "Needs a person to check"
    return state
