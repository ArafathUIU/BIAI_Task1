"""Overview dashboard - live processed documents only."""

from __future__ import annotations

import streamlit as st

from supplier_check.control_center.components import (
    attention_callout_html,
    decision_badge,
    distribution_bar,
    empty_state_html,
    esc,
    kpi_row,
    relative_time,
)
from supplier_check.control_center.session import open_document, set_page
from supplier_check.control_center.workspace import (
    count_decisions,
    live_documents,
    load_evaluation_run,
)


def render() -> None:
    docs = live_documents()
    processed = [d for d in docs if d.processing_status == "processed" and d.decision]
    counts = count_decisions(docs)
    needs_count = counts["Needs a person to check"]
    eval_run = load_evaluation_run()
    last_eval = (
        f"Last evaluation: {str(eval_run['completed_at'])[:19]}"
        if eval_run and eval_run.get("completed_at")
        else "Last evaluation: Not Available"
    )

    st.markdown(
        f"""
        <div class="sv-cta-banner">
          <div>
            <h1>SupplierGuard</h1>
            <p>Supplier quote and contract verification pipeline — upload packs, run compliance checks, and review Approve / Reject / Needs Review.</p>
            <div class="sv-cta-note">Live operational metrics only. Assignment scoring is on Evaluation. {esc(last_eval)}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _cta_l, cta_m, _cta_r = st.columns([1.0, 1.5, 1.0])
    with cta_m:
        st.markdown('<div class="sv-cta-action-wrap">', unsafe_allow_html=True)
        if st.button(
            "Start New Verification",
            type="primary",
            use_container_width=True,
            help="Upload and process one or more supplier PDFs",
        ):
            set_page("New Verification")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        kpi_row(
            counts["total_processed"],
            counts["Approve"],
            counts["Reject"],
            needs_count,
        ),
        unsafe_allow_html=True,
    )

    st.markdown(
        distribution_bar(
            counts["Approve"],
            counts["Reject"],
            needs_count,
        ),
        unsafe_allow_html=True,
    )

    if needs_count:
        st.markdown(attention_callout_html(needs_count), unsafe_allow_html=True)
        if st.button("Open Needs Review", key="ov_needs_link"):
            set_page("Needs Human Review")
            st.rerun()

    st.markdown('<div class="sv-section-title">Recent Documents</div>', unsafe_allow_html=True)
    recent = sorted(
        processed,
        key=lambda d: d.processed_at or d.created_at,
        reverse=True,
    )[:8]
    if not recent:
        st.markdown(
            empty_state_html(
                "No live documents processed yet",
                "Use Start New Verification to upload a supplier PDF and run the pipeline.",
                icon="📋",
            ),
            unsafe_allow_html=True,
        )
        return

    h = st.columns([2.4, 1.6, 1.3, 1.2, 0.8])
    h[0].markdown("**Filename**")
    h[1].markdown("**Supplier**")
    h[2].markdown("**Decision**")
    h[3].markdown("**Processed**")
    h[4].markdown("**Action**")

    for doc in recent:
        c0, c1, c2, c3, c4 = st.columns([2.4, 1.6, 1.3, 1.2, 0.8])
        c0.markdown(f"**{doc.file_name}**")
        c1.caption(doc.supplier_name or "-")
        c2.markdown(decision_badge(doc.decision), unsafe_allow_html=True)
        rel, exact = relative_time(doc.processed_at or doc.created_at)
        c3.markdown(
            f'<span class="sv-muted" title="{esc(exact)}">{esc(rel)}</span>',
            unsafe_allow_html=True,
        )
        with c4:
            st.markdown('<div class="sv-btn-compact">', unsafe_allow_html=True)
            if st.button("View", key=f"recent_open_{doc.doc_uid}", use_container_width=True):
                open_document(doc.doc_uid)
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
