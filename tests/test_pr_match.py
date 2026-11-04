from decimal import Decimal
from pathlib import Path

from supplier_check.pr import apply_pr_comparison, get_pr_row, load_purchase_request

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def test_load_purchase_request_has_five_items() -> None:
    pr = load_purchase_request(DATA_DIR / "purchase-request.csv")
    assert set(pr) == {"A", "B", "C", "D", "E"}
    assert pr["A"]["quantity_requested"] == 12000
    assert pr["A"]["max_unit_price"] == Decimal("480.00")


def test_get_pr_row_missing_returns_none() -> None:
    pr = load_purchase_request(DATA_DIR / "purchase-request.csv")
    assert get_pr_row("Z", pr) is None
    assert get_pr_row(None, pr) is None


def test_apply_pr_comparison_computes_percentages() -> None:
    # Build a minimal state with a canned extraction by monkeypatching.
    import json

    import supplier_check.extract as ex
    from supplier_check.extract import extract_quotation
    from supplier_check.ingest import ingest_pdf

    payload = {
        "supplier_name": {"value": "X", "evidence": None, "confidence": 1.0},
        "item_code": {"value": "A", "evidence": None, "confidence": 1.0},
        "quantity": {"value": 12000, "evidence": None, "confidence": 1.0},
        "unit": {"value": "metre", "evidence": None, "confidence": 1.0},
        "unit_price": {"value": 490.0, "evidence": None, "confidence": 1.0},
        "delivery_days": {"value": 24, "evidence": None, "confidence": 1.0},
        "advance_payment_pct": {"value": 10.0, "evidence": None, "confidence": 1.0},
        "balance_payment_days": {"value": 45, "evidence": None, "confidence": 1.0},
        "validity_days": {"value": 45, "evidence": None, "confidence": 1.0},
        "late_penalty_clause_present": {"value": True, "evidence": None, "confidence": 1.0},
        "late_penalty_pct_per_week": {"value": 1.0, "evidence": None, "confidence": 1.0},
        "line_amount": {"value": 5880000.0, "evidence": None, "confidence": 1.0},
        "subtotal": {"value": 5880000.0, "evidence": None, "confidence": 1.0},
        "vat_rate": {"value": 15.0, "evidence": None, "confidence": 1.0},
        "vat_amount": {"value": 882000.0, "evidence": None, "confidence": 1.0},
        "total": {"value": 6762000.0, "evidence": None, "confidence": 1.0},
        "tin": {"value": "1", "evidence": None, "confidence": 1.0},
        "bin": {"value": "2", "evidence": None, "confidence": 1.0},
        "quotation_no": {"value": None, "evidence": None, "confidence": 0.0},
        "quotation_date": {"value": None, "evidence": None, "confidence": 0.0},
        "description": {"value": None, "evidence": None, "confidence": 0.0},
        "currency": {"value": None, "evidence": None, "confidence": 0.0},
        "payment_terms_text": {"value": None, "evidence": None, "confidence": 0.0},
    }
    ex.call_llm = lambda messages, client=None, model=None: json.dumps(payload)

    state = ingest_pdf(DATA_DIR / "supplier-pack-01.pdf")
    state = extract_quotation(state)
    pr = load_purchase_request(DATA_DIR / "purchase-request.csv")
    state = apply_pr_comparison(state, pr)
    assert state.pr_match_ok is True
    # 490 vs 480 = +2.0833%
    assert state.price_over_max_pct is not None
    assert abs(state.price_over_max_pct - 2.0833) < 0.01
    assert state.qty_diff_pct == 0.0
