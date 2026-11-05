"""Persistent live-document workspace (not session-only).

Layout::

    workspace/
      live/
        index.json
        docs/<doc_uid>/
          meta.json
          source.pdf
          result.json   # full GraphState when processed
      evaluation/
        last_run.json
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from supplier_check.schemas import GraphState

ROOT = Path(__file__).resolve().parents[3]
WORKSPACE = ROOT / "workspace"
LIVE_DIR = WORKSPACE / "live"
LIVE_DOCS = LIVE_DIR / "docs"
LIVE_INDEX = LIVE_DIR / "index.json"
EVAL_DIR = WORKSPACE / "evaluation"
EVAL_LAST = EVAL_DIR / "last_run.json"

ProcessingStatus = Literal["uploaded", "processing", "processed", "failed"]
DecisionLiteral = Literal["Approve", "Reject", "Needs a person to check"]


class DocumentMeta(BaseModel):
    """Registry row for one live (or evaluation-copied) document."""

    doc_uid: str
    file_name: str
    pdf_path: str
    text_hash: str | None = None
    processing_status: ProcessingStatus = "uploaded"
    decision: DecisionLiteral | None = None
    human_review_required: bool = False
    extraction_status: str | None = None
    supplier_name: str | None = None
    error: str | None = None
    created_at: str
    processed_at: str | None = None
    source: Literal["live", "evaluation"] = "live"


def ensure_workspace() -> None:
    LIVE_DOCS.mkdir(parents=True, exist_ok=True)
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    if not LIVE_INDEX.exists():
        payload = {
            "updated_at": datetime.now(UTC).isoformat(),
            "documents": [],
        }
        LIVE_INDEX.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )


def _write_index(docs: list[DocumentMeta]) -> None:
    LIVE_DOCS.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now(UTC).isoformat(),
        "documents": [d.model_dump() for d in docs],
    }
    LIVE_INDEX.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def load_index() -> list[DocumentMeta]:
    ensure_workspace()
    if not LIVE_INDEX.exists():
        return []
    try:
        data = json.loads(LIVE_INDEX.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    docs: list[DocumentMeta] = []
    for row in data.get("documents", []):
        try:
            docs.append(DocumentMeta.model_validate(row))
        except Exception:  # noqa: BLE001,S112 - skip corrupt index rows
            continue
    return docs


def get_meta(doc_uid: str) -> DocumentMeta | None:
    for doc in load_index():
        if doc.doc_uid == doc_uid:
            return doc
    return None


def upsert_meta(meta: DocumentMeta) -> DocumentMeta:
    docs = [d for d in load_index() if d.doc_uid != meta.doc_uid]
    docs.append(meta)
    docs.sort(key=lambda d: d.created_at, reverse=True)
    _write_index(docs)
    return meta


def doc_dir(doc_uid: str) -> Path:
    return LIVE_DOCS / doc_uid


def result_path(doc_uid: str) -> Path:
    return doc_dir(doc_uid) / "result.json"


def pdf_path_for(doc_uid: str) -> Path:
    return doc_dir(doc_uid) / "source.pdf"


def _safe_stem(name: str) -> str:
    stem = Path(name).stem
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._") or "document"
    return cleaned[:80]


def make_doc_uid(file_name: str, content: bytes) -> str:
    digest = hashlib.sha256(content).hexdigest()[:12]
    return f"{_safe_stem(file_name)}__{digest}"


def register_upload(file_name: str, content: bytes, *, source: Literal["live", "evaluation"] = "live") -> DocumentMeta:
    """Save PDF bytes and register as uploaded (or refresh existing content-identical doc)."""
    ensure_workspace()
    if not file_name.lower().endswith(".pdf"):
        raise ValueError("Only PDF files are supported.")
    if not content:
        raise ValueError("Uploaded file is empty.")
    doc_uid = make_doc_uid(file_name, content)
    existing = get_meta(doc_uid)
    target = doc_dir(doc_uid)
    target.mkdir(parents=True, exist_ok=True)
    pdf = target / "source.pdf"
    pdf.write_bytes(content)
    meta_path = target / "meta.json"
    now = datetime.now(UTC).isoformat()
    if existing and existing.processing_status == "processed" and result_path(doc_uid).exists():
        # Same content already processed - keep results, refresh path/name.
        existing.file_name = file_name
        existing.pdf_path = str(pdf)
        upsert_meta(existing)
        meta_path.write_text(existing.model_dump_json(indent=2), encoding="utf-8")
        return existing

    meta = DocumentMeta(
        doc_uid=doc_uid,
        file_name=file_name,
        pdf_path=str(pdf),
        processing_status="uploaded",
        decision=None,
        human_review_required=False,
        created_at=existing.created_at if existing else now,
        processed_at=None,
        source=source,
        error=None,
    )
    # Drop stale result if re-uploading same uid after failure/upload.
    if result_path(doc_uid).exists() and (existing is None or existing.processing_status != "processed"):
        result_path(doc_uid).unlink(missing_ok=True)
    meta_path.write_text(meta.model_dump_json(indent=2), encoding="utf-8")
    upsert_meta(meta)
    return meta


def save_result(meta: DocumentMeta, state: GraphState | None, *, error: str | None = None) -> DocumentMeta:
    """Persist processing outcome and update index."""
    ensure_workspace()
    folder = doc_dir(meta.doc_uid)
    folder.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC).isoformat()
    meta.processed_at = now
    meta.error = error
    if error:
        meta.processing_status = "failed"
        meta.decision = None
        meta.human_review_required = True
        meta.extraction_status = "needs_human"
    elif state is not None:
        result_path(meta.doc_uid).write_text(
            state.model_dump_json(indent=2), encoding="utf-8"
        )
        meta.processing_status = "processed"
        meta.decision = state.decision
        meta.human_review_required = bool(state.human_review_required)
        meta.extraction_status = state.extraction_status
        meta.text_hash = state.text_hash or meta.text_hash
        if state.extraction and state.extraction.supplier_name.value is not None:
            meta.supplier_name = str(state.extraction.supplier_name.value)
        meta.error = None
    else:
        meta.processing_status = "failed"
        meta.decision = None
        meta.error = meta.error or "No result produced."
    (folder / "meta.json").write_text(meta.model_dump_json(indent=2), encoding="utf-8")
    return upsert_meta(meta)


def mark_processing(doc_uid: str) -> DocumentMeta | None:
    meta = get_meta(doc_uid)
    if meta is None:
        return None
    meta.processing_status = "processing"
    meta.error = None
    return upsert_meta(meta)


def load_result(doc_uid: str) -> GraphState | None:
    path = result_path(doc_uid)
    if not path.exists():
        return None
    try:
        return GraphState.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def delete_document(doc_uid: str) -> None:
    folder = doc_dir(doc_uid)
    if folder.exists():
        shutil.rmtree(folder, ignore_errors=True)
    docs = [d for d in load_index() if d.doc_uid != doc_uid]
    _write_index(docs)


def live_documents(*, processed_only: bool = False) -> list[DocumentMeta]:
    docs = [d for d in load_index() if d.source == "live"]
    if processed_only:
        return [d for d in docs if d.processing_status == "processed" and d.decision]
    return docs


def count_decisions(docs: list[DocumentMeta]) -> dict[str, int]:
    counts = {"Approve": 0, "Reject": 0, "Needs a person to check": 0, "total_processed": 0}
    for d in docs:
        if d.processing_status != "processed" or not d.decision:
            continue
        counts["total_processed"] += 1
        if d.decision in counts:
            counts[d.decision] += 1
    return counts


def save_evaluation_run(payload: dict[str, Any]) -> Path:
    ensure_workspace()
    EVAL_LAST.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return EVAL_LAST


def load_evaluation_run() -> dict[str, Any] | None:
    if not EVAL_LAST.exists():
        return None
    try:
        return json.loads(EVAL_LAST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


class EvaluationRow(BaseModel):
    doc_id: str
    file_name: str
    expected: str
    actual: str | None
    result: Literal["Correct", "Incorrect", "Failed", "Not Evaluated"]
    reasons: list[str] = Field(default_factory=list)
