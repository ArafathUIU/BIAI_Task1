import json

from supplier_check.extract import (
    build_messages,
    extract_quotation,
    parse_extraction,
)
from supplier_check.ingest import ingest_pdf
from supplier_check.schemas import GraphState

DATA_DIR = __import__("pathlib").Path(__file__).resolve().parents[1] / "data"


def _valid_payload() -> dict:
    return {
        name: {"value": None, "evidence": None, "confidence": 0.0}
        for name in __import__("supplier_check.schemas", fromlist=["QuotationExtraction"]).QuotationExtraction.model_fields
    }


def test_parse_valid_payload() -> None:
    payload = _valid_payload()
    payload["supplier_name"] = {"value": "Padma Textile Mills Ltd", "evidence": "Padma Textile Mills Ltd", "confidence": 0.9}
    extraction, issues = parse_extraction(payload)
    assert issues == []
    assert extraction is not None
    assert extraction.supplier_name.value == "Padma Textile Mills Ltd"


def test_parse_invalid_json() -> None:
    extraction, issues = parse_extraction("{not json")
    assert extraction is None
    assert issues and "not valid JSON" in issues[0]


def test_parse_schema_failure() -> None:
    extraction, issues = parse_extraction({"supplier_name": "bad"})
    assert extraction is None
    assert issues and "Schema validation failed" in issues[0]


def test_build_messages_includes_document_text() -> None:
    msgs = build_messages("hello document")
    assert msgs[0]["role"] == "system"
    assert "hello document" in msgs[1]["content"]


def test_extract_quotation_node_with_mocked_llm(monkeypatch) -> None:
    state = ingest_pdf(DATA_DIR / "supplier-pack-01.pdf")
    payload = _valid_payload()
    monkeypatch.setattr(
        "supplier_check.extract.call_llm",
        lambda messages, client=None, model=None: json.dumps(payload),
    )
    result = extract_quotation(state)
    assert result.extraction_status == "ok"
    assert result.extraction is not None


def test_extract_quotation_node_llm_failure(monkeypatch) -> None:
    state = ingest_pdf(DATA_DIR / "supplier-pack-01.pdf")

    def boom(messages, client=None, model=None):
        raise RuntimeError("no key")

    monkeypatch.setattr("supplier_check.extract.call_llm", boom)
    result = extract_quotation(state)
    assert result.extraction_status == "needs_human"
    assert any("LLM call failed" in i for i in result.extraction_issues)


def test_extract_quotation_node_ingestion_failure() -> None:
    state = GraphState(doc_id="x", ingestion_ok=False, raw_text="")
    result = extract_quotation(state)
    assert result.extraction_status == "needs_human"
