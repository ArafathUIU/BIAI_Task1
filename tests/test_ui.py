from supplier_check.schemas import FieldExtraction, GraphState, QuotationExtraction
from supplier_check.ui import (
    _counts,
    _field_rows,
    _resolve_path,
    _results_rows,
    decision_badge_html,
    render_html_table,
    render_markdown_table,
)


def test_resolve_path_uses_project_root() -> None:
    path = _resolve_path("data")
    assert path.name == "data"
    assert path.is_absolute()
    assert (path / "purchase-request.csv").exists()


def test_results_rows_and_markdown_table() -> None:
    state = GraphState(
        doc_id="supplier-pack-01",
        decision="Approve",
        reasons=["All company rules pass."],
        qty_diff_pct=0.0,
        price_diff_pct=-1.67,
    )
    rows = _results_rows([state])
    assert rows[0]["Document"] == "supplier-pack-01"
    assert rows[0]["Decision"] == "Approve"
    assert "Price %" in rows[0]
    md = render_markdown_table(rows)
    assert "Document" in md
    assert "supplier-pack-01" in md
    assert "|" in md


def test_html_table_includes_decision_badge() -> None:
    rows = [
        {
            "Document": "supplier-pack-03",
            "Decision": "Reject",
            "Primary reason": "price",
        }
    ]
    html_out = render_html_table(rows, decision_col="Decision")
    assert "Reject" in html_out
    assert "#FDECEC" in html_out  # reject badge background


def test_decision_badge_and_counts() -> None:
    states = [
        GraphState(doc_id="a", decision="Approve"),
        GraphState(doc_id="b", decision="Reject"),
        GraphState(doc_id="c", decision="Needs a person to check"),
        GraphState(doc_id="d", decision="Reject"),
    ]
    assert _counts(states) == {
        "Approve": 1,
        "Reject": 2,
        "Needs a person to check": 1,
    }
    assert "Approve" in decision_badge_html("Approve")


def test_field_rows_hides_empty_by_default() -> None:
    null = FieldExtraction()
    payload = {name: null.model_copy() for name in QuotationExtraction.model_fields}
    payload["supplier_name"] = FieldExtraction(
        value="Padma Textile Mills Ltd", evidence="Padma Textile Mills Ltd", confidence=0.9
    )
    extraction = QuotationExtraction.model_validate(
        {k: v.model_dump() for k, v in payload.items()}
    )
    state = GraphState(doc_id="x", extraction=extraction)
    filled = _field_rows(state, filled_only=True)
    assert len(filled) == 1
    assert filled[0]["Field"] == "supplier_name"
    assert len(_field_rows(state, filled_only=False)) == len(QuotationExtraction.model_fields)
