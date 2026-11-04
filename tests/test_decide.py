from pathlib import Path

from supplier_check.decide import decide
from supplier_check.ingest import ingest_pdf
from supplier_check.pr import load_purchase_request
from supplier_check.schemas import FieldExtraction, GraphState, QuotationExtraction

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def test_decide_uncertain_extraction_is_needs() -> None:
    state = ingest_pdf(DATA_DIR / "supplier-pack-01.pdf")
    state.extraction_status = "needs_human"
    state.extraction_issues = ["missing field"]
    state = decide(state)
    assert state.decision == "Needs a person to check"
    assert state.human_review_required is True


def test_decide_pr_mismatch_is_needs() -> None:
    state = GraphState(doc_id="x", ingestion_ok=True, raw_text="x")
    state.extraction_status = "ok"
    state.pr_match_ok = False
    state = decide(state)
    assert state.decision == "Needs a person to check"
    assert any("purchase-request" in r for r in state.reasons)


def test_decide_ok_status_without_extraction_is_needs() -> None:
    # extraction_status ok and pr_match_ok but no extraction -> still Needs.
    state = GraphState(doc_id="x", ingestion_ok=True, raw_text="x")
    state.extraction_status = "ok"
    state.pr_match_ok = True
    state.extraction = None
    state.pr_row = None
    state = decide(state)
    assert state.decision == "Needs a person to check"


def _approved_extraction() -> QuotationExtraction:
    null = FieldExtraction(value=None, evidence=None, confidence=0.0)
    values = {
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
    base = {name: null.model_copy() for name in QuotationExtraction.model_fields}
    for key, value in values.items():
        base[key] = FieldExtraction(value=value, evidence="x", confidence=1.0)
    return QuotationExtraction.model_validate(
        {name: field.model_dump() for name, field in base.items()}
    )


def test_decide_full_approve_path() -> None:
    pr = load_purchase_request(DATA_DIR / "purchase-request.csv")
    row = pr["A"]
    state = ingest_pdf(DATA_DIR / "supplier-pack-01.pdf")
    state.extraction = _approved_extraction()
    state.extraction_status = "ok"
    state.pr_row = row
    state.pr_match_ok = True
    state.price_over_max_pct = 0.0
    state.qty_diff_pct = 0.0
    state.price_diff_pct = 0.0
    state = decide(state)
    assert state.decision == "Approve"
    assert state.human_review_required is False
