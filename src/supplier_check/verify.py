"""Extraction verification node (Phase 4).

Primary gates (in order):
1. Required fields are present.
2. Evidence quotes are exact substrings of the source text.
3. Arithmetic on quantities/prices/totals is consistent.

LLM self-confidence is a weak secondary signal only.
"""

from __future__ import annotations

from typing import Any

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

MONEY_TOL = 0.01


def normalize_text(text: str) -> str:
    return " ".join(text.split())


def evidence_ok(field: Any, raw_text: str, *, field_name: str | None = None) -> bool:
    """A field with a value must carry an evidence quote that is a substring.

    Exception: ``late_penalty_clause_present=False`` may have null evidence,
    because absence of a clause is a valid, rule-relevant finding.
    """
    if field.value is None:
        return field.evidence is None
    if field_name == "late_penalty_clause_present" and field.value is False:
        return field.evidence is None or (
            isinstance(field.evidence, str)
            and normalize_text(field.evidence) in normalize_text(raw_text)
        )
    if not isinstance(field.evidence, str) or not field.evidence.strip():
        return False
    return normalize_text(field.evidence) in normalize_text(raw_text)


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


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
    if _is_number(vat_rate) and _is_number(subtotal) and _is_number(vat_amount) and abs(subtotal * vat_rate / 100 - vat_amount) > MONEY_TOL:
        issues.append(
            f"Numbers do not add up: VAT {vat_rate}% of {subtotal} = "
            f"{subtotal * vat_rate / 100}, but VAT amount is {vat_amount}."
        )
    if _is_number(subtotal) and _is_number(vat_amount) and _is_number(total) and abs(subtotal + vat_amount - total) > MONEY_TOL:
        issues.append(
            f"Numbers do not add up: subtotal ({subtotal}) + VAT ({vat_amount}) = "
            f"{subtotal + vat_amount}, but total is {total}."
        )
    if _is_number(subtotal) and vat_amount is None and _is_number(total) and abs(subtotal - total) > MONEY_TOL:
        issues.append(
            f"Numbers do not add up: subtotal ({subtotal}) != total ({total})."
        )
    return issues


def verify_extraction(state: GraphState) -> GraphState:
    """LangGraph node: verify extraction against primary gates."""
    issues: list[str] = []

    if not state.ingestion_ok:
        state.extraction_status = "needs_human"
        state.extraction_issues = list(state.ingestion_issues) or ["Ingestion failed."]
        return state

    if state.extraction is None:
        state.extraction_status = "needs_human"
        # Keep earlier extract/LLM errors; only add a fallback if nothing was recorded.
        if not state.extraction_issues:
            state.extraction_issues = ["No extraction available to verify."]
        return state

    extraction = state.extraction
    raw_text = state.raw_text

    # 1. Required fields present.
    for name in REQUIRED_FIELDS:
        field = getattr(extraction, name)
        if field.value is None:
            issues.append(f"Required field '{name}' is missing.")

    # 2. Evidence substring check (primary anti-hallucination gate).
    # Required fields with bad evidence fail verification.
    # Optional fields with bad evidence are cleared (never trusted) without failing
    # the whole document — otherwise unused text fields can block Approve.
    for name in QuotationExtraction.model_fields:
        field = getattr(extraction, name)
        if evidence_ok(field, raw_text, field_name=name):
            continue
        if field.value is None and field.evidence is None:
            continue
        if name not in REQUIRED_FIELDS:
            field.value = None
            field.evidence = None
            field.confidence = 0.0
            issues.append(f"Cleared unverified optional field '{name}'.")
            continue
        if field.value is None:
            issues.append(f"Field '{name}' has evidence but no value.")
        elif not isinstance(field.evidence, str) or not field.evidence.strip():
            issues.append(f"Field '{name}' has a value but no supporting evidence.")
        else:
            issues.append(
                f"Field '{name}' evidence is not an exact quote from the document."
            )

    # 3. Arithmetic consistency — recorded for rules, but does not fail extraction.
    # Company rules treat math errors as "Needs a person", not as extract failure.
    math_notes = [f"Note: {msg}" for msg in arithmetic_issues(extraction)]
    issues.extend(math_notes)

    # 4. Weak secondary signal: low confidence (recorded, does not fail on its own).
    for name in QuotationExtraction.model_fields:
        field = getattr(extraction, name)
        if field.value is not None and field.confidence < CONFIDENCE_THRESHOLD:
            # False late-penalty with null evidence is an allowed absence finding.
            if name == "late_penalty_clause_present" and field.value is False:
                continue
            issues.append(
                f"Low confidence ({field.confidence:.2f}) for field '{name}'."
            )

    state.extraction_issues = issues
    # Fails if any primary-gate issue exists. Informational notes do not fail.
    def _is_primary(issue: str) -> bool:
        return not issue.startswith(
            ("Low confidence", "Cleared unverified optional field", "Note:")
        )

    primary_failed = any(_is_primary(i) for i in issues)
    state.extraction_status = "needs_human" if primary_failed else "ok"
    return state