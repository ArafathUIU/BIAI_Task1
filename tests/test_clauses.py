from pathlib import Path

from supplier_check.clauses import (
    extract_weekly_penalty_pct,
    normalize_text,
    scan_late_penalty_clause,
    scan_late_penalty_rate,
)
from supplier_check.ingest import ingest_pdf

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _tc(body: str) -> str:
    return "Supplier X\nQUOTATION\nTERMS AND CONDITIONS\n" + body


def test_late_penalty_verified_true_on_pack_01() -> None:
    state = ingest_pdf(DATA_DIR / "supplier-pack-01.pdf")
    field = scan_late_penalty_clause(state.raw_text)
    assert field.status == "FOUND"
    assert field.value is True
    assert field.evidence
    assert field.evidence in state.raw_text or normalize_text(field.evidence) in normalize_text(
        state.raw_text
    )
    assert "penalty" in field.evidence.lower()
    assert field.confidence is not None and field.confidence >= 0.9
    rate = scan_late_penalty_rate(state.raw_text, field)
    assert rate.status == "FOUND"
    assert rate.value == 1.0


def test_pack_02_shall_pay_075_found_with_rate() -> None:
    """Regression: equivalent wording without the word 'penalty' + decimal rate."""
    state = ingest_pdf(DATA_DIR / "supplier-pack-02.pdf")
    field = scan_late_penalty_clause(state.raw_text)
    assert field.status == "FOUND"
    assert field.value is True
    assert field.evidence is not None
    assert field.evidence in state.raw_text or normalize_text(field.evidence) in normalize_text(
        state.raw_text
    )
    assert "shall pay" in field.evidence.lower()
    assert "0.75%" in field.evidence
    rate = scan_late_penalty_rate(state.raw_text, field)
    assert rate.status == "FOUND"
    assert rate.value == 0.75
    assert extract_weekly_penalty_pct(field.evidence) == 0.75


def test_conventional_half_percent_penalty_per_week_found() -> None:
    text = _tc(
        "1. Payment. Net 30.\n"
        "2. Delay. Late delivery penalty of 0.5% of order value per week.\n"
        "3. Validity. 30 days.\n"
    )
    field = scan_late_penalty_clause(text)
    assert field.status == "FOUND"
    assert field.value is True
    assert field.evidence is not None
    assert "0.5%" in field.evidence
    assert extract_weekly_penalty_pct(field.evidence) == 0.5


def test_weekly_delay_deduction_125_found() -> None:
    text = _tc(
        "1. Payment. Net 45.\n"
        "2. A deduction of 1.25% of the order value per week of delay applies "
        "for delayed delivery.\n"
        "3. Validity. 40 days.\n"
    )
    field = scan_late_penalty_clause(text)
    assert field.status == "FOUND"
    assert field.value is True
    assert field.evidence is not None
    assert extract_weekly_penalty_pct(field.evidence) == 1.25


def test_complete_tc_without_qualifying_clause_is_not_found() -> None:
    text = _tc(
        "1. Payment. 10% advance payable with the purchase order. "
        "Balance within 60 days of delivery.\n"
        "2. Delivery. Delivery within 27 days of PO.\n"
        "3. Validity. This quotation is valid for 30 days from the date above.\n"
        "4. Quality. Goods as per approved sample.\n"
    )
    field = scan_late_penalty_clause(text)
    assert field.status == "NOT_FOUND"
    assert field.value is False
    assert field.evidence is not None
    assert "terms and conditions" in field.evidence.lower()
    # Must not use an unrelated Payment/VAT opening blob as "proof".
    assert "10% advance" not in field.evidence
    assert "VAT" not in field.evidence


def test_late_penalty_verified_false_on_pack_06() -> None:
    state = ingest_pdf(DATA_DIR / "supplier-pack-06.pdf")
    field = scan_late_penalty_clause(state.raw_text)
    assert field.status == "NOT_FOUND"
    assert field.value is False
    assert field.evidence is not None
    assert "terms and conditions" in field.evidence.lower()
    assert field.confidence is not None and field.confidence < 1.0
    rate = scan_late_penalty_rate(state.raw_text, field)
    assert rate.status == "NOT_FOUND"
    assert rate.value is None


def test_late_penalty_uncertain_when_text_uninspectable() -> None:
    field = scan_late_penalty_clause("")
    assert field.status == "UNCERTAIN"
    assert field.value is None
    assert field.evidence is None
    assert field.confidence is None

    field2 = scan_late_penalty_clause("Short note only.")
    assert field2.status == "UNCERTAIN"
    assert field2.value is None


def test_incomplete_tc_header_only_is_uncertain() -> None:
    # Header present but body too short to inspect reliably.
    field = scan_late_penalty_clause("TERMS AND CONDITIONS\n1. Payment only.")
    assert field.status == "UNCERTAIN"
    assert field.value is None


def test_unrelated_percentage_or_delay_is_not_false_found() -> None:
    text = _tc(
        "1. Payment. 10% advance. Balance within 30 days of delivery.\n"
        "2. Delivery. Goods delivered within 21 days from the date of PO.\n"
        "3. Validity. Valid for 30 days. VAT 15% shown separately.\n"
        "4. Interest. Late payment interest of 2.0% per month may apply.\n"
    )
    field = scan_late_penalty_clause(text)
    assert field.status == "NOT_FOUND"
    assert field.value is False


def test_decimal_rates_parsed_from_evidence() -> None:
    assert extract_weekly_penalty_pct("penalty of 0.75% per week of delay") == 0.75
    assert extract_weekly_penalty_pct("penalty of 0.5% of order value per week") == 0.5
    assert extract_weekly_penalty_pct("shall pay 1.25% of the order value per week") == 1.25
    assert extract_weekly_penalty_pct("Late delivery penalty: 2.0% per week") == 2.0


def test_found_evidence_is_exact_substring_of_raw_text() -> None:
    raw = _tc(
        "1. Payment. Net 30.\n"
        "3. Delay. For late delivery the supplier shall pay 0.75% of the order "
        "value per week of delay.\n"
    )
    field = scan_late_penalty_clause(raw)
    assert field.status == "FOUND"
    assert field.evidence is not None
    assert field.evidence in raw
