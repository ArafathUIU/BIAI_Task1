import json
from pathlib import Path

import pytest

from supplier_check.extract import extract_quotation
from supplier_check.ingest import ingest_pdf
from supplier_check.schemas import QuotationExtraction
from supplier_check.verify import arithmetic_issues, evidence_ok, verify_extraction

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

NULL_FIELD = {"value": None, "evidence": None, "confidence": 0.0}

# Evidence strings must be exact substrings of the matching PDF text.
PACK01_FIELDS = {
    "supplier_name": ("Padma Textile Mills Ltd", "Padma Textile Mills Ltd"),
    "item_code": ("A", "A Cotton twill fabric, 280 gsm 12,000 metre 472.00"),
    "quantity": (12000, "12,000"),
    "unit": ("metre", "metre"),
    "unit_price": (472.0, "472.00"),
    "delivery_days": (24, "Delivery within 24 days"),
    "advance_payment_pct": (10.0, "10% advance"),
    "balance_payment_days": (45, "within 45 days after delivery"),
    "validity_days": (45, "valid for 45 days"),
    "late_penalty_clause_present": (True, "Late delivery penalty: 1%"),
    "late_penalty_pct_per_week": (1.0, "Late delivery penalty: 1%"),
    "line_amount": (5664000.0, "5,664,000.00"),
    "subtotal": (5664000.0, "Subtotal 5,664,000.00"),
    "vat_rate": (15.0, "VAT 15%"),
    "vat_amount": (849600.0, "849,600.00"),
    "total": (6513600.0, "Total 6,513,600.00"),
    "tin": ("101458013391", "TIN: 101458013391"),
    "bin": ("000170141-0101", "BIN: 000170141-0101"),
}

PACK09_FIELDS = {
    "supplier_name": ("Dhaleshwari Poly Pack", "Dhaleshwari Poly Pack"),
    "item_code": ("D", "D Poly bag, 30 x 40 cm 50,000 piece 6.40"),
    "quantity": (50000, "50,000"),
    "unit": ("piece", "piece"),
    "unit_price": (6.4, "6.40"),
    "delivery_days": (28, "Delivery within 4 weeks"),
    "advance_payment_pct": (5.0, "5% advance"),
    "balance_payment_days": ("30 to 90 days", "30 to 90 days"),
    "validity_days": (30, "valid for 30 days"),
    "late_penalty_clause_present": (True, "Late delivery penalty of 0.5%"),
    "late_penalty_pct_per_week": (0.5, "0.5% of order value per week"),
    # Intentionally wrong line total vs 6.40 x 50,000 = 320,000
    "line_amount": (322000.0, "322,000.00"),
    "subtotal": (322000.0, "Subtotal 322,000.00"),
    "vat_rate": (15.0, "VAT 15%"),
    "vat_amount": (48300.0, "48,300.00"),
    "total": (370300.0, "Total 370,300.00"),
    "tin": ("109458093391", "TIN: 109458093391"),
    "bin": ("000970941-0101", "BIN: 000970941-0101"),
}

PACK10_FIELDS = {
    "supplier_name": ("Kushiyara Box Industries", "Kushiyara Box Industries"),
    "item_code": ("E", "E Carton box, 5-ply 3,000 piece 94.00"),
    "quantity": (3000, "3,000"),
    "unit": ("piece", "piece"),
    "unit_price": (94.0, "94.00"),
    "delivery_days": (60, "Delivery within 60 days"),
    "advance_payment_pct": (10.0, "10% advance"),
    "balance_payment_days": (45, "within 45 days of delivery"),
    "validity_days": (30, "valid for 30 days"),
    "late_penalty_clause_present": (True, "Late delivery penalty of 0.5%"),
    "late_penalty_pct_per_week": (0.5, "0.5% of order value per week"),
    "line_amount": (282000.0, "282,000.00"),
    "subtotal": (282000.0, "282,000.00"),
    "vat_rate": None,
    "vat_amount": None,
    "total": (282000.0, "Total (all taxes included) 282,000.00"),
    "tin": ("110458103391", "TIN: 110458103391"),
    "bin": ("001071041-0101", "BIN: 001071041-0101"),
}


def _payload(field_map: dict) -> dict:
    """Build extraction JSON with real per-field evidence substrings."""
    base = {name: dict(NULL_FIELD) for name in QuotationExtraction.model_fields}
    for key, spec in field_map.items():
        if spec is None:
            base[key] = dict(NULL_FIELD)
            continue
        if not isinstance(spec, tuple):
            raise TypeError(f"field_map[{key!r}] must be (value, evidence) or None")
        value, evidence = spec
        if value is None:
            base[key] = dict(NULL_FIELD)
        else:
            base[key] = {"value": value, "evidence": evidence, "confidence": 1.0}
    return base


@pytest.fixture
def mock_llm(monkeypatch):
    def _set(payload: dict) -> None:
        monkeypatch.setattr(
            "supplier_check.extract.call_llm",
            lambda messages, client=None, model=None: json.dumps(payload),
        )

    return _set


def test_pack_01_evidence_snippets_are_real_substrings() -> None:
    state = ingest_pdf(DATA_DIR / "supplier-pack-01.pdf")
    for name, (value, evidence) in PACK01_FIELDS.items():
        field = type("F", (), {"value": value, "evidence": evidence})()
        assert evidence_ok(field, state.raw_text), f"{name}: {evidence!r}"


def test_pack_01_verifies_ok(mock_llm) -> None:
    mock_llm(_payload(PACK01_FIELDS))
    state = ingest_pdf(DATA_DIR / "supplier-pack-01.pdf")
    state = extract_quotation(state)
    state = verify_extraction(state)
    assert state.extraction_status == "ok"


def test_pack_09_arithmetic_mismatch_noted_but_verify_can_pass(mock_llm) -> None:
    mock_llm(_payload(PACK09_FIELDS))
    state = ingest_pdf(DATA_DIR / "supplier-pack-09.pdf")
    state = extract_quotation(state)
    state = verify_extraction(state)
    # Math errors are left for the rule engine (Needs), not extract failure.
    assert state.extraction_status == "ok"
    assert any("Numbers do not add up" in i for i in state.extraction_issues)


def test_pack_10_verifies_ok_despite_null_vat(mock_llm) -> None:
    mock_llm(_payload(PACK10_FIELDS))
    state = ingest_pdf(DATA_DIR / "supplier-pack-10.pdf")
    state = extract_quotation(state)
    state = verify_extraction(state)
    assert state.extraction_status == "ok"


def test_evidence_must_be_substring(mock_llm) -> None:
    mock_llm(_payload(PACK01_FIELDS))
    state = ingest_pdf(DATA_DIR / "supplier-pack-01.pdf")
    state = extract_quotation(state)
    assert state.extraction is not None
    state.extraction.supplier_name.evidence = "not in document"
    state = verify_extraction(state)
    assert state.extraction_status == "needs_human"
    assert any("evidence is not an exact quote" in i for i in state.extraction_issues)


def test_optional_field_without_evidence_is_cleared_not_failed(mock_llm) -> None:
    mock_llm(_payload(PACK01_FIELDS))
    state = ingest_pdf(DATA_DIR / "supplier-pack-01.pdf")
    state = extract_quotation(state)
    assert state.extraction is not None
    state.extraction.payment_terms_text.value = "some terms"
    state.extraction.payment_terms_text.evidence = None
    state = verify_extraction(state)
    assert state.extraction_status == "ok"
    assert state.extraction.payment_terms_text.value is None
    assert any("Cleared unverified optional field" in i for i in state.extraction_issues)


def test_llm_false_penalty_without_evidence_is_overwritten_by_scan(mock_llm) -> None:
    mock_llm(_payload(PACK01_FIELDS))
    state = ingest_pdf(DATA_DIR / "supplier-pack-01.pdf")
    state = extract_quotation(state)
    assert state.extraction is not None
    # Model guesses false with no evidence; pack-01 text actually has a clause.
    state.extraction.late_penalty_clause_present.value = False
    state.extraction.late_penalty_clause_present.evidence = None
    state.extraction.late_penalty_clause_present.confidence = 0.0
    state = verify_extraction(state)
    assert state.extraction_status == "ok"
    assert state.extraction.late_penalty_clause_present.value is True
    assert state.extraction.late_penalty_clause_present.status == "FOUND"
    assert state.extraction.late_penalty_clause_present.evidence


def test_arithmetic_issues_detects_mismatch(mock_llm) -> None:
    mock_llm(_payload(PACK01_FIELDS))
    state = ingest_pdf(DATA_DIR / "supplier-pack-01.pdf")
    state = extract_quotation(state)
    assert state.extraction is not None
    state.extraction.line_amount.value = 999999.0
    issues = arithmetic_issues(state.extraction)
    assert any("Numbers do not add up" in i for i in issues)


def test_low_confidence_alone_does_not_fail(mock_llm, monkeypatch) -> None:
    monkeypatch.setattr("supplier_check.verify.CONFIDENCE_THRESHOLD", 0.80)
    mock_llm(_payload(PACK01_FIELDS))
    state = ingest_pdf(DATA_DIR / "supplier-pack-01.pdf")
    state = extract_quotation(state)
    assert state.extraction is not None
    state.extraction.supplier_name.confidence = 0.5
    state = verify_extraction(state)
    assert state.extraction_status == "ok"
    assert any("Low confidence" in i for i in state.extraction_issues)
