from pathlib import Path

from supplier_check.pr import load_purchase_request
from supplier_check.rules import apply_rules
from supplier_check.schemas import FieldExtraction, QuotationExtraction

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def make_extraction(**overrides) -> QuotationExtraction:
    base = {
        name: FieldExtraction(value=None, evidence=None, confidence=1.0)
        for name in QuotationExtraction.model_fields
    }
    for key, value in overrides.items():
        base[key] = FieldExtraction(value=value, evidence=None, confidence=1.0)
    return QuotationExtraction.model_validate(
        {name: field.model_dump() for name, field in base.items()}
    )


def run_case(item: str, **overrides):
    pr = load_purchase_request(DATA_DIR / "purchase-request.csv")
    row = pr[item]
    max_price = float(row["max_unit_price"])
    price = overrides["unit_price"]
    price_over_max = (price - max_price) / max_price * 100
    extraction = make_extraction(**overrides)
    return apply_rules(extraction, row, price_over_max)


def test_pack_01_approve() -> None:
    r = run_case(
        "A",
        supplier_name="Padma Textile Mills Ltd",
        item_code="A",
        quantity=12000,
        unit="metre",
        unit_price=472.0,
        delivery_days=24,
        advance_payment_pct=10.0,
        balance_payment_days=45,
        validity_days=45,
        late_penalty_clause_present=True,
        late_penalty_pct_per_week=1.0,
        line_amount=5664000.0,
        subtotal=5664000.0,
        vat_rate=15.0,
        vat_amount=849600.0,
        total=6513600.0,
        tin="101458013391",
        bin="000170141-0101",
    )
    assert r.decision == "Approve"


def test_pack_02_approve() -> None:
    r = run_case(
        "B",
        item_code="B",
        quantity=20000,
        unit="piece",
        unit_price=36.0,
        delivery_days=21,
        advance_payment_pct=0.0,
        balance_payment_days=30,
        validity_days=30,
        late_penalty_clause_present=True,
        late_penalty_pct_per_week=0.75,
        line_amount=720000.0,
        subtotal=720000.0,
        vat_rate=15.0,
        vat_amount=108000.0,
        total=828000.0,
        tin="102458023391",
        bin="000270241-0101",
    )
    assert r.decision == "Approve"


def test_pack_03_reject_price() -> None:
    r = run_case(
        "C",
        item_code="C",
        quantity=800,
        unit="cone",
        unit_price=229.0,
        delivery_days=20,
        advance_payment_pct=15.0,
        balance_payment_days=40,
        validity_days=30,
        late_penalty_clause_present=True,
        late_penalty_pct_per_week=0.5,
        line_amount=183200.0,
        subtotal=183200.0,
        vat_rate=15.0,
        vat_amount=27480.0,
        total=210680.0,
        tin="103458033391",
        bin="000370341-0101",
    )
    assert r.decision == "Reject"
    assert any("more than 3% above" in x for x in r.reasons)


def test_pack_04_needs_price() -> None:
    r = run_case(
        "D",
        item_code="D",
        quantity=50000,
        unit="piece",
        unit_price=6.65,
        delivery_days=28,
        advance_payment_pct=10.0,
        balance_payment_days=30,
        validity_days=40,
        late_penalty_clause_present=True,
        late_penalty_pct_per_week=0.6,
        line_amount=332500.0,
        subtotal=332500.0,
        vat_rate=15.0,
        vat_amount=49875.0,
        total=382375.0,
        tin="104458043391",
        bin="000470441-0101",
    )
    assert r.decision == "Needs a person to check"
    assert any("no more than 3%" in x for x in r.reasons)


def test_pack_05_reject_advance() -> None:
    r = run_case(
        "E",
        item_code="E",
        quantity=3000,
        unit="piece",
        unit_price=92.0,
        delivery_days=25,
        advance_payment_pct=40.0,
        balance_payment_days=30,
        validity_days=30,
        late_penalty_clause_present=True,
        late_penalty_pct_per_week=1.0,
        line_amount=276000.0,
        subtotal=276000.0,
        vat_rate=15.0,
        vat_amount=41400.0,
        total=317400.0,
        tin="105458053391",
        bin="000570541-0101",
    )
    assert r.decision == "Reject"
    assert any("Advance payment is more than 20%" in x for x in r.reasons)


def test_pack_06_reject_no_penalty_clause() -> None:
    r = run_case(
        "A",
        item_code="A",
        quantity=12000,
        unit="metre",
        unit_price=465.0,
        delivery_days=27,
        advance_payment_pct=10.0,
        balance_payment_days=60,
        validity_days=30,
        late_penalty_clause_present=False,
        late_penalty_pct_per_week=None,
        line_amount=5580000.0,
        subtotal=5580000.0,
        vat_rate=15.0,
        vat_amount=837000.0,
        total=6417000.0,
        tin="106458063391",
        bin="000670641-0101",
    )
    assert r.decision == "Reject"
    assert any("no late-delivery penalty clause" in x for x in r.reasons)


def test_pack_07_needs_quantity() -> None:
    r = run_case(
        "B",
        item_code="B",
        quantity=16500,
        unit="piece",
        unit_price=35.0,
        delivery_days=22,
        advance_payment_pct=0.0,
        balance_payment_days=45,
        validity_days=35,
        late_penalty_clause_present=True,
        late_penalty_pct_per_week=0.5,
        line_amount=577500.0,
        subtotal=577500.0,
        vat_rate=15.0,
        vat_amount=86625.0,
        total=664125.0,
        tin="107458073391",
        bin="000770741-0101",
    )
    assert r.decision == "Needs a person to check"
    assert any("Quantity differs" in x for x in r.reasons)


def test_pack_08_reject_missing_tin_bin() -> None:
    r = run_case(
        "C",
        item_code="C",
        quantity=800,
        unit="cone",
        unit_price=205.0,
        delivery_days=18,
        advance_payment_pct=10.0,
        balance_payment_days=30,
        validity_days=30,
        late_penalty_clause_present=True,
        late_penalty_pct_per_week=0.5,
        line_amount=164000.0,
        subtotal=164000.0,
        vat_rate=15.0,
        vat_amount=24600.0,
        total=188600.0,
        tin=None,
        bin=None,
    )
    assert r.decision == "Reject"
    assert any("TIN or BIN is missing" in x for x in r.reasons)


def test_pack_09_needs_payment_and_numbers() -> None:
    r = run_case(
        "D",
        item_code="D",
        quantity=50000,
        unit="piece",
        unit_price=6.4,
        delivery_days=28,
        advance_payment_pct=5.0,
        balance_payment_days="30 to 90 days",
        validity_days=30,
        late_penalty_clause_present=True,
        late_penalty_pct_per_week=0.5,
        line_amount=322000.0,
        subtotal=322000.0,
        vat_rate=15.0,
        vat_amount=48300.0,
        total=370300.0,
        tin="109458093391",
        bin="000970941-0101",
    )
    assert r.decision == "Needs a person to check"
    assert any("Payment terms are unclear" in x for x in r.reasons)
    assert any("numbers do not add up" in x.lower() for x in r.reasons)


def test_pack_10_reject_delivery() -> None:
    r = run_case(
        "E",
        item_code="E",
        quantity=3000,
        unit="piece",
        unit_price=94.0,
        delivery_days=60,
        advance_payment_pct=10.0,
        balance_payment_days=45,
        validity_days=30,
        late_penalty_clause_present=True,
        late_penalty_pct_per_week=0.5,
        line_amount=282000.0,
        subtotal=282000.0,
        vat_rate=None,
        vat_amount=None,
        total=282000.0,
        tin="110458103391",
        bin="001071041-0101",
    )
    assert r.decision == "Reject"
    assert any("later than 45 days" in x for x in r.reasons)


def test_rule_boundary_price_exactly_3_pct_is_needs_not_reject() -> None:
    pr = load_purchase_request(DATA_DIR / "purchase-request.csv")
    row = pr["A"]
    max_price = float(row["max_unit_price"])
    price = max_price * 1.03
    extraction = make_extraction(
        item_code="A",
        quantity=12000,
        unit="metre",
        unit_price=price,
        delivery_days=24,
        advance_payment_pct=10.0,
        balance_payment_days=45,
        validity_days=45,
        late_penalty_clause_present=True,
        late_penalty_pct_per_week=1.0,
        line_amount=12000 * price,
        subtotal=12000 * price,
        vat_rate=15.0,
        vat_amount=12000 * price * 0.15,
        total=12000 * price * 1.15,
        tin="1",
        bin="2",
    )
    r = apply_rules(extraction, row, (price - max_price) / max_price * 100)
    assert r.decision == "Needs a person to check"


def test_rule_boundary_delivery_45_days_is_needs() -> None:
    pr = load_purchase_request(DATA_DIR / "purchase-request.csv")
    row = pr["A"]
    extraction = make_extraction(
        item_code="A",
        quantity=12000,
        unit="metre",
        unit_price=480.0,
        delivery_days=45,
        advance_payment_pct=10.0,
        balance_payment_days=45,
        validity_days=45,
        late_penalty_clause_present=True,
        late_penalty_pct_per_week=1.0,
        line_amount=5760000.0,
        subtotal=5760000.0,
        vat_rate=15.0,
        vat_amount=864000.0,
        total=6624000.0,
        tin="1",
        bin="2",
    )
    r = apply_rules(extraction, row, 0.0)
    assert r.decision == "Needs a person to check"


def test_rule_boundary_delivery_46_days_is_reject() -> None:
    pr = load_purchase_request(DATA_DIR / "purchase-request.csv")
    row = pr["A"]
    extraction = make_extraction(
        item_code="A",
        quantity=12000,
        unit="metre",
        unit_price=480.0,
        delivery_days=46,
        advance_payment_pct=10.0,
        balance_payment_days=45,
        validity_days=45,
        late_penalty_clause_present=True,
        late_penalty_pct_per_week=1.0,
        line_amount=5760000.0,
        subtotal=5760000.0,
        vat_rate=15.0,
        vat_amount=864000.0,
        total=6624000.0,
        tin="1",
        bin="2",
    )
    r = apply_rules(extraction, row, 0.0)
    assert r.decision == "Reject"
