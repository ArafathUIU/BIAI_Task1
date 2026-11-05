"""Decision node: combine extraction verification and rule results."""

from __future__ import annotations

from .rules import apply_rules
from .schemas import GraphState


def decide(state: GraphState) -> GraphState:
    """Set the final decision using deterministic precedence.

    Priority:
    1. Cannot inspect document / no extraction / no PR match → Needs
    2. Confirmed hard-rule Reject from verified facts → Reject
    3. Critical extraction uncertainty → Needs
    4. Soft Needs rules / Approve from rule engine
    """
    if not state.ingestion_ok:
        state.decision = "Needs a person to check"
        state.reasons = list(state.ingestion_issues) or [
            "Could not reliably extract or verify the document."
        ]
        state.evidence = []
        state.human_review_required = True
        return state

    if state.extraction is None:
        reasons = ["Could not reliably extract or verify the document."]
        reasons.extend(state.extraction_issues)
        state.decision = "Needs a person to check"
        state.reasons = reasons
        state.evidence = []
        state.human_review_required = True
        return state

    if not state.pr_match_ok or state.pr_row is None:
        reasons = ["No matching purchase-request row for the extracted item code."]
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

    # Confirmed Reject always wins over soft extraction noise.
    if rule_result.decision == "Reject":
        state.decision = "Reject"
        state.reasons = rule_result.reasons
        state.evidence = rule_result.evidence
        state.human_review_required = False
        return state

    if state.extraction_status != "ok":
        reasons = ["Could not reliably extract or verify the document."]
        reasons.extend(state.extraction_issues)
        # Keep soft Needs hits from rules as extra context when present.
        if rule_result.decision == "Needs a person to check":
            for reason in rule_result.reasons:
                if reason not in reasons:
                    reasons.append(reason)
        state.decision = "Needs a person to check"
        state.reasons = reasons
        state.evidence = rule_result.evidence
        state.human_review_required = True
        return state

    state.decision = rule_result.decision
    state.reasons = rule_result.reasons
    state.evidence = rule_result.evidence
    state.human_review_required = state.decision == "Needs a person to check"
    return state
