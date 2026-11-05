"""Streamlit entry for SupplierGuard."""

from __future__ import annotations

import streamlit as st

from supplier_check.control_center.pages import (
    detail,
    documents,
    evaluation,
    new_verification,
    overview,
)
from supplier_check.control_center.session import (
    PAGES,
    apply_pending_navigation,
    init_session,
    nav_display,
    resolve_current_page,
)
from supplier_check.control_center.styles import inject_styles
from supplier_check.control_center.workspace import ensure_workspace, live_documents


def main() -> None:
    st.set_page_config(
        page_title="SupplierGuard",
        page_icon="SG",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_styles()
    ensure_workspace()
    init_session()
    apply_pending_navigation()

    docs = live_documents()
    processed = [d for d in docs if d.processing_status == "processed" and d.decision]
    needs = sum(
        1
        for d in processed
        if d.decision == "Needs a person to check" or d.human_review_required
    )
    failed = sum(1 for d in docs if d.processing_status == "failed")

    with st.sidebar:
        st.markdown(
            """
            <div class="sv-brand">
              <div class="sv-brand-mark">SG</div>
              <div class="sv-brand-copy">
                <strong>SupplierGuard</strong>
                <span>Supplier quote and contract verification pipeline</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        nav = st.radio(
            "Navigation",
            PAGES,
            key="sv_nav_radio",
            format_func=nav_display,
            label_visibility="collapsed",
        )

        st.markdown(
            f"""
            <div class="sv-side-stats">
              <div>Pipeline ready</div>
              <div class="sv-side-badges">
                <span class="sv-side-badge ok">{len(processed)} processed</span>
                <span class="sv-side-badge warn">{needs} review</span>
                <span class="sv-side-badge err">{failed} failed</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    current = resolve_current_page(nav)
    if current == "Document Detail":
        detail.render()
    elif current == "Overview":
        overview.render()
    elif current == "New Verification":
        new_verification.render()
    elif current in {"All Documents", "Approved", "Rejected", "Needs Human Review"}:
        documents.render(current)
    elif current == "Evaluation":
        evaluation.render()
    else:
        overview.render()


if __name__ == "__main__":
    main()
