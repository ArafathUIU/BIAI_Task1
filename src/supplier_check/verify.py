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


def evidence_ok(field: Any, raw_text: str) -> bool:
    """A field with a value must carry an evidence quote that is a substring."""
    if field.value is None:
        return field.evidence is None
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
    for name in QuotationExtraction.model_fields:
        field = getattr(extraction, name)
        if not evidence_ok(field, raw_text):
            if field.value is None and field.evidence is None:
                continue
            if field.value is None:
                issues.append(f"Field '{name}' has evidence but no value.")
            elif field.evidence is None:
                issues.append(f"Field '{name}' has a value but no supporting evidence.")
            else:
                issues.append(
                    f"Field '{name}' evidence is not an exact quote from the document."
                )

    # 3. Arithmetic consistency.
    issues.extend(arithmetic_issues(extraction))

    # 4. Weak secondary signal: low confidence (recorded, does not fail on its own).
    for name in QuotationExtraction.model_fields:
        field = getattr(extraction, name)
        if field.value is not None and field.confidence < CONFIDENCE_THRESHOLD:
            issues.append(
                f"Low confidence ({field.confidence:.2f}) for field '{name}'."
            )

    state.extraction_issues = issues
    # Fails if any primary-gate issue exists (low-confidence notes are allowed
    # to remain as informational when everything else passes).
    primary_failed = any(
        not i.startswith("Low confidence")
        for i in issues
    )
    state.extraction_status = "needs_human" if primary_failed else "ok"
    return state