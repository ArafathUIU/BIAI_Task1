"""Lock decisions against tests/fixtures/expected.json (no live LLM)."""

from __future__ import annotations

import json
from pathlib import Path

from tests.test_rules import make_extraction

from supplier_check.pr import load_purchase_request
from supplier_check.rules import apply_rules

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
EXPECTED_PATH = ROOT / "tests" / "fixtures" / "expected.json"

# Canned, correct extractions fields for each pack (ground truth for the rule engine).
PACK_EXTRACTIONS: dict[str, dict] = {
    "supplier-pack-01": {
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
    },
    "supplier-pack-02": {
        "item_code": "B",
        "quantity": 20000,
        "unit": "piece",
        "unit_price": 36.0,
        "delivery_days": 21,
        "advance_payment_pct": 0.0,
        "balance_payment_days": 30,
        "validity_days": 30,
        "late_penalty_clause_present": True,
        "late_penalty_pct_per_week": 0.75,
        "line_amount": 720000.0,
        "subtotal": 720000.0,
        "vat_rate": 15.0,
        "vat_amount": 108000.0,
        "total": 828000.0,
        "tin": "102458023391",
        "bin": "000270241-0101",
    },
    "supplier-pack-03": {
        "item_code": "C",
        "quantity": 800,
        "unit": "cone",
        "unit_price": 229.0,
        "delivery_days": 20,
        "advance_payment_pct": 15.0,
        "balance_payment_days": 40,
        "validity_days": 30,
        "late_penalty_clause_present": True,
        "late_penalty_pct_per_week": 0.5,
        "line_amount": 183200.0,
        "subtotal": 183200.0,
        "vat_rate": 15.0,
        "vat_amount": 27480.0,
        "total": 210680.0,
        "tin": "103458033391",
        "bin": "000370341-0101",
    },
    "supplier-pack-04": {
        "item_code": "D",
        "quantity": 50000,
        "unit": "piece",
        "unit_price": 6.65,
        "delivery_days": 28,
        "advance_payment_pct": 10.0,
        "balance_payment_days": 30,
        "validity_days": 40,
        "late_penalty_clause_present": True,
        "late_penalty_pct_per_week": 0.6,
        "line_amount": 332500.0,
        "subtotal": 332500.0,
        "vat_rate": 15.0,
        "vat_amount": 49875.0,
        "total": 382375.0,
        "tin": "104458043391",
        "bin": "000470441-0101",
    },
    "supplier-pack-05": {
        "item_code": "E",
        "quantity": 3000,
        "unit": "piece",
        "unit_price": 92.0,
        "delivery_days": 25,
        "advance_payment_pct": 40.0,
        "balance_payment_days": 30,
        "validity_days": 30,
        "late_penalty_clause_present": True,
        "late_penalty_pct_per_week": 1.0,
        "line_amount": 276000.0,
        "subtotal": 276000.0,
        "vat_rate": 15.0,
        "vat_amount": 41400.0,
        "total": 317400.0,
        "tin": "105458053391",
        "bin": "000570541-0101",
    },
    "supplier-pack-06": {
        "item_code": "A",
        "quantity": 12000,
        "unit": "metre",
        "unit_price": 465.0,
        "delivery_days": 27,
        "advance_payment_pct": 10.0,
        "balance_payment_days": 60,
        "validity_days": 30,
        "late_penalty_clause_present": False,
        "late_penalty_pct_per_week": None,
        "line_amount": 5580000.0,
        "subtotal": 5580000.0,
        "vat_rate": 15.0,
        "vat_amount": 837000.0,
        "total": 6417000.0,
        "tin": "106458063391",
        "bin": "000670641-0101",
    },
    "supplier-pack-07": {
        "item_code": "B",
        "quantity": 16500,
        "unit": "piece",
        "unit_price": 35.0,
        "delivery_days": 22,
        "advance_payment_pct": 0.0,
        "balance_payment_days": 45,
        "validity_days": 35,
        "late_penalty_clause_present": True,
        "late_penalty_pct_per_week": 0.5,
        "line_amount": 577500.0,
        "subtotal": 577500.0,
        "vat_rate": 15.0,
        "vat_amount": 86625.0,
        "total": 664125.0,
        "tin": "107458073391",
        "bin": "000770741-0101",
    },
    "supplier-pack-08": {
        "item_code": "C",
        "quantity": 800,
        "unit": "cone",
        "unit_price": 205.0,
        "delivery_days": 18,
        "advance_payment_pct": 10.0,
        "balance_payment_days": 30,
        "validity_days": 30,
        "late_penalty_clause_present": True,
        "late_penalty_pct_per_week": 0.5,
        "line_amount": 164000.0,
        "subtotal": 164000.0,
        "vat_rate": 15.0,
        "vat_amount": 24600.0,
        "total": 188600.0,
        "tin": None,
        "bin": None,
    },
    "supplier-pack-09": {
        "item_code": "D",
        "quantity": 50000,
        "unit": "piece",
        "unit_price": 6.4,
        "delivery_days": 28,
        "advance_payment_pct": 5.0,
        "balance_payment_days": "30 to 90 days",
        "validity_days": 30,
        "late_penalty_clause_present": True,
        "late_penalty_pct_per_week": 0.5,
        "line_amount": 322000.0,
        "subtotal": 322000.0,
        "vat_rate": 15.0,
        "vat_amount": 48300.0,
        "total": 370300.0,
        "tin": "109458093391",
        "bin": "000970941-0101",
    },
    "supplier-pack-10": {
        "item_code": "E",
        "quantity": 3000,
        "unit": "piece",
        "unit_price": 94.0,
        "delivery_days": 60,
        "advance_payment_pct": 10.0,
        "balance_payment_days": 45,
        "validity_days": 30,
        "late_penalty_clause_present": True,
        "late_penalty_pct_per_week": 0.5,
        "line_amount": 282000.0,
        "subtotal": 282000.0,
        "vat_rate": None,
        "vat_amount": None,
        "total": 282000.0,
        "tin": "110458103391",
        "bin": "001071041-0101",
    },
}

# Keywords that must appear in rule reasons / hits for the locked primary reason.
PRIMARY_REASON_TOKENS: dict[str, list[str]] = {
    "supplier-pack-01": ["all company rules pass"],
    "supplier-pack-02": ["all company rules pass"],
    "supplier-pack-03": ["more than 3%"],
    "supplier-pack-04": ["no more than 3%"],
    "supplier-pack-05": ["advance payment is more than 20%"],
    "supplier-pack-06": ["no late-delivery penalty clause"],
    "supplier-pack-07": ["quantity differs"],
    "supplier-pack-08": ["tin or bin is missing"],
    "supplier-pack-09": ["payment terms are unclear", "numbers do not add up"],
    "supplier-pack-10": ["later than 45 days"],
}


def _load_expected() -> dict:
    return json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))


def test_expected_fixture_lists_all_ten_packs() -> None:
    expected = _load_expected()
    assert len(expected["decisions"]) == 10
    assert set(expected["decisions"]) == set(PACK_EXTRACTIONS)


def test_golden_labels_match_rule_engine() -> None:
    expected = _load_expected()
    pr = load_purchase_request(DATA_DIR / "purchase-request.csv")

    for pack_id, fields in PACK_EXTRACTIONS.items():
        item = fields["item_code"]
        row = pr[item]
        max_price = float(row["max_unit_price"])
        price = fields["unit_price"]
        price_over_max = (price - max_price) / max_price * 100
        extraction = make_extraction(**fields)
        result = apply_rules(extraction, row, price_over_max)

        assert result.decision == expected["decisions"][pack_id], pack_id

        reason_blob = " ".join(result.reasons).lower()
        hit_blob = " ".join(result.rule_hits).lower()
        blob = f"{reason_blob} {hit_blob}"
        for token in PRIMARY_REASON_TOKENS[pack_id]:
            assert token in blob, f"{pack_id} missing token {token!r} in {blob!r}"

        # Pack 10 must keep the VAT Needs hit on Reject (D12).
        if pack_id == "supplier-pack-10":
            assert "needs_vat_not_separate_15" in result.rule_hits
