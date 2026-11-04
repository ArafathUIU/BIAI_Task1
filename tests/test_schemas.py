from supplier_check.schemas import FieldExtraction, GraphState, QuotationExtraction


def test_field_extraction_defaults() -> None:
    f = FieldExtraction()
    assert f.value is None
    assert f.confidence == 0.0


def test_quotation_extraction_requires_all_fields() -> None:
    payload = {name: {"value": None, "evidence": None, "confidence": 0.0} for name in QuotationExtraction.model_fields}
    q = QuotationExtraction.model_validate(payload)
    assert q.supplier_name.value is None


def test_graph_state_defaults() -> None:
    s = GraphState(doc_id="x")
    assert s.extraction_status == "needs_human"
    assert s.ingestion_ok is False
