"""New Verification - guided upload, select, process, and next-step review."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from supplier_check.control_center.components import (
    decision_badge,
    empty_state_html,
    esc,
    status_badge,
    workflow_steps_html,
)
from supplier_check.control_center.processing import process_documents
from supplier_check.control_center.session import open_document, set_page
from supplier_check.control_center.workspace import (
    ROOT,
    delete_document,
    get_meta,
    live_documents,
    register_upload,
)


def _fmt_size(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / (1024 * 1024):.1f} MB"


def _short_uid(doc_uid: str) -> str:
    if len(doc_uid) <= 22:
        return doc_uid
    return doc_uid[:18] + "…"


def _current_step(docs: list, has_batch: bool) -> tuple[int, int]:
    """Return (active_step, done_through) for the guided stepper."""
    if has_batch:
        return 3, 3
    if docs:
        return 2, 1
    return 1, 0


def _render_batch_result_banner() -> None:
    """Clear post-process panel: updated statuses + where to go next."""
    batch = st.session_state.get("sv_last_batch")
    if not batch:
        return

    ok = int(batch.get("ok", 0))
    failed = int(batch.get("failed", 0))
    items = batch.get("items") or []

    if failed and not ok:
        panel_cls = "sv-next-panel err"
        title = "Processing finished with failures"
        lead = "Fix the failed files or re-upload, then try again."
    elif failed:
        panel_cls = "sv-next-panel warn"
        title = "Processing finished with mixed results"
        lead = f"Processed: {ok}. Failed: {failed}. Statuses in the table below are updated."
    else:
        panel_cls = "sv-next-panel"
        title = "Verification complete"
        lead = f"Processed: {ok}. File Status and Decision below are updated. Pick a next step."

    rows_html = ""
    for item in items:
        name = esc(item.get("file_name", item.get("doc_uid")))
        if item.get("status") == "failed":
            badge = status_badge("failed")
        else:
            badge = decision_badge(item.get("decision"))
        rows_html += (
            f"<li><span><strong>{name}</strong></span><span>{badge}</span></li>"
        )

    st.markdown(
        f"""
        <div class="{panel_cls}">
          <h3>{esc(title)}</h3>
          <p>{esc(lead)}</p>
          <div class="sv-next-hint">
            <strong>Where to go next:</strong>
            open a document for charts and reasons, check Overview for KPIs,
            or browse All Documents.
          </div>
          <ul class="sv-next-list">{rows_html}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    n1, n2, n3, n4 = st.columns(4)
    first_ok = next((i for i in items if i.get("status") == "processed"), None)
    with n1:
        if first_ok and st.button(
            "Open result details",
            key="batch_open_first",
            use_container_width=True,
            type="primary",
        ):
            open_document(str(first_ok["doc_uid"]))
            st.rerun()
    with n2:
        if st.button("Go to Overview", key="batch_go_overview", use_container_width=True):
            st.session_state.pop("sv_last_batch", None)
            set_page("Overview")
            st.rerun()
    with n3:
        if st.button("All Documents", key="batch_go_all", use_container_width=True):
            st.session_state.pop("sv_last_batch", None)
            set_page("All Documents")
            st.rerun()
    with n4:
        if st.button("Verify more PDFs", key="batch_dismiss", use_container_width=True):
            st.session_state.pop("sv_last_batch", None)
            st.rerun()

    st.divider()


def render() -> None:
    docs = live_documents()
    has_batch = bool(st.session_state.get("sv_last_batch"))
    active, done_through = _current_step(docs, has_batch)

    st.markdown(
        """
        <div class="sv-page-header">
          <div>
            <h1>New Verification</h1>
            <p>Upload supplier PDFs, process them, then follow the next-step panel to review results.</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        workflow_steps_html(active=active, done_through=done_through),
        unsafe_allow_html=True,
    )

    _render_batch_result_banner()

    st.markdown(
        """
        <div class="sv-upload-shell">
          <div class="sv-upload-head">
            <div class="sv-upload-icon">☁</div>
            <div>
              <h3>Upload supplier documents</h3>
              <p>Drag &amp; drop PDFs here, or browse · PDF only · 200MB per file</p>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    uploads = st.file_uploader(
        "PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        help="PDF only · 200MB per file. Select documents below, then Process.",
        label_visibility="collapsed",
    )

    if uploads:
        fingerprint = tuple(sorted((u.name or "", len(u.getvalue())) for u in uploads))
        last_fp = st.session_state.get("sv_upload_fingerprint")
        if fingerprint != last_fp:
            added = 0
            errors: list[str] = []
            new_uids: list[str] = []
            for uploaded in uploads:
                name = uploaded.name or "document.pdf"
                if not name.lower().endswith(".pdf"):
                    errors.append(f"{name}: not a PDF")
                    continue
                try:
                    content = uploaded.getvalue()
                    meta = register_upload(name, content, source="live")
                    new_uids.append(meta.doc_uid)
                    added += 1
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{name}: {exc}")
            st.session_state["sv_upload_fingerprint"] = fingerprint
            if added:
                st.success(f"Added {added} PDF(s). Select them below, then Process.")
                st.session_state["sv_selected_uids"] = list(
                    dict.fromkeys([*new_uids, *st.session_state.get("sv_selected_uids", [])])
                )
            for err in errors:
                st.error(err)

        with st.expander("Selected upload batch", expanded=False):
            for uploaded in uploads:
                name = uploaded.name or "document.pdf"
                size = _fmt_size(len(uploaded.getvalue()))
                st.caption(f"{name} · {size}")

    docs = live_documents()
    if not docs:
        st.markdown(
            empty_state_html(
                "No documents yet",
                "Upload a supplier PDF above to begin verification.",
                icon="☁",
            ),
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        '<div class="sv-section-title">Select documents and process</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "After Process finishes, File Status and Decision update automatically. "
        "Use View on a processed row for charts and reasons."
    )

    selected: list[str] = []
    # Sel | Document | Status | Decision | View | Remove
    header = st.columns([0.4, 2.6, 1.15, 1.15, 0.7, 0.55])
    header[0].markdown("**Sel**")
    header[1].markdown("**Document**")
    header[2].markdown("**File Status**")
    header[3].markdown("**Decision**")
    header[4].markdown("**View**")
    header[5].markdown("** **")

    for doc in docs:
        c0, c1, c2, c3, c4, c5 = st.columns([0.4, 2.6, 1.15, 1.15, 0.7, 0.55])
        default_checked = doc.doc_uid in st.session_state.get("sv_selected_uids", [])
        checked = c0.checkbox(
            "select",
            value=default_checked,
            key=f"sel_{doc.doc_uid}",
            label_visibility="collapsed",
        )
        if checked:
            selected.append(doc.doc_uid)

        supplier = doc.supplier_name or "Supplier pending"
        uid_short = _short_uid(doc.doc_uid)
        c1.markdown(
            f'<div class="sv-doc-name">{esc(doc.file_name)}</div>'
            f'<div class="sv-doc-meta" title="{esc(doc.doc_uid)}">'
            f"{esc(supplier)} · {esc(uid_short)}</div>",
            unsafe_allow_html=True,
        )
        c2.markdown(status_badge(doc.processing_status), unsafe_allow_html=True)
        if doc.processing_status == "failed":
            c3.markdown(status_badge("failed"), unsafe_allow_html=True)
            if doc.error:
                c3.caption(doc.error[:70])
        elif doc.processing_status != "processed":
            c3.markdown(decision_badge(None, empty="Not Processed"), unsafe_allow_html=True)
        else:
            c3.markdown(decision_badge(doc.decision), unsafe_allow_html=True)

        with c4:
            st.markdown('<div class="sv-btn-compact">', unsafe_allow_html=True)
            if doc.processing_status == "processed":
                if st.button(
                    "View",
                    key=f"open_{doc.doc_uid}",
                    use_container_width=True,
                    type="primary",
                ):
                    open_document(doc.doc_uid)
                    st.rerun()
            else:
                st.caption("")
            st.markdown("</div>", unsafe_allow_html=True)
        with c5:
            st.markdown('<div class="sv-btn-ghost sv-btn-compact">', unsafe_allow_html=True)
            if st.button("🗑", key=f"rm_{doc.doc_uid}", use_container_width=True, help="Remove"):
                delete_document(doc.doc_uid)
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    st.session_state["sv_selected_uids"] = selected

    st.markdown('<div class="sv-action-bar">', unsafe_allow_html=True)
    st.caption(f"{len(selected)} selected · PDF only · sequential batch processing")
    a1, a2, a3, a4 = st.columns([1.55, 1.15, 1.0, 1.0])
    process_selected = a1.button(
        "Process Selected Documents",
        type="primary",
        use_container_width=True,
        disabled=not selected,
    )
    process_one = a2.button(
        "Process Single Document",
        use_container_width=True,
        disabled=len(selected) != 1,
        help="Requires exactly one selected document.",
    )
    clear_sel = a3.button("Clear Selection", use_container_width=True)
    reprocess = a4.checkbox("Allow re-process", value=False)
    st.markdown("</div>", unsafe_allow_html=True)

    if clear_sel:
        st.session_state["sv_selected_uids"] = []
        st.rerun()

    targets = selected
    if process_one and len(selected) == 1:
        targets = selected
        process_selected = True

    if process_selected and targets:
        to_run: list[str] = []
        for uid in targets:
            meta = get_meta(uid)
            if meta is None:
                continue
            if meta.processing_status == "processed" and not reprocess:
                continue
            to_run.append(uid)
        skipped = len(targets) - len(to_run)
        if skipped:
            st.info(
                f"Skipped {skipped} already-processed document(s). "
                "Enable Allow re-process to force."
            )
        if not to_run:
            st.warning("Nothing to process.")
            return

        progress = st.progress(0.0, text="Starting sequential processing...")
        status_box = st.empty()
        audit_dir = ROOT / "runs" / f"live-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        audit_dir.mkdir(parents=True, exist_ok=True)

        def _on_progress(index: int, total: int, meta, phase: str) -> None:
            progress.progress(
                index / max(total, 1),
                text=f"{phase}: {meta.file_name} ({index}/{total})",
            )
            status_box.caption(
                f"Sequential processing {index} of {total}: `{meta.file_name}`"
            )

        results = process_documents(to_run, audit_dir=audit_dir, on_progress=_on_progress)
        progress.empty()

        st.session_state["sv_last_batch"] = {
            "ok": sum(1 for r in results if r.processing_status == "processed"),
            "failed": sum(1 for r in results if r.processing_status == "failed"),
            "items": [
                {
                    "doc_uid": r.doc_uid,
                    "file_name": r.file_name,
                    "status": r.processing_status,
                    "decision": r.decision,
                    "error": r.error,
                }
                for r in results
            ],
        }
        st.rerun()
