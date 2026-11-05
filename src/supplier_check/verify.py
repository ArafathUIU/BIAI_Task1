"""Extraction verification node (Phase 4).

Primary gates (in order):
1. Deterministic late-penalty scan overwrites LLM guesses for that field (D20).
2. Required fields are present.
3. Evidence quotes are exact substrings of the source text.
4. Percentage fields (not D20-owned) are reconciled against evidence % tokens (D21).
5. Arithmetic notes are recorded for the rule engine (do not fail extract).

LLM self-confidence is a weak secondary signal only.
"""

from __future__ import annotations

import re
from typing import Any

from .clauses import scan_late_penalty_clause, scan_late_penalty_rate
from .config import CONFIDENCE_THRESHOLD
from .schemas import GraphState, QuotationExtraction

REQUIRED_FIELDS = (
    "supplier_name",
    "item_code",
    "quantity",
    "unit",
    "unit_price",
    "delivery_days",
    "advance_payment_pct",
    "balance_payment_days",
    "validity_days",
    "late_penalty_clause_present",
    "line_amount",
    "subtotal",
    "total",
)

# Percentage-point fields verified against evidence. ``late_penalty_pct_per_week``
# is owned by the D20 scanner and must not be overwritten here.
PERCENT_FIELDS = (
    "advance_payment_pct",
    "vat_rate",
)

MONEY_TOL = 0.01
_PCT_TOKEN = re.compile(r"(?i)(\d+(?:\.\d+)?)\s*%")
_NUM_TOL = 1e-6


def normalize_text(text: str) -> str:
    return " ".join(text.split())


def evidence_ok(field: Any, raw_text: str) -> bool:
    """A field with a value must carry an evidence quote that is a substring."""
    if field.value is None:
        return field.evidence is None
    if not isinstance(field.evidence, str) or not field.evidence.strip():
        return False
    return normalize_text(field.evidence) in normalize_text(raw_text)


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _approx(a: float, b: float) -> bool:
    return abs(float(a) - float(b)) <= max(_NUM_TOL, 1e-9 * max(abs(a), abs(b), 1.0))


def _percentages_in_evidence(evidence: str) -> list[float]:
    return [float(m.group(1)) for m in _PCT_TOKEN.finditer(evidence)]


def _select_evidence_percent(
    field_name: str, evidence: str, pcts: list[float]
) -> float | None:
    """Pick the evidence % that applies to this field, or None if ambiguous."""
    if not pcts:
        return None
    if len(pcts) == 1:
        return pcts[0]

    keyword = {
        "advance_payment_pct": "advance",
        "vat_rate": "vat",
    }.get(field_name)
    if not keyword:
        return None

    hits: list[float] = []
    for match in _PCT_TOKEN.finditer(evidence):
        start = max(0, match.start() - 40)
        end = min(len(evidence), match.end() + 40)
        window = evidence[start:end].lower()
        if keyword in window:
            hits.append(float(match.group(1)))
    if len(hits) == 1:
        return hits[0]
    return None


def reconcile_percent_field(field_name: str, field: Any) -> list[str]:
    """Reconcile a percentage-point field against ``N%`` tokens in its evidence.

    Returns audit/debug notes. Mutates ``field`` in place when normalizing or
    marking UNCERTAIN. Does not invent values when evidence is ambiguous.
    """
    notes: list[str] = []
    if not _is_number(field.value):
        return notes
    if not isinstance(field.evidence, str) or not field.evidence.strip():
        return notes

    value = float(field.value)
    pcts = _percentages_in_evidence(field.evidence)
    if not pcts:
        # Allow explicit zero advance with prose evidence ("No advance ...").
        if _approx(value, 0.0):
            field.status = field.status or "FOUND"
            return notes
        field.status = "UNCERTAIN"
        field.value = None
        notes.append(
            f"Field '{field_name}' value could not be reconciled: evidence has "
            "no percentage token supporting the extracted number."
        )
        return notes

    selected = _select_evidence_percent(field_name, field.evidence, pcts)
    if selected is None:
        field.status = "UNCERTAIN"
        field.value = None
        notes.append(
            f"Field '{field_name}' evidence has multiple percentages and the "
            "relevant rate could not be identified reliably."
        )
        return notes

    # Direct percent-point match (40% → 40, 0.4% → 0.4).
    if _approx(value, selected):
        field.value = selected
        field.status = "FOUND"
        return notes

    # Unambiguous fraction→points: evidence 40% + value 0.4 → 40.
    # Require selected >= 1 so genuine small rates like 0.4% + 0.4 stay as-is
    # (already handled by the direct match above).
    if (
        value > 0.0
        and value <= 1.0
        and selected >= 1.0
        and _approx(value * 100.0, selected)
    ):
        notes.append(
            f"Note: Normalized '{field_name}' from {value} to {selected} "
            f"(evidence states {selected}%; fraction interpreted as percent points)."
        )
        field.value = selected
        field.status = "FOUND"
        return notes

    field.status = "UNCERTAIN"
    field.value = None
    notes.append(
        f"Field '{field_name}' value {value} does not match evidence "
        f"percentage {selected}%."
    )
    return notes


def arithmetic_issues(extraction: QuotationExtraction) -> list[str]:
    issues: list[str] = []
    q = extraction.quantity.value
    p = extraction.unit_price.value
    line = extraction.line_amount.value
    subtotal = extraction.subtotal.value
    vat_rate = extraction.vat_rate.value
    vat_amount = extraction.vat_amount.value
    total = extraction.total.value

    if _is_number(q) and _is_number(p) and _is_number(line) and abs(q * p - line) > MONEY_TOL:
        issues.append(
            f"Numbers do not add up: quantity ({q}) x unit price ({p}) = {q * p}, "
            f"but line amount is {line}."
        )
    if _is_number(line) and _is_number(subtotal) and abs(line - subtotal) > MONEY_TOL:
        issues.append(
            f"Numbers do not add up: line amount ({line}) != subtotal ({subtotal})."
        )
    if (
        _is_number(vat_rate)
        and _is_number(subtotal)
        and _is_number(vat_amount)
        and abs(subtotal * vat_rate / 100 - vat_amount) > MONEY_TOL
    ):
        issues.append(
            f"Numbers do not add up: VAT {vat_rate}% of {subtotal} = "
            f"{subtotal * vat_rate / 100}, but VAT amount is {vat_amount}."
        )
    if (
        _is_number(subtotal)
        and _is_number(vat_amount)
        and _is_number(total)
        and abs(subtotal + vat_amount - total) > MONEY_TOL
    ):
        issues.append(
            f"Numbers do not add up: subtotal ({subtotal}) + VAT ({vat_amount}) = "
            f"{subtotal + vat_amount}, but total is {total}."
        )
    if (
        _is_number(subtotal)
        and vat_amount is None
        and _is_number(total)
        and abs(subtotal - total) > MONEY_TOL
    ):
        issues.append(
            f"Numbers do not add up: subtotal ({subtotal}) != total ({total})."
        )
    return issues


def apply_late_penalty_scan(extraction: QuotationExtraction, raw_text: str) -> None:
    """Overwrite LLM late-penalty guess with a deterministic scan."""
    scanned = scan_late_penalty_clause(raw_text)
    extraction.late_penalty_clause_present = scanned
    extraction.late_penalty_pct_per_week = scan_late_penalty_rate(raw_text, scanned)


def verify_extraction(state: GraphState) -> GraphState:
    """LangGraph node: verify extraction against primary gates."""
    issues: list[str] = []

    if not state.ingestion_ok:
        state.extraction_status = "needs_human"
        state.extraction_issues = list(state.ingestion_issues) or ["Ingestion failed."]
        return state

    if state.extraction is None:
        state.extraction_status = "needs_human"
        if not state.extraction_issues:
            state.extraction_issues = ["No extraction available to verify."]
        return state

    extraction = state.extraction
    raw_text = state.raw_text

    # Deterministic late-penalty classification (never trust bare LLM false).
    apply_late_penalty_scan(extraction, raw_text)
    lp = extraction.late_penalty_clause_present
    if lp.status == "UNCERTAIN":
        issues.append(
            "Late-delivery penalty clause could not be verified "
            "(contract section not reliably inspectable)."
        )
    elif lp.status == "NOT_FOUND":
        issues.append("Note: Late-delivery penalty clause not found after inspecting T&C.")
    elif lp.status == "FOUND":
        issues.append("Note: Late-delivery penalty clause found with supporting evidence.")

    # 1. Required fields present (late_penalty may be False with NOT_FOUND — that is present).
    for name in REQUIRED_FIELDS:
        field = getattr(extraction, name)
        if name == "late_penalty_clause_present":
            if field.status == "UNCERTAIN" or (
                field.value is None and field.status != "NOT_FOUND"
            ):
                issues.append(
                    "Required field 'late_penalty_clause_present' is UNCERTAIN."
                )
            continue
        if field.value is None:
            issues.append(f"Required field '{name}' is missing.")

    # 2. Evidence substring check.
    for name in QuotationExtraction.model_fields:
        field = getattr(extraction, name)
        if name in {"late_penalty_clause_present", "late_penalty_pct_per_week"}:
            # Owned by the D20 deterministic scanner; do not re-verify here.
            continue
        if evidence_ok(field, raw_text):
            if field.value is not None and field.evidence:
                field.status = field.status or "FOUND"
                if field.confidence is None:
                    field.confidence = 0.9
            continue
        if field.value is None and field.evidence is None:
            if field.status is None:
                field.status = "NOT_FOUND" if name in {"tin", "bin"} else field.status
            continue
        if name not in REQUIRED_FIELDS:
            field.value = None
            field.evidence = None
            field.confidence = None
            field.status = "UNCERTAIN"
            issues.append(f"Cleared unverified optional field '{name}'.")
            continue
        field.status = "UNCERTAIN"
        if field.value is None:
            issues.append(f"Field '{name}' has evidence but no value.")
        elif not isinstance(field.evidence, str) or not field.evidence.strip():
            issues.append(f"Field '{name}' has a value but no supporting evidence.")
        else:
            issues.append(
                f"Field '{name}' evidence is not an exact quote from the document."
            )

    # 2b. Percentage value <-> evidence reconciliation (D21). Skip D20-owned fields.
    for name in PERCENT_FIELDS:
        field = getattr(extraction, name)
        if field.value is None:
            continue
        if not evidence_ok(field, raw_text):
            # Substring failure already recorded above.
            continue
        issues.extend(reconcile_percent_field(name, field))
        if field.status == "UNCERTAIN" and name in REQUIRED_FIELDS and field.value is None:
            issues.append(f"Required field '{name}' is UNCERTAIN after percent reconciliation.")

    # 3. Arithmetic notes for the rule engine.
    math_notes = [f"Note: {msg}" for msg in arithmetic_issues(extraction)]
    issues.extend(math_notes)

    # 4. Low confidence notes (never alone a hard fail).
    threshold = CONFIDENCE_THRESHOLD
    for name in QuotationExtraction.model_fields:
        field = getattr(extraction, name)
        if field.value is not None and field.confidence is not None and field.confidence < threshold:
            issues.append(
                f"Low confidence ({field.confidence:.2f}) for field '{name}'."
            )

    state.extraction_issues = issues

    def _is_primary(issue: str) -> bool:
        return not issue.startswith(
            ("Low confidence", "Cleared unverified optional field", "Note:")
        )

    primary_failed = any(_is_primary(i) for i in issues)
    state.extraction_status = "needs_human" if primary_failed else "ok"
    return state
