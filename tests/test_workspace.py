"""Live workspace persistence helpers."""

from __future__ import annotations

from pathlib import Path

from supplier_check.control_center.workspace import (
    get_meta,
    load_result,
    make_doc_uid,
    register_upload,
    save_result,
)
from supplier_check.schemas import GraphState


def test_register_upload_and_persist_result(tmp_path, monkeypatch) -> None:
    import supplier_check.control_center.workspace as ws

    monkeypatch.setattr(ws, "WORKSPACE", tmp_path / "workspace")
    monkeypatch.setattr(ws, "LIVE_DIR", tmp_path / "workspace" / "live")
    monkeypatch.setattr(ws, "LIVE_DOCS", tmp_path / "workspace" / "live" / "docs")
    monkeypatch.setattr(ws, "LIVE_INDEX", tmp_path / "workspace" / "live" / "index.json")
    monkeypatch.setattr(ws, "EVAL_DIR", tmp_path / "workspace" / "evaluation")
    monkeypatch.setattr(ws, "EVAL_LAST", tmp_path / "workspace" / "evaluation" / "last_run.json")

    content = b"%PDF-1.4 fake content for test"
    meta = register_upload("quote-a.pdf", content)
    assert meta.processing_status == "uploaded"
    assert meta.decision is None
    assert Path(meta.pdf_path).exists()
    assert make_doc_uid("quote-a.pdf", content) == meta.doc_uid

    # Same bytes => same uid, keep registry stable.
    meta2 = register_upload("quote-a.pdf", content)
    assert meta2.doc_uid == meta.doc_uid

    state = GraphState(
        doc_id=meta.doc_uid,
        file_name="quote-a.pdf",
        decision="Reject",
        reasons=["Advance payment is more than 20%."],
        extraction_status="ok",
        human_review_required=False,
    )
    saved = save_result(meta, state)
    assert saved.processing_status == "processed"
    assert saved.decision == "Reject"
    loaded = load_result(meta.doc_uid)
    assert loaded is not None
    assert loaded.decision == "Reject"
    assert get_meta(meta.doc_uid) is not None


def test_failed_processing_is_not_a_decision(tmp_path, monkeypatch) -> None:
    import supplier_check.control_center.workspace as ws

    monkeypatch.setattr(ws, "WORKSPACE", tmp_path / "workspace")
    monkeypatch.setattr(ws, "LIVE_DIR", tmp_path / "workspace" / "live")
    monkeypatch.setattr(ws, "LIVE_DOCS", tmp_path / "workspace" / "live" / "docs")
    monkeypatch.setattr(ws, "LIVE_INDEX", tmp_path / "workspace" / "live" / "index.json")
    monkeypatch.setattr(ws, "EVAL_DIR", tmp_path / "workspace" / "evaluation")
    monkeypatch.setattr(ws, "EVAL_LAST", tmp_path / "workspace" / "evaluation" / "last_run.json")

    meta = register_upload("bad.pdf", b"%PDF-1.4 x")
    failed = save_result(meta, None, error="Pipeline error: boom")
    assert failed.processing_status == "failed"
    assert failed.decision is None
    assert failed.error is not None
