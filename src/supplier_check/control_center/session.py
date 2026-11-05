"""Streamlit session-state helpers for navigation and selection."""

from __future__ import annotations

from typing import Any

import streamlit as st

PAGES = [
    "Overview",
    "New Verification",
    "All Documents",
    "Approved",
    "Rejected",
    "Needs Human Review",
    "Evaluation",
]

# Compact labels for sidebar nav (presentation only).
NAV_LABELS = {
    "Overview": "Overview",
    "New Verification": "New Verification",
    "All Documents": "All Documents",
    "Approved": "Approved",
    "Rejected": "Rejected",
    "Needs Human Review": "Needs Review",
    "Evaluation": "Evaluation",
}


def nav_display(page: str) -> str:
    return NAV_LABELS.get(page, page)


def init_session() -> None:
    defaults: dict[str, Any] = {
        "sv_page": "Overview",
        "sv_selected_doc": None,
        "sv_selected_uids": [],
        "sv_upload_batch_ids": [],
        "sv_search": "",
        "sv_nav_radio": "Overview",
        "_sv_prev_nav": "Overview",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def apply_pending_navigation() -> None:
    """Apply queued page changes before sidebar widgets are created.

    Streamlit forbids mutating a widget-bound key after that widget exists, so
    programmatic navigation must stage the target and apply it on the next run
    before ``st.radio(..., key='sv_nav_radio')``.
    """
    pending = st.session_state.pop("sv_pending_page", None)
    if pending is None:
        return
    if pending == "Document Detail":
        st.session_state["sv_page"] = "Document Detail"
        return
    if pending in PAGES:
        st.session_state["sv_nav_radio"] = pending
        st.session_state["sv_page"] = pending
        st.session_state["_sv_prev_nav"] = pending


def set_page(page: str) -> None:
    """Queue a nav change; caller should ``st.rerun()`` afterward."""
    st.session_state["sv_pending_page"] = page


def open_document(doc_uid: str) -> None:
    st.session_state["sv_selected_doc"] = doc_uid
    st.session_state["sv_pending_page"] = "Document Detail"


def resolve_current_page(nav_selection: str) -> str:
    """Resolve page after sidebar radio, preserving Document Detail until nav changes."""
    prev = st.session_state.get("_sv_prev_nav")
    if prev is not None and nav_selection != prev:
        # User clicked a different sidebar item.
        st.session_state["sv_page"] = nav_selection
    st.session_state["_sv_prev_nav"] = nav_selection

    if st.session_state.get("sv_page") == "Document Detail":
        return "Document Detail"

    st.session_state["sv_page"] = nav_selection
    return nav_selection
