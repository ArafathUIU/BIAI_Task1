"""Document list views: All / Approved / Rejected / Needs Human Review."""

from __future__ import annotations

import streamlit as st

from supplier_check.control_center.components import (
    decision_badge,
    empty_state_html,
    esc,
    relative_time,
    status_badge,
)
from supplier_check.control_center.session import open_document, set_page
from supplier_check.control_center.workspace import DocumentMeta, live_documents


def _filter_docs(page: str) -> list[DocumentMeta]:
    docs = live_documents()
    if page == "All Documents":
        return docs
    if page == "Approved":
        return [d for d in docs if d.processing_status == "processed" and d.decision == "Approve"]
    if page == "Rejected":
        return [d for d in docs if d.processing_status == "processed" and d.decision == "Reject"]
    if page == "Needs Human Review":
        return [
            d
            for d in docs
            if (d.processing_status == "processed" and d.decision == "Needs a person to check")
            or (d.processing_status == "failed")
        ]
    return docs


def _page_copy(page: str) -> tuple[str, str, str, str]:
    """title, subtitle, empty title, empty message."""
    if page == "Needs Human Review":
        return (
            "Needs Human Review",
            "Needs Review decisions plus processing failures. Failures are not supplier rejections.",
            "Nothing needs review",
            "When a document needs a person to check, it will appear here.",
        )
    if page == "All Documents":
        return (
            "All Documents",
            "Live workspace documents. Unprocessed files show Not Processed until you run verification.",
            "No documents yet",
            "Upload and process supplier PDFs from New Verification.",
        )
    if page == "Approved":
        return (
            "Approved",
            "Live documents that passed company compliance rules.",
            "No approved documents yet",
            "Approved supplier packs will show up here after processing.",
        )
    if page == "Rejected":
        return (
            "Rejected",
            "Live documents that failed one or more hard rules.",
            "No rejected documents yet",
            "Rejected packs will appear here when hard rules fail.",
        )
    return (page, "Filtered from live processed documents only.", "No documents", "Nothing to show.")


def _render_doc_header() -> None:
    header = st.columns([2.4, 1.2, 1.3, 1.2, 0.8])
    header[0].markdown("**Document**")
    header[1].markdown("**File Status**")
    header[2].markdown("**Decision**")
    header[3].markdown(
        '<div style="text-align:right"><strong>Updated</strong></div>',
        unsafe_allow_html=True,
    )
    header[4].markdown("**Action**")


def _render_doc_row(doc: DocumentMeta, *, key_prefix: str) -> None:
    c1, c2, c3, c4, c5 = st.columns([2.4, 1.2, 1.3, 1.2, 0.8])
    with c1:
        st.markdown(
            f'<div class="sv-doc-name">{esc(doc.file_name)}</div>'
            f'<div class="sv-doc-meta">{esc(doc.supplier_name or "-")}</div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(status_badge(doc.processing_status), unsafe_allow_html=True)
        if doc.processing_status == "failed" and doc.error:
            st.caption(doc.error[:100])
    with c3:
        if doc.processing_status == "failed":
            st.markdown(status_badge("failed"), unsafe_allow_html=True)
        elif doc.processing_status != "processed":
            st.markdown(decision_badge(None), unsafe_allow_html=True)
        else:
            st.markdown(decision_badge(doc.decision), unsafe_allow_html=True)
    with c4:
        rel, exact = relative_time(doc.processed_at or doc.created_at)
        st.markdown(
            f'<div style="text-align:right" class="sv-muted" title="{esc(exact)}">'
            f"{esc(rel)}</div>",
            unsafe_allow_html=True,
        )
    with c5:
        st.markdown('<div class="sv-btn-compact">', unsafe_allow_html=True)
        if st.button("View", key=f"view_{key_prefix}_{doc.doc_uid}", use_container_width=True):
            open_document(doc.doc_uid)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


def render(page: str) -> None:
    title, subtitle, empty_title, empty_msg = _page_copy(page)
    st.markdown(
        f"""
        <div class="sv-page-header">
          <div>
            <h1>{esc(title)}</h1>
            <p>{esc(subtitle)}</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    top_l, top_r = st.columns([2.4, 1.0])
    with top_l:
        query = st.text_input(
            "Search filename",
            value=st.session_state.get("sv_search", ""),
            placeholder="Search by filename…",
            label_visibility="collapsed",
        )
        st.session_state["sv_search"] = query
    with top_r:
        if st.button("New Verification", use_container_width=True, type="primary"):
            set_page("New Verification")
            st.rerun()

    docs = _filter_docs(page)
    if query.strip():
        q = query.strip().lower()
        docs = [d for d in docs if q in d.file_name.lower() or q in d.doc_uid.lower()]

    st.caption(f"{len(docs)} document(s) in this view")

    if not docs:
        icons = {
            "Approved": "✅",
            "Rejected": "⛔",
            "Needs Human Review": "⚠️",
            "All Documents": "📄",
        }
        st.markdown(
            empty_state_html(empty_title, empty_msg, icon=icons.get(page, "📄")),
            unsafe_allow_html=True,
        )
        return

    _render_doc_header()
    for doc in docs:
        _render_doc_row(doc, key_prefix=page)
