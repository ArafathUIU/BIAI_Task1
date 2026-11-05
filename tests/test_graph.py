import json
from pathlib import Path

import pytest

from supplier_check.graph import build_graph, run_batch

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _pack01_payload() -> dict:
    from tests.test_verify import PACK01_FIELDS, _payload

    return _payload(PACK01_FIELDS)


@pytest.fixture
def mock_llm(monkeypatch):
    def _set(payload):
        monkeypatch.setattr(
            "supplier_check.extract.call_llm",
            lambda messages, client=None, model=None: json.dumps(payload),
        )

    return _set


def test_graph_runs_pack_01_end_to_end(mock_llm, tmp_path) -> None:
    mock_llm(_pack01_payload())
    graph = build_graph(DATA_DIR / "purchase-request.csv")
    state = {"doc_id": "supplier-pack-01", "file_path": str(DATA_DIR / "supplier-pack-01.pdf")}
    final = graph.invoke(state)
    assert final["decision"] == "Approve"
    assert final["pr_match_ok"] is True
    assert final["extraction_status"] == "ok"


def test_run_batch_writes_audit_jsonl(mock_llm, tmp_path, monkeypatch) -> None:
    mock_llm(_pack01_payload())
    monkeypatch.setattr(
        "supplier_check.extract.get_client_and_model",
        lambda: (object(), "llama-3.3-70b-versatile"),
    )
    # Only one pack present in a temp folder to keep it fast.
    import shutil

    work = tmp_path / "data"
    work.mkdir()
    shutil.copy(DATA_DIR / "supplier-pack-01.pdf", work / "supplier-pack-01.pdf")
    shutil.copy(DATA_DIR / "purchase-request.csv", work / "purchase-request.csv")
    run_dir = run_batch(work, tmp_path / "runs")
    audit = run_dir / "results.jsonl"
    assert audit.exists()
    lines = audit.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["doc_id"] == "supplier-pack-01"
    assert record["decision"] == "Approve"
    assert record["model"] == "llama-3.3-70b-versatile"


def test_run_batch_continues_after_pipeline_error(mock_llm, tmp_path, monkeypatch) -> None:
    mock_llm(_pack01_payload())
    import shutil

    from supplier_check import graph as graph_mod

    work = tmp_path / "data"
    work.mkdir()
    shutil.copy(DATA_DIR / "supplier-pack-01.pdf", work / "supplier-pack-01.pdf")
    shutil.copy(DATA_DIR / "supplier-pack-02.pdf", work / "supplier-pack-02.pdf")
    shutil.copy(DATA_DIR / "purchase-request.csv", work / "purchase-request.csv")

    real_build = graph_mod.build_graph

    class BoomGraph:
        def invoke(self, state):
            if state.get("doc_id") == "supplier-pack-01":
                raise RuntimeError("boom")
            return real_build(work / "purchase-request.csv").invoke(state)

    monkeypatch.setattr(graph_mod, "build_graph", lambda pr_path: BoomGraph())
    run_dir = run_batch(work, tmp_path / "runs")
    lines = [
        json.loads(line)
        for line in (run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(lines) == 2
    by_id = {row["doc_id"]: row for row in lines}
    assert by_id["supplier-pack-01"]["decision"] == "Needs a person to check"
    assert "Pipeline error" in by_id["supplier-pack-01"]["reasons"][0]
    assert by_id["supplier-pack-02"]["decision"] in {
        "Approve",
        "Reject",
        "Needs a person to check",
    }


def test_pack_05_fraction_advance_rejects_end_to_end(mock_llm) -> None:
    """Pack 05 LLM returns advance 0.4 (fraction) with evidence '40% ...'.

    Percent reconciliation (D21) must normalize 0.4 → 40, then rule engine
    rejects for advance > 20%.
    """
    payload = {
        "supplier_name": {"value": "Meghna Carton Works", "evidence": "Meghna Carton Works", "confidence": 1.0},
        "quotation_no": {"value": "QT-2026-905", "evidence": "Quotation no. QT-2026-905", "confidence": 1.0},
        "quotation_date": {"value": "2026-10-25", "evidence": "Date 2026-10-25", "confidence": 1.0},
        "item_code": {"value": "E", "evidence": "E Carton box, 5-ply 3,000 piece 92.00 276,000.00", "confidence": 1.0},
        "description": {"value": "Carton box, 5-ply", "evidence": "Carton box, 5-ply", "confidence": 1.0},
        "quantity": {"value": 3000, "evidence": "3,000", "confidence": 1.0},
        "unit": {"value": "piece", "evidence": "piece", "confidence": 1.0},
        "unit_price": {"value": 92.0, "evidence": "92.00", "confidence": 1.0},
        "currency": {"value": "BDT", "evidence": "Unit price (BDT)", "confidence": 1.0},
        "line_amount": {"value": 276000.0, "evidence": "276,000.00", "confidence": 1.0},
        "subtotal": {"value": 276000.0, "evidence": "Subtotal 276,000.00", "confidence": 1.0},
        "vat_rate": {"value": 15.0, "evidence": "VAT 15%", "confidence": 1.0},
        "vat_amount": {"value": 41400.0, "evidence": "41,400.00", "confidence": 1.0},
        "total": {"value": 317400.0, "evidence": "Total 317,400.00", "confidence": 1.0},
        "advance_payment_pct": {"value": 0.4, "evidence": "40% advance payable with the purchase order.", "confidence": 1.0},
        "balance_payment_days": {"value": 30, "evidence": "within 30 days of delivery.", "confidence": 1.0},
        "payment_terms_text": {"value": "40% advance payable with the purchase order.", "evidence": "40% advance payable with the purchase order.", "confidence": 1.0},
        "delivery_days": {"value": 25, "evidence": "Delivery within 25 days of PO.", "confidence": 1.0},
        "late_penalty_clause_present": {"value": True, "evidence": "Late delivery penalty of 1% of order value per week.", "confidence": 1.0},
        "late_penalty_pct_per_week": {"value": 0.01, "evidence": "Late delivery penalty of 1% of order value per week.", "confidence": 1.0},
        "validity_days": {"value": 30, "evidence": "valid for 30 days from the date above.", "confidence": 1.0},
        "tin": {"value": "105458053391", "evidence": "Supplier TIN: 105458053391", "confidence": 1.0},
        "bin": {"value": "000570541-0101", "evidence": "BIN: 000570541-0101", "confidence": 1.0},
    }
    mock_llm(payload)
    graph = build_graph(DATA_DIR / "purchase-request.csv")
    state = {"doc_id": "supplier-pack-05", "file_path": str(DATA_DIR / "supplier-pack-05.pdf")}
    final = graph.invoke(state)
    assert final["decision"] == "Reject"
    assert any("Advance payment is more than 20%" in r for r in final["reasons"])
    assert final["extraction_status"] == "ok"
    # Reconciled value must be 40 (percent points), not 0.4 (fraction).
    assert final["extraction"]["advance_payment_pct"]["value"] == 40
