"""PDF ingestion and text extraction."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pdfplumber
from pypdf import PdfReader

from .schemas import GraphState


def normalize_text(text: str) -> str:
    """Collapse all whitespace runs to a single space."""
    return " ".join(text.split())


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _extract_with_pdfplumber(path: Path) -> str:
    pages: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    return "\n".join(pages)


def _extract_with_pypdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages: list[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)


def extract_text_from_pdf(path: Path) -> str:
    """Extract text using pdfplumber, falling back to pypdf on failure/empty."""
    path = Path(path)
    text = ""
    try:
        text = _extract_with_pdfplumber(path)
    except Exception:  # noqa: BLE001 - fallback extractor must not crash ingestion
        text = ""
    if normalize_text(text):
        return text
    try:
        text = _extract_with_pypdf(path)
    except Exception:  # noqa: BLE001 - fallback extractor must not crash ingestion
        text = ""
    return text


def ingest_pdf(path: Path) -> GraphState:
    """Read a PDF into a GraphState with raw text, hash, and ingestion status."""
    path = Path(path)
    text = extract_text_from_pdf(path)
    normalized = normalize_text(text)
    issues: list[str] = []
    if not normalized:
        issues.append("No text could be extracted from the PDF.")
    elif len(normalized) < 50:
        issues.append("Extracted text is very short; document may be scanned or empty.")

    return GraphState(
        doc_id=path.stem,
        file_name=path.name,
        raw_text=text,
        text_hash=sha256_file(path),
        ingestion_ok=not issues,
        ingestion_issues=issues,
    )
