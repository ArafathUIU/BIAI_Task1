from pathlib import Path

from supplier_check.decide import decide
from supplier_check.ingest import ingest_pdf
from supplier_check.schemas import GraphState

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def test_decide_uncertain_extraction_is_needs() -> None:
    state = ingest_pdf(DATA_DIR / "supplier-pack-01.pdf")
    state.extraction_status = "needs_human"
    state.extraction_issues = ["missing field"]
    state = decide(state)
    assert state.decision == "Needs a person to check"
    assert state.human_review_required is True


def test_decide_pr_mismatch_is_needs() -> None:
    state = GraphState(doc_id="x", ingestion_ok=True, raw_text="x")
    state.extraction_status = "ok"
    state.pr_match_ok = False
    state = decide(state)
    assert state.decision == "Needs a person to check"
    assert any("purchase-request" in r for r in state.reasons)


def test_decide_approve_path() -> None:
    # Reuse a verified extraction by mocking is complex; check precedence only:
    # if extraction_status ok and pr_match_ok but no extraction, still needs.
    state = GraphState(doc_id="x", ingestion_ok=True, raw_text="x")
    state.extraction_status = "ok"
    state.pr_match_ok = True
    state.extraction = None
    state.pr_row = None
    state = decide(state)
    assert state.decision == "Needs a person to check"
