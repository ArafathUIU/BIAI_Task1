from pathlib import Path

from supplier_check.ingest import extract_text_from_pdf, ingest_pdf, normalize_text

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def test_pack_01_text_non_empty() -> None:
    text = extract_text_from_pdf(DATA_DIR / "supplier-pack-01.pdf")
    assert normalize_text(text)


def test_pack_01_ingestion_ok() -> None:
    state = ingest_pdf(DATA_DIR / "supplier-pack-01.pdf")
    assert state.ingestion_ok is True
    assert state.raw_text.strip()
    assert state.text_hash


def test_pack_01_evidence_substring_preview() -> None:
    # Preview of the Phase 4 evidence check: a quote must be a substring.
    state = ingest_pdf(DATA_DIR / "supplier-pack-01.pdf")
    assert "Padma Textile Mills Ltd" in normalize_text(state.raw_text)
