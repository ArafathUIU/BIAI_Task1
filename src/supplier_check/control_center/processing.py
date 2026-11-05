"""Invoke the existing LangGraph pipeline for one or more documents.

Does not duplicate extract/verify/rules/decide logic.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from supplier_check.graph import build_graph
from supplier_check.schemas import GraphState
from supplier_check.store import write_audit

from .workspace import (
    ROOT,
    DocumentMeta,
    get_meta,
    mark_processing,
    save_result,
)

ProgressCallback = Callable[[int, int, DocumentMeta, str], None]


def default_pr_path() -> Path:
    return ROOT / "data" / "purchase-request.csv"


def process_document(
    doc_uid: str,
    *,
    pr_path: Path | None = None,
    audit_dir: Path | None = None,
) -> DocumentMeta:
    """Process a single registered document through the existing graph."""
    meta = get_meta(doc_uid)
    if meta is None:
        raise FileNotFoundError(f"Unknown document: {doc_uid}")
    pdf = Path(meta.pdf_path)
    if not pdf.exists():
        meta = save_result(meta, None, error=f"PDF missing on disk: {pdf}")
        return meta

    mark_processing(doc_uid)
    meta = get_meta(doc_uid) or meta
    pr = pr_path or default_pr_path()
    if not pr.exists():
        return save_result(meta, None, error=f"Purchase request not found: {pr}")

    graph = build_graph(pr)
    try:
        state = GraphState(doc_id=meta.doc_uid, file_name=meta.file_name, file_path=str(pdf))
        final = graph.invoke(state.model_dump())
        final_state = GraphState.model_validate(final)
        # Prefer original filename in the persisted result.
        final_state.file_name = meta.file_name
        final_state.file_path = str(pdf)
        if audit_dir is not None:
            write_audit(audit_dir, final_state)
        return save_result(meta, final_state)
    except Exception as exc:  # noqa: BLE001 - one failure must not invent a Reject
        return save_result(meta, None, error=f"Pipeline error: {exc}")


def process_documents(
    doc_uids: list[str],
    *,
    pr_path: Path | None = None,
    audit_dir: Path | None = None,
    on_progress: ProgressCallback | None = None,
) -> list[DocumentMeta]:
    """Process selected documents sequentially; continue after individual failures."""
    results: list[DocumentMeta] = []
    total = len(doc_uids)
    for index, doc_uid in enumerate(doc_uids, start=1):
        meta = get_meta(doc_uid)
        if meta is None:
            continue
        if on_progress:
            on_progress(index, total, meta, "starting")
        updated = process_document(doc_uid, pr_path=pr_path, audit_dir=audit_dir)
        results.append(updated)
        if on_progress:
            status = "failed" if updated.processing_status == "failed" else "done"
            on_progress(index, total, updated, status)
    return results
