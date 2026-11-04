"""Streamlit demo UI for the supplier document checker.

Do not use pandas / ``st.table`` / ``st.dataframe``. On some Windows machines
Application Control blocks pandas native DLLs and those APIs crash the app.
"""

from __future__ import annotations

import html
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

DECISION_STYLE = {
    "Approve": {"bg": "#E8F5EE", "fg": "#146C43", "border": "#A6D5B8"},
    "Reject": {"bg": "#FDECEC", "fg": "#B42318", "border": "#F0B4B0"},
    "Needs a person to check": {"bg": "#FFF4E5", "fg": "#B54708", "border": "#F5D0A9"},
}


def _resolve_path(path_str: str) -> Path:
    """Resolve relative paths against the project root, not the process cwd."""
    path = Path(path_str).expanduser()
    if not path.is_absolute():
        path = _ROOT / path
    return path.resolve()


def _run_batch(input_dir: Path) -> tuple[Path, list[GraphState]]:
    pr_path = input_dir / "purchase-request.csv"
    graph = build_graph(pr_path)
    run_dir = _ROOT / "runs" / datetime.now().strftime("%Y%m%d-%H%M%S")
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
        progress.progress(i / max(len(pdfs), 1), text=f"Processed {pdf.name}")
    progress.empty()
    return run_dir, states


def _supplier(state: GraphState) -> str:
    if state.extraction is None or state.extraction.supplier_name.value is None:
        return ""
    return str(state.extraction.supplier_name.value)


def _item(state: GraphState) -> str:
    if state.extraction is None or state.extraction.item_code.value is None:
        return ""
    return str(state.extraction.item_code.value)


def _primary_reason(state: GraphState) -> str:
    """Show the decision reason; only surface extract errors when extract failed."""
    if state.extraction_status != "ok":
        for issue in state.extraction_issues:
            text = issue.strip()
            if not text or text.startswith(("Cleared unverified", "Note:", "Low confidence")):
                continue
            return text if len(text) <= 160 else text[:157] + "..."
    if state.reasons:
        return state.reasons[0]
    return ""


def _results_rows(states: list[GraphState]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for s in states:
        rows.append(
            {
                "Document": s.doc_id,
                "Supplier": _supplier(s),
                "Item": _item(s),
                "Qty %": "" if s.qty_diff_pct is None else f"{s.qty_diff_pct:+.1f}",
                "Price %": "" if s.price_diff_pct is None else f"{s.price_diff_pct:+.1f}",
                "Decision": s.decision or "",
                "Primary reason": _primary_reason(s),
            }
        )
    return rows


def _field_rows(state: GraphState, *, filled_only: bool = True) -> list[dict[str, str]]:
    if state.extraction is None:
        return []
    rows: list[dict[str, str]] = []
    for name, field in state.extraction.model_dump().items():
        value = field.get("value")
        if filled_only and value is None:
            continue
        conf = field.get("confidence")
        evidence = field.get("evidence")
        rows.append(
            {
                "Field": name,
                "Value": "" if value is None else str(value),
                "Conf.": "" if conf is None else f"{float(conf):.2f}",
                "Evidence": "" if evidence is None else str(evidence),
            }
        )
    return rows


def _counts(states: list[GraphState]) -> dict[str, int]:
    counts = {"Approve": 0, "Reject": 0, "Needs a person to check": 0}
    for s in states:
        if s.decision in counts:
            counts[s.decision] += 1
    return counts


def decision_badge_html(decision: str | None) -> str:
    label = decision or "Unknown"
    style = DECISION_STYLE.get(
        label, {"bg": "#F4F4F5", "fg": "#3F3F46", "border": "#D4D4D8"}
    )
    return (
        f"<span style='display:inline-block;padding:0.25rem 0.7rem;"
        f"background:{style['bg']};color:{style['fg']};"
        f"border:1px solid {style['border']};font-weight:600;"
        f"font-size:0.92rem'>{html.escape(label)}</span>"
    )


def render_html_table(rows: list[dict[str, str]], *, decision_col: str | None = None) -> str:
    """Build a compact HTML table without pandas."""
    if not rows:
        return "<p><em>No rows.</em></p>"
    cols = list(rows[0].keys())
    head = "".join(
        f"<th style='text-align:left;padding:0.55rem 0.65rem;border-bottom:1px solid #D4D4D8;"
        f"color:#52525B;font-size:0.8rem;font-weight:600'>{html.escape(c)}</th>"
        for c in cols
    )
    body_parts: list[str] = []
    for row in rows:
        cells: list[str] = []
        for c in cols:
            raw = str(row.get(c, ""))
            if decision_col and c == decision_col:
                cells.append(
                    f"<td style='padding:0.55rem 0.65rem;border-bottom:1px solid #EEE;'>"
                    f"{decision_badge_html(raw)}</td>"
                )
            else:
                cells.append(
                    f"<td style='padding:0.55rem 0.65rem;border-bottom:1px solid #EEE;"
                    f"vertical-align:top;font-size:0.9rem'>{html.escape(raw)}</td>"
                )
        body_parts.append(f"<tr>{''.join(cells)}</tr>")
    return (
        "<div style='overflow-x:auto;border:1px solid #E4E4E7;background:#fff'>"
        "<table style='width:100%;border-collapse:collapse'>"
        f"<thead><tr style='background:#FAFAFA'>{head}</tr></thead>"
        f"<tbody>{''.join(body_parts)}</tbody>"
        "</table></div>"
    )


def render_markdown_table(rows: list[dict[str, str]]) -> str:
    """Markdown fallback helper (kept for tests / no-HTML contexts)."""
    if not rows:
        return "_No rows._"
    cols = list(rows[0].keys())

    def cell(value: str) -> str:
        return (
            value.replace("\\", "\\\\")
            .replace("|", "\\|")
            .replace("\n", " ")
            .replace("\r", " ")
        )

    header = "| " + " | ".join(cell(c) for c in cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    body = [
        "| " + " | ".join(cell(str(row.get(c, ""))) for c in cols) + " |" for row in rows
    ]
    return "\n".join([header, sep, *body])


def _inject_style() -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.4rem; max-width: 1200px; }
        div[data-testid="stMetricValue"] { font-size: 1.6rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="Supplier Document Checker",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_style()

    st.title("Supplier Document Checker")
    st.caption(
        "Aamar Garments · fixed-step review pipeline · "
        "LLM extracts fields · Python rules decide · never guesses"
    )

    if "states" not in st.session_state:
        st.session_state["states"] = []
        st.session_state["run_dir"] = None

    with st.sidebar:
        st.header("Run batch")
        st.write("Pipeline: ingest → extract → verify → compare PR → apply rules")
        input_dir = st.text_input("Sample folder", value="data")
        run_clicked = st.button("Run all packs", type="primary", use_container_width=True)
        if run_clicked:
            path = _resolve_path(input_dir)
            if not path.exists():
                st.error(f"Folder not found: {path}")
            elif not list(path.glob("supplier-pack-*.pdf")):
                st.error("No supplier-pack-*.pdf files found in that folder.")
            else:
                with st.spinner("Checking supplier packs..."):
                    run_dir, states = _run_batch(path)
                st.session_state["states"] = states
                st.session_state["run_dir"] = str(run_dir)
                st.success(f"Done · {len(states)} docs · audit saved")

        if st.session_state.get("run_dir"):
            st.caption(f"Audit\n`{st.session_state['run_dir']}`")

        st.divider()
        st.markdown(
            "**Decisions**\n\n"
            "- **Approve** — all rules pass\n"
            "- **Reject** — hard policy breach\n"
            "- **Needs a person** — uncertain or soft breach"
        )

    states: list[GraphState] = st.session_state["states"]
    if not states:
        st.info("Use the sidebar to run the sample packs, then review decisions and evidence here.")
        st.markdown(
            """
**What this demo shows**
1. Extract commercial fields from each supplier PDF  
2. Ground every field with an exact quote from the document  
3. Compare against the purchase request  
4. Apply company rules in fixed order — no free-running agent  
"""
        )
        return

    counts = _counts(states)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Documents", len(states))
    m2.metric("Approve", counts["Approve"])
    m3.metric("Reject", counts["Reject"])
    m4.metric("Needs person", counts["Needs a person to check"])

    filter_options = ["All", "Approve", "Reject", "Needs a person to check"]
    chosen_filter = st.radio(
        "Filter results",
        filter_options,
        horizontal=True,
        label_visibility="collapsed",
    )
    filtered = [
        s
        for s in states
        if chosen_filter == "All" or s.decision == chosen_filter
    ]

    st.subheader("Results")
    st.markdown(
        render_html_table(_results_rows(filtered), decision_col="Decision"),
        unsafe_allow_html=True,
    )

    st.subheader("Document detail")
    labels = {
        s.doc_id: f"{s.doc_id} · {s.decision or '—'} · {_supplier(s) or 'unknown supplier'}"
        for s in states
    }
    selected = st.selectbox(
        "Choose a document",
        options=list(labels.keys()),
        format_func=lambda key: labels[key],
    )
    state = next(s for s in states if s.doc_id == selected)

    st.markdown(decision_badge_html(state.decision), unsafe_allow_html=True)
    st.write("")

    left, right = st.columns([1.05, 1.2], gap="large")
    with left:
        st.markdown("##### Why this decision")
        for r in state.reasons:
            st.markdown(f"- {r}")
        if state.evidence:
            st.markdown("##### Supporting quotes")
            for e in state.evidence:
                st.code(e, language=None)
        if state.rule_result is not None and state.rule_result.rule_hits:
            st.markdown("##### Rule hits")
            st.caption(", ".join(state.rule_result.rule_hits))

        meta = [
            f"Extraction: `{state.extraction_status}`",
            f"PR match: `{'yes' if state.pr_match_ok else 'no'}`",
            f"Human review: `{'required' if state.human_review_required else 'not required'}`",
        ]
        if state.qty_diff_pct is not None:
            meta.append(f"Qty diff: `{state.qty_diff_pct:+.2f}%`")
        if state.price_over_max_pct is not None:
            meta.append(f"Price over max: `{state.price_over_max_pct:+.2f}%`")
        st.markdown(" · ".join(meta))

        if state.extraction_issues:
            with st.expander("Extraction / verification notes"):
                for issue in state.extraction_issues:
                    st.write(f"- {issue}")

    with right:
        st.markdown("##### Extracted fields")
        show_all = st.toggle("Show empty fields", value=False)
        st.markdown(
            render_html_table(_field_rows(state, filled_only=not show_all)),
            unsafe_allow_html=True,
        )

    with st.expander("Raw PDF text", expanded=False):
        st.text(state.raw_text or "(empty)")

    needs = [s for s in states if s.decision == "Needs a person to check"]
    if needs:
        st.subheader("Review queue")
        st.caption(f"{len(needs)} document(s) waiting for a person.")
        for s in needs:
            reason = s.reasons[0] if s.reasons else "No reason recorded"
            st.markdown(
                f"- **{s.doc_id}** · {_supplier(s) or '—'} — {reason}"
            )


if __name__ == "__main__":
    main()
