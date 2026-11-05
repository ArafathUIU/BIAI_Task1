"""D21: percentage evidence-value reconciliation in verify."""

from __future__ import annotations

from pathlib import Path

from tests.test_golden_labels import PACK_EXTRACTIONS
from tests.test_rules import make_extraction

from supplier_check.decide import decide
from supplier_check.extract import parse_extraction
from supplier_check.ingest import ingest_pdf
from supplier_check.pr import load_purchase_request
from supplier_check.rules import apply_rules
from supplier_check.schemas import FieldExtraction, QuotationExtraction
from supplier_check.verify import (
    apply_late_penalty_scan,
    evidence_ok,
    reconcile_percent_field,
    verify_extraction,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
RAW_PACK05 = Path(__file__).resolve().parents[1] / "runs" / "_pack05_raw_llm.json"


def _field(value, evidence: str | None, confidence: float = 1.0) -> FieldExtraction:
    return FieldExtraction(value=value, evidence=evidence, confidence=confidence)


def test_percent_direct_match_40_found() -> None:
    field = _field(40, "40% advance payable with the purchase order.")
    notes = reconcile_percent_field("advance_payment_pct", field)
    assert notes == []
    assert field.value == 40
    assert field.status == "FOUND"


def test_percent_fraction_0_4_normalized_to_40() -> None:
    field = _field(0.4, "40% advance payable with the purchase order.")
    notes = reconcile_percent_field("advance_payment_pct", field)
    assert field.value == 40
    assert field.status == "FOUND"
    assert any("Normalized" in n for n in notes)
    assert any("0.4" in n and "40" in n for n in notes)


def test_percent_genuine_0_4_pct_not_normalized() -> None:
    field = _field(0.4, "Late delivery penalty of 0.4% of order value per week.")
    notes = reconcile_percent_field("advance_payment_pct", field)
    assert notes == []
    assert field.value == 0.4
    assert field.status == "FOUND"


def test_percent_mismatch_40_evidence_value_20_uncertain() -> None:
    field = _field(20, "40% advance payable with the purchase order.")
    notes = reconcile_percent_field("advance_payment_pct", field)
    assert field.status == "UNCERTAIN"
    assert field.value is None
    assert any("does not match evidence percentage 40" in n for n in notes)


def test_percent_missing_evidence_keeps_evidence_ok_contract() -> None:
    field = _field(40, None)
    assert evidence_ok(field, "40% advance") is False
    notes = reconcile_percent_field("advance_payment_pct", field)
    assert notes == []
    assert field.value == 40


def test_percent_unrelated_evidence_no_pct_token_uncertain() -> None:
    field = _field(40, "Delivery within 25 days of PO.")
    notes = reconcile_percent_field("advance_payment_pct", field)
    assert field.status == "UNCERTAIN"
    assert field.value is None
    assert any("no percentage token" in n for n in notes)


def test_percent_multiple_values_without_context_uncertain() -> None:
    field = _field(40, "Rates may be 40% or 60% as agreed by both parties.")
    notes = reconcile_percent_field("advance_payment_pct", field)
    assert field.status == "UNCERTAIN"
    assert field.value is None
    assert any("multiple percentages" in n for n in notes)


def test_percent_multiple_values_advance_context_selects_reliably() -> None:
    field = _field(
        0.4,
        "40% advance payable with the purchase order, balance 60% within 30 days.",
    )
    notes = reconcile_percent_field("advance_payment_pct", field)
    assert field.value == 40
    assert field.status == "FOUND"
    assert any("Normalized" in n for n in notes)


def _pack05_fraction_extraction(raw_text: str) -> QuotationExtraction:
    """Build Pack 05 extraction with the observed 0.4 advance fraction bug."""
    values = {
        "supplier_name": ("Meghna Carton Works", "Meghna Carton Works"),
        "quotation_no": ("QT-2026-905", "Quotation no. QT-2026-905"),
        "quotation_date": ("2026-10-25", "Date 2026-10-25"),
        "item_code": ("E", "E Carton box, 5-ply 3,000 piece 92.00 276,000.00"),
        "description": ("Carton box, 5-ply", "Carton box, 5-ply"),
        "quantity": (3000, "3,000"),
        "unit": ("piece", "piece"),
        "unit_price": (92.0, "92.00"),
        "currency": ("BDT", "Unit price (BDT)"),
        "line_amount": (276000.0, "276,000.00"),
        "subtotal": (276000.0, "Subtotal 276,000.00"),
        "vat_rate": (15.0, "VAT 15%"),
        "vat_amount": (41400.0, "41,400.00"),
        "total": (317400.0, "Total 317,400.00"),
        "advance_payment_pct": (0.4, "40% advance payable with the purchase order."),
        "balance_payment_days": (30, "within 30 days of delivery."),
        "delivery_days": (25, "Delivery within 25 days of PO."),
        "late_penalty_clause_present": (
            True,
            "Late delivery penalty of 1% of order value per week.",
        ),
        "late_penalty_pct_per_week": (
            0.01,
            "Late delivery penalty of 1% of order value per week.",
        ),
        "validity_days": (30, "valid for 30 days from the date above."),
        "tin": ("105458053391", "Supplier TIN: 105458053391"),
        "bin": ("000570541-0101", "BIN: 000570541-0101"),
    }
    data = {
        name: {"value": None, "evidence": None, "confidence": None}
        for name in QuotationExtraction.model_fields
    }
    for key, (value, evidence) in values.items():
        assert evidence in raw_text, evidence
        data[key] = {"value": value, "evidence": evidence, "confidence": 1.0}
    return QuotationExtraction.model_validate(data)


def test_pack_05_replay_fraction_advance_rejects() -> None:
    """Replay the observed LLM fraction bug through verify ? rules ? decide."""
    state = ingest_pdf(DATA_DIR / "supplier-pack-05.pdf")
    if RAW_PACK05.exists():
        extraction, issues = parse_extraction(RAW_PACK05.read_text(encoding="utf-8"))
        assert extraction is not None, issues
        # payment_terms_text evidence may span a newline in the PDF; clear if needed.
        pt = extraction.payment_terms_text
        if pt.evidence and pt.evidence not in state.raw_text:
            extraction.payment_terms_text = _field(None, None)
    else:
        extraction = _pack05_fraction_extraction(state.raw_text)

    state.extraction = extraction
    state = verify_extraction(state)
    assert state.extraction is not None
    assert state.extraction.advance_payment_pct.value == 40
    assert state.extraction.advance_payment_pct.status == "FOUND"
    assert any("Normalized" in i and "advance_payment_pct" in i for i in state.extraction_issues)
    # D20 still owns weekly penalty (1%, not LLM 0.01).
    assert state.extraction.late_penalty_pct_per_week.value == 1.0
    assert state.extraction_status == "ok"

    pr = load_purchase_request(DATA_DIR / "purchase-request.csv")
    row = pr["E"]
    up = float(state.extraction.unit_price.value)
    max_p = float(row["max_unit_price"])
    over = (up - max_p) / max_p * 100
    state.pr_row = row
    state.pr_match_ok = True
    state.price_over_max_pct = over
    state.qty_diff_pct = 0.0
    state = decide(state)
    assert state.decision == "Reject"
    assert state.rule_result is not None
    assert "reject_advance_over_20pct" in state.rule_result.rule_hits


def test_pack_02_remains_approve_after_percent_reconcile() -> None:
    state = ingest_pdf(DATA_DIR / "supplier-pack-02.pdf")
    fields = dict(PACK_EXTRACTIONS["supplier-pack-02"])
    extraction = make_extraction(**fields)
    apply_late_penalty_scan(extraction, state.raw_text)
    extraction.advance_payment_pct = _field(0.0, "No advance payment required.")
    notes = reconcile_percent_field("advance_payment_pct", extraction.advance_payment_pct)
    assert notes == []
    assert extraction.advance_payment_pct.value == 0.0
    assert extraction.late_penalty_clause_present.value is True
    assert extraction.late_penalty_pct_per_week.value == 0.75

    pr = load_purchase_request(DATA_DIR / "purchase-request.csv")
    row = pr["B"]
    over = (fields["unit_price"] - float(row["max_unit_price"])) / float(row["max_unit_price"]) * 100
    result = apply_rules(extraction, row, over)
    assert result.decision == "Approve"


def test_pack_06_remains_reject_after_percent_reconcile() -> None:
    state = ingest_pdf(DATA_DIR / "supplier-pack-06.pdf")
    fields = dict(PACK_EXTRACTIONS["supplier-pack-06"])
    extraction = make_extraction(**fields)
    apply_late_penalty_scan(extraction, state.raw_text)
    extraction.advance_payment_pct = _field(10.0, "10% advance payable with the purchase order.")
    notes = reconcile_percent_field("advance_payment_pct", extraction.advance_payment_pct)
    assert notes == []
    assert extraction.advance_payment_pct.value == 10.0
    assert extraction.late_penalty_clause_present.status == "NOT_FOUND"
    assert extraction.late_penalty_clause_present.value is False

    pr = load_purchase_request(DATA_DIR / "purchase-request.csv")
    row = pr["A"]
    over = (fields["unit_price"] - float(row["max_unit_price"])) / float(row["max_unit_price"]) * 100
    result = apply_rules(extraction, row, over)
    assert result.decision == "Reject"
    assert "reject_no_late_penalty_clause" in result.rule_hits
