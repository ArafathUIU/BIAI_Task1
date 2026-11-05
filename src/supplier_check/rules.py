"""Deterministic rule engine for supplier documents.

All decisions (Approve / Reject / Needs a person to check) come from here.
The LLM is never consulted for a decision.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from .schemas import RuleResult


def _num(v: Any) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, Decimal):
        return float(v)
    return None


def _field(extraction: Any, name: str) -> Any:
    return getattr(extraction, name)


def _ev(extraction: Any, name: str) -> str | None:
    f = getattr(extraction, name)
    return f.evidence if isinstance(f.evidence, str) and f.evidence.strip() else None


def _payment_days(extraction: Any) -> int | None:
    v = _field(extraction, "balance_payment_days").value
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return int(v)
    if isinstance(v, str):
        try:
            return int(v.strip())
        except ValueError:
            return None
    return None


def _tin_missing(extraction: Any) -> bool:
    v = _field(extraction, "tin").value
    return v is None or (isinstance(v, str) and not v.strip())


def _bin_missing(extraction: Any) -> bool:
    v = _field(extraction, "bin").value
    return v is None or (isinstance(v, str) and not v.strip())


def _vat_shown_separately_at_15(extraction: Any) -> bool:
    rate = _field(extraction, "vat_rate").value
    amount = _field(extraction, "vat_amount").value
    return rate == 15 and amount is not None


def _numbers_add_up(extraction: Any) -> bool:
    from .verify import arithmetic_issues

    return len(arithmetic_issues(extraction)) == 0


def _late_penalty_state(extraction: Any) -> str:
    """Return present | absent | uncertain for the late-penalty clause."""
    field = _field(extraction, "late_penalty_clause_present")
    status = getattr(field, "status", None)
    if status == "FOUND" or field.value is True:
        return "present"
    if status == "NOT_FOUND" or field.value is False:
        return "absent"
    return "uncertain"


def apply_rules(extraction: Any, pr_row: dict[str, Any], price_over_max: float | None) -> RuleResult:
    """Apply company rules. Returns a RuleResult with decision + reasons + evidence."""
    if price_over_max is not None:
        price_over_max = round(price_over_max, 9)
    result = RuleResult()
    reject_reasons: list[str] = []
    reject_evidence: list[str] = []
    reject_hits: list[str] = []
    needs_reasons: list[str] = []
    needs_evidence: list[str] = []
    needs_hits: list[str] = []

    def reject(reason: str, hit: str, ev: str | None = None) -> None:
        reject_reasons.append(reason)
        reject_hits.append(hit)
        if ev:
            reject_evidence.append(ev)

    def needs(reason: str, hit: str, ev: str | None = None) -> None:
        needs_reasons.append(reason)
        needs_hits.append(hit)
        if ev:
            needs_evidence.append(ev)

    # --- Reject rules ---
    if price_over_max is not None and price_over_max > 3.0:
        reject(
            "Unit price is more than 3% above the maximum unit price in the purchase request.",
            "reject_price_over_3pct",
            _ev(extraction, "unit_price"),
        )
    advance = _num(_field(extraction, "advance_payment_pct").value)
    if advance is not None and advance > 20.0:
        reject(
            "Advance payment is more than 20%.",
            "reject_advance_over_20pct",
            _ev(extraction, "advance_payment_pct"),
        )
    late_penalty = _late_penalty_state(extraction)
    if late_penalty == "absent":
        reject(
            "The contract has no late-delivery penalty clause.",
            "reject_no_late_penalty_clause",
            _ev(extraction, "late_penalty_clause_present")
            or _ev(extraction, "payment_terms_text"),
        )
    if _tin_missing(extraction) or _bin_missing(extraction):
        reject(
            "The supplier's TIN or BIN is missing.",
            "reject_tin_bin_missing",
            _ev(extraction, "tin") or _ev(extraction, "bin") or _ev(extraction, "payment_terms_text"),
        )
    delivery = _field(extraction, "delivery_days").value
    delivery_n = _num(delivery)
    if delivery_n is not None and delivery_n > 45:
        reject(
            "Delivery is promised later than 45 days after the purchase order.",
            "reject_delivery_over_45_days",
            _ev(extraction, "delivery_days"),
        )

    # --- Needs rules (evaluated even on Reject, so audit can record extra hits) ---
    if late_penalty == "uncertain":
        needs(
            "Late-delivery penalty clause could not be verified from the document.",
            "needs_late_penalty_uncertain",
            _ev(extraction, "late_penalty_clause_present"),
        )
    if price_over_max is not None and 0 < price_over_max <= 3.0:
        needs(
            "Unit price is above the maximum, but by no more than 3%.",
            "needs_price_up_to_3pct",
            _ev(extraction, "unit_price"),
        )
    requested_qty = pr_row["quantity_requested"]
    qty = _field(extraction, "quantity").value
    if isinstance(qty, (int, float)) and not isinstance(qty, bool) and requested_qty:
        qty_diff = abs((qty - requested_qty) / requested_qty * 100)
        if qty_diff > 5.0:
            needs(
                "Quantity differs from the quantity requested by more than 5%.",
                "needs_qty_diff_over_5pct",
                _ev(extraction, "quantity"),
            )
    if _payment_days(extraction) is None or not (30 <= (_payment_days(extraction) or 0) <= 60):
        # Distinguish missing vs out-of-range; both are "unclear or outside".
        needs(
            "Payment terms are unclear, or outside 30 to 60 days after delivery.",
            "needs_payment_terms",
            _ev(extraction, "balance_payment_days") or _ev(extraction, "payment_terms_text"),
        )
    if delivery_n is None:
        needs(
            "Delivery days could not be determined from the document.",
            "needs_delivery_unknown",
            _ev(extraction, "delivery_days"),
        )
    elif 31 <= delivery_n <= 45:
        needs(
            "Delivery is promised in 31 to 45 days.",
            "needs_delivery_31_45_days",
            _ev(extraction, "delivery_days"),
        )
    if not _vat_shown_separately_at_15(extraction):
        needs(
            "VAT is not shown separately at 15%.",
            "needs_vat_not_separate_15",
            _ev(extraction, "vat_rate") or _ev(extraction, "total"),
        )
    if not _numbers_add_up(extraction):
        needs(
            "The numbers do not add up (line total, subtotal, VAT or total is wrong).",
            "needs_numbers_dont_add_up",
            _ev(extraction, "line_amount") or _ev(extraction, "subtotal"),
        )
    validity = _field(extraction, "validity_days").value
    validity_n = _num(validity)
    if validity_n is not None and validity_n < 30:
        needs(
            "The quotation is valid for less than 30 days.",
            "needs_validity_under_30_days",
            _ev(extraction, "validity_days"),
        )
    penalty = _num(_field(extraction, "late_penalty_pct_per_week").value)
    if penalty is not None and penalty < 0.5:
        needs(
            "Late-delivery penalty is below 0.5% of order value per week.",
            "needs_penalty_under_0_5pct",
            _ev(extraction, "late_penalty_pct_per_week"),
        )

    if reject_reasons:
        result.decision = "Reject"
        result.reasons = reject_reasons
        result.evidence = reject_evidence
        result.rule_hits = reject_hits + [h for h in needs_hits if h not in reject_hits]
        return result

    if needs_reasons:
        result.decision = "Needs a person to check"
        result.reasons = needs_reasons
        result.evidence = needs_evidence
        result.rule_hits = needs_hits
        return result

    result.decision = "Approve"
    result.reasons = ["All company rules pass."]
    result.evidence = []
    result.rule_hits = ["approve_all_rules_pass"]
    return result
