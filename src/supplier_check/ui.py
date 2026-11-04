"""Streamlit demo UI for the supplier document checker."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from supplier_check.graph import build_graph
from supplier_check.schemas import GraphState
from supplier_check.store import write_audit


def _run_batch(input_dir: Path) -> tuple[Path, list[GraphState]]:
    pr_path = input_dir / "purchase-request.csv"
    graph = build_graph(pr_path)
    run_dir = Path("runs") / datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    states: list[GraphState] = []
    pdfs = sorted(input_dir.glob("supplier-pack-*.pdf"))
    progress = st.progress(0.0, text="Starting...")
    for i, pdf in enumerate(pdfs, start=1):
        try:
            state = GraphState(doc_id=pdf.stem, file_path=str(pdf))
            final = graph.invoke(state.model_dump())
            final_state = GraphState.model_validate(final)
        except Exception as exc:  # noqa: BLE001 - keep the batch running
            final_state = GraphState(
                doc_id=pdf.stem,
                file_name=pdf.name,
                file_path=str(pdf),
                decision="Needs a person to check",
                reasons=[f"Pipeline error while processing document: {exc}"],
                human_review_required=True,
                extraction_status="needs_human",
                extraction_issues=[str(exc)],
            )
        write_audit(run_dir, final_state)
        states.append(final_state)
        progress.progress(i / len(pdfs), text=f"Processed {pdf.name}")
    progress.empty()
    return run_dir, states


def _results_frame(states: list[GraphState]) -> list[dict]:
    rows = []
    for s in states:
        supplier = None
        item = None
        if s.extraction is not None:
            supplier = s.extraction.supplier_name.value
            item = s.extraction.item_code.value
        rows.append(
            {
                "Document": s.doc_id,
                "Supplier": supplier,
                "Item": item,
                "Qty diff %": None if s.qty_diff_pct is None else round(s.qty_diff_pct, 2),
                "Price diff %": None if s.price_diff_pct is None else round(s.price_diff_pct, 2),
                "Decision": s.decision,
                "Reason": (s.reasons[0] if s.reasons else ""),
            }
        )
    return rows


def _field_table(state: GraphState) -> list[dict]:
    if state.extraction is None:
        return []
    rows = []
    for name, field in state.extraction.model_dump().items():
        rows.append(
            {
                "Field": name,
                "Value": field.get("value"),
                "Confidence": field.get("confidence"),
                "Evidence": field.get("evidence"),
            }
        )
    return rows


def main() -> None:
    st.set_page_config(page_title="Supplier Document Checker", layout="wide")
    st.title("Supplier Document Checker")
    st.caption("Fixed-step LangGraph pipeline. LLM extracts; Python rules decide.")

    if "states" not in st.session_state:
        st.session_state["states"] = []
        st.session_state["run_dir"] = None

    with st.sidebar:
        st.header("Run")
        input_dir = st.text_input("Input folder", value="data")
        if st.button("Run batch", type="primary"):
            path = Path(input_dir)
            if not path.exists():
                st.error(f"Folder not found: {path}")
            elif not list(path.glob("supplier-pack-*.pdf")):
                st.error("No supplier-pack-*.pdf files found in that folder.")
            else:
                run_dir, states = _run_batch(path)
                st.session_state["states"] = states
                st.session_state["run_dir"] = str(run_dir)
                st.success(f"Processed {len(states)} documents. Audit: {run_dir}")

    states: list[GraphState] = st.session_state["states"]
    if not states:
        st.info("Run a batch to see results.")
        return

    st.subheader("Results")
    df = _results_frame(states)
    st.table(df)

    st.subheader("Detail / evidence")
    selected = st.selectbox("Document", [s.doc_id for s in states])
    state = next(s for s in states if s.doc_id == selected)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Decision:** {state.decision}")
        st.markdown("**Reasons:**")
        for r in state.reasons:
            st.write(f"- {r}")
        if state.evidence:
            st.markdown("**Evidence quotes:**")
            for e in state.evidence:
                st.code(e)
        if state.rule_result is not None:
            st.markdown("**Rule hits:**")
            st.write(", ".join(state.rule_result.rule_hits) or "none")
        st.markdown(f"**Extraction status:** {state.extraction_status}")
        if state.extraction_issues:
            st.markdown("**Extraction issues:**")
            for i in state.extraction_issues:
                st.write(f"- {i}")
        if state.human_review_required:
            st.warning("Needs a person to check.")

    with col2:
        st.markdown("**Extracted fields:**")
        ft = _field_table(state)
        if not ft.empty:
            st.table(ft)

    with st.expander("Raw document text"):
        st.text(state.raw_text)

    # Optional review queue
    needs = [s for s in states if s.decision == "Needs a person to check"]
    if needs:
        st.subheader("Review queue")
        st.write(f"{len(needs)} document(s) need a person to check.")
        for s in needs:
            st.write(f"- {s.doc_id}: {s.reasons[0] if s.reasons else ''}")


if __name__ == "__main__":
    main()
