"""Assignment Evaluation - independent golden labels for the 10 sample packs."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import streamlit as st

from supplier_check.control_center.components import render_html_table
from supplier_check.control_center.workspace import (
    ROOT,
    load_evaluation_run,
    save_evaluation_run,
)
from supplier_check.graph import build_graph
from supplier_check.schemas import GraphState
from supplier_check.store import write_audit

DATA_DIR = ROOT / "data"
EXPECTED_PATH = ROOT / "tests" / "fixtures" / "expected.json"


def render() -> None:
    st.markdown('<div class="sv-section-title">Assignment Evaluation</div>', unsafe_allow_html=True)
    st.caption(
        "Independent assessment against the locked golden dataset for the ten sample PDFs. "
        "Live uploads are never added to this dataset. Decision accuracy uses expected labels, "
        "not the system's own prior outputs."
    )

    expected = _load_expected()
    if expected is None:
        st.error("Golden fixture missing: tests/fixtures/expected.json")
        return

    decisions = expected.get("decisions", {})
    last = load_evaluation_run()

    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown('<div class="sv-card">', unsafe_allow_html=True)
        st.markdown("**Evaluation modes**")
        st.markdown(
            "- **Live end-to-end extraction evaluation** - run the full pipeline on the 10 sample PDFs "
            "(uses LLM; subject to provider limits).\n"
            "- **Field-level extraction accuracy** - Not Evaluated (no independent per-field ground-truth "
            "file is published beyond golden decisions).\n"
            "- **Evidence verification statistics** - Not Available as an aggregate metric in this build."
        )
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        run = st.button("Run live evaluation (10 packs)", type="primary", use_container_width=True)

    if run:
        _run_live_evaluation(decisions)

    last = load_evaluation_run()
    if not last:
        st.info("No evaluation run stored yet.")
        return

    rows = last.get("rows", [])
    correct = sum(1 for r in rows if r.get("result") == "Correct")
    incorrect = sum(1 for r in rows if r.get("result") == "Incorrect")
    failed = sum(1 for r in rows if r.get("result") == "Failed")
    evaluated = correct + incorrect
    accuracy = f"{(100.0 * correct / evaluated):.1f}%" if evaluated else "Not Evaluated"
    needs = sum(
        1
        for r in rows
        if r.get("actual") == "Needs a person to check" or r.get("result") == "Failed"
    )

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Evaluated docs", len(rows))
    m2.metric("Correct decisions", correct)
    m3.metric("Incorrect decisions", incorrect)
    m4.metric("Decision accuracy", accuracy)
    m5.metric("Needs / failed", needs)

    st.caption(f"Completed at: `{last.get('completed_at', 'Not Available')}`")
    st.caption(f"Failed pipeline runs: {failed}")
    st.caption("Field-level extraction accuracy: Not Evaluated")
    st.caption("Evidence verification aggregate: Not Available")

    table_rows = []
    for r in rows:
        result = r.get("result", "Not Evaluated")
        badge = {
            "Correct": '<span class="sv-badge approve">Correct</span>',
            "Incorrect": '<span class="sv-badge reject">Incorrect</span>',
            "Failed": '<span class="sv-badge failed">Failed</span>',
        }.get(result, '<span class="sv-badge neutral">Not Evaluated</span>')
        table_rows.append(
            {
                "Document": r.get("file_name") or r.get("doc_id", ""),
                "Expected Decision": r.get("expected", ""),
                "Actual Decision": r.get("actual") or "-",
                "Result": badge,
            }
        )
    st.markdown(render_html_table(table_rows), unsafe_allow_html=True)

    with st.expander("Per-document reasons"):
        for r in rows:
            st.markdown(
                f"**{r.get('file_name')}** - expected `{r.get('expected')}` / "
                f"actual `{r.get('actual')}` / {r.get('result')}"
            )
            for reason in r.get("reasons") or []:
                st.write(f"- {reason}")


def _load_expected() -> dict | None:
    if not EXPECTED_PATH.exists():
        return None
    return json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))


def _run_live_evaluation(decisions: dict[str, str]) -> None:
    pdfs = sorted(DATA_DIR.glob("supplier-pack-*.pdf"))
    if not pdfs:
        st.error("No supplier-pack-*.pdf files found in data/.")
        return

    progress = st.progress(0.0, text="Running evaluation...")
    audit_dir = ROOT / "runs" / f"eval-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"
    audit_dir.mkdir(parents=True, exist_ok=True)
    pr_path = DATA_DIR / "purchase-request.csv"
    graph = build_graph(pr_path)
    rows: list[dict] = []

    for i, pdf in enumerate(pdfs, start=1):
        progress.progress(i / len(pdfs), text=f"Evaluating {pdf.name}")
        doc_id = pdf.stem
        expected = decisions.get(doc_id, "")
        try:
            # Keep evaluation PDFs out of the live index by running graph directly.
            state = GraphState(doc_id=doc_id, file_name=pdf.name, file_path=str(pdf))
            final = GraphState.model_validate(graph.invoke(state.model_dump()))
            write_audit(audit_dir, final)
            actual = final.decision
            if actual is None:
                result = "Failed"
            elif actual == expected:
                result = "Correct"
            else:
                result = "Incorrect"
            rows.append(
                {
                    "doc_id": doc_id,
                    "file_name": pdf.name,
                    "expected": expected,
                    "actual": actual,
                    "result": result,
                    "reasons": list(final.reasons or []),
                }
            )
        except Exception as exc:  # noqa: BLE001
            rows.append(
                {
                    "doc_id": doc_id,
                    "file_name": pdf.name,
                    "expected": expected,
                    "actual": None,
                    "result": "Failed",
                    "reasons": [f"Pipeline error: {exc}"],
                }
            )

    payload = {
        "completed_at": datetime.now(UTC).isoformat(),
        "mode": "live_end_to_end",
        "audit_dir": str(audit_dir),
        "rows": rows,
        "notes": {
            "field_level_accuracy": "Not Evaluated",
            "evidence_verification_aggregate": "Not Available",
            "golden_labels_path": str(EXPECTED_PATH),
        },
    }
    save_evaluation_run(payload)
    progress.empty()
    st.success(f"Evaluation complete. Audit: `{audit_dir}`")
    st.rerun()
