import json
from pathlib import Path

import pytest

from supplier_check.extract import extract_quotation
from supplier_check.ingest import ingest_pdf
from supplier_check.schemas import QuotationExtraction
from supplier_check.verify import arithmetic_issues, verify_extraction

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

NULL_FIELD = {"value": None, "evidence": None, "confidence": 0.0}


def _payload(overrides: dict | None = None) -> dict:
    """Build a canned extraction whose non-null evidence is a real substring."""
    overrides = overrides or {}
    base = {name: dict(NULL_FIELD) for name in QuotationExtraction.model_fields}
    defaults = {
        "supplier_name": "Padma Textile Mills Ltd",
        "item_code": "A",
        "quantity": 12000,
        "unit": "metre",
        "unit_price": 472.0,
        "delivery_days": 24,
        "advance_payment_pct": 10.0,
        "balance_payment_days": 45,
        "validity_days": 45,
        "late_penalty_clause_present": True,
        "late_penalty_pct_per_week": 1.0,
        "line_amount": 5664000.0,
        "subtotal": 5664000.0,
        "vat_rate": 15.0,
        "vat_amount": 849600.0,
        "total": 6513600.0,
        "tin": "101458013391",
        "bin": "000170141-0101",
    }
    for key, value in {**defaults, **overrides}.items():
        if value is None:
            base[key] = dict(NULL_FIELD)
        else:
            base[key] = {"value": value, "evidence": "days", "confidence": 1.0}
    return base


@pytest.fixture
def mock_llm(monkeypatch):
    def _set(payload: dict) -> None:
        monkeypatch.setattr(
            "supplier_check.extract.call_llm",
            lambda messages, client=None, model=None: json.dumps(payload),
        )

    return _set


def test_pack_01_verifies_ok(mock_llm) -> None:
    mock_llm(_payload())
    state = ingest_pdf(DATA_DIR / "supplier-pack-01.pdf")
    state = extract_quotation(state)
    state = verify_extraction(state)
    assert state.extraction_status == "ok"


def test_pack_09_arithmetic_mismatch_is_needs_human(mock_llm) -> None:
    mock_llm(
        _payload(
            {
                "item_code": "D",
                "quantity": 50000,
                "unit": "piece",
                "unit_price": 6.4,
                "delivery_days": 28,
                "advance_payment_pct": 5.0,
                "balance_payment_days": 45,
                "validity_days": 30,
                "line_amount": 322000.0,
                "subtotal": 322000.0,
                "vat_rate": 15.0,
                "vat_amount": 48300.0,
                "total": 370300.0,
                "tin": "109458093391",
                "bin": "000970941-0101",
            }
        )
    )
    state = ingest_pdf(DATA_DIR / "supplier-pack-09.pdf")
    state = extract_quotation(state)
    state = verify_extraction(state)
    assert state.extraction_status == "needs_human"
    assert any("Numbers do not add up" in i for i in state.extraction_issues)


def test_pack_10_verifies_ok_despite_null_vat(mock_llm) -> None:
    mock_llm(
        _payload(
            {
                "item_code": "E",
                "quantity": 3000,
                "unit": "piece",
                "unit_price": 94.0,
                "delivery_days": 60,
                "advance_payment_pct": 10.0,
                "balance_payment_days": 45,
                "validity_days": 30,
                "line_amount": 282000.0,
                "subtotal": 282000.0,
                "vat_rate": None,
                "vat_amount": None,
                "total": 282000.0,
                "tin": "110458103391",
                "bin": "001071041-0101",
            }
        )
    )
    state = ingest_pdf(DATA_DIR / "supplier-pack-10.pdf")
    state = extract_quotation(state)
    state = verify_extraction(state)
    assert state.extraction_status == "ok"


def test_evidence_must_be_substring(mock_llm) -> None:
    mock_llm(_payload())
    state = ingest_pdf(DATA_DIR / "supplier-pack-01.pdf")
    state = extract_quotation(state)
    assert state.extraction is not None
    state.extraction.supplier_name.evidence = "not in document"
    state = verify_extraction(state)
    assert state.extraction_status == "needs_human"
    assert any("evidence is not an exact quote" in i for i in state.extraction_issues)


def test_arithmetic_issues_detects_mismatch(mock_llm) -> None:
    mock_llm(_payload())
    state = ingest_pdf(DATA_DIR / "supplier-pack-01.pdf")
    state = extract_quotation(state)
    assert state.extraction is not None
    state.extraction.line_amount.value = 999999.0
    issues = arithmetic_issues(state.extraction)
    assert any("Numbers do not add up" in i for i in issues)
