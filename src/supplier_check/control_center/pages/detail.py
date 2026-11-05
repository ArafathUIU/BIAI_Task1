"""Individual document verification detail."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from supplier_check.control_center.components import (
    conic_pie,
    decision_badge,
    decision_reason_panel,
    esc,
    extraction_field_counts,
    extraction_stat_chips,
    field_rows,
    field_status_counts,
    field_table_html,
    rule_outcome_counts,
    rule_rows,
    status_badge,
    summary_metric_cards,
    supplier_name,
)
from supplier_check.control_center.workspace import get_meta, load_result


def render() -> None:
    doc_uid = st.session_state.get("sv_selected_doc")
    if not doc_uid:
        st.warning("No document selected.")
        if st.button("← Back to All Documents"):
            from supplier_check.control_center.session import set_page

            set_page("All Documents")
            st.rerun()
        return

    meta = get_meta(doc_uid)
    if meta is None:
        st.error("Document not found in workspace.")
        return

    st.markdown('<div class="sv-btn-ghost sv-btn-compact">', unsafe_allow_html=True)
    if st.button("← Back", key="detail_back"):
        from supplier_check.control_center.session import set_page

        set_page("All Documents")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    state = load_result(doc_uid)

    # 1. Header
    supplier = meta.supplier_name or (supplier_name(state) if state else "Not Available")
    processed = (meta.processed_at or "Not Available")[:19].replace("T", " ")
    if meta.processing_status == "failed":
        decision_html = status_badge("failed")
    else:
        decision_html = decision_badge(meta.decision)
    st.markdown(
        f"""
        <div class="sv-page-header">
          <div>
            <h1>{esc(meta.file_name)}</h1>
            <div class="sv-detail-meta">
              {decision_html}
              {status_badge(meta.processing_status)}
              <span class="sv-muted">Processed {esc(processed)}</span>
              <span class="sv-muted">Supplier {esc(supplier)}</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if meta.processing_status == "failed":
        st.error("Processing failed - this is not a supplier rejection.")
        st.code(meta.error or "Unknown error", language=None)
        _pdf_preview(meta.pdf_path)
        return

    if meta.processing_status != "processed" or state is None:
        st.info("This document has not been processed yet. Open New Verification to process it.")
        _pdf_preview(meta.pdf_path)
        return

    # 2. Decision reasons
    st.markdown(decision_reason_panel(state), unsafe_allow_html=True)

    # 3. Charts row
    passed, failed, needs = rule_outcome_counts(state)
    found, not_found, uncertain_fields, unset = field_status_counts(state)
    pie_l, pie_r = st.columns(2)
    with pie_l:
        st.markdown(
            conic_pie(
                [
                    ("Pass", passed, "#1B7F4B"),
                    ("Fail", failed, "#B42318"),
                    ("Needs Review", needs, "#F59E0B"),
                ],
                title="Company Rules Outcome",
                empty_text="No rule hits recorded for this document.",
            ),
            unsafe_allow_html=True,
        )
    with pie_r:
        st.markdown(
            conic_pie(
                [
                    ("Found", found, "#1B7F4B"),
                    ("Not Found", not_found, "#6B7A8C"),
                    ("Uncertain", uncertain_fields, "#F59E0B"),
                    ("Unset", unset, "#CBD5E1"),
                ],
                title="Field Verification Status",
                empty_text="No extraction fields available.",
            ),
            unsafe_allow_html=True,
        )

    # 4. Document summary (custom cards — no st.metric truncation)
    st.markdown('<div class="sv-section-title">Document Summary</div>', unsafe_allow_html=True)
    ext = state.extraction
    st.markdown(
        summary_metric_cards(
            [
                ("Supplier", _display(ext.supplier_name.value if ext else None)),
                ("Quantity", _display(ext.quantity.value if ext else None)),
                ("Unit Price", _display(ext.unit_price.value if ext else None)),
                ("Delivery (days)", _display(ext.delivery_days.value if ext else None)),
                ("Advance %", _display(ext.advance_payment_pct.value if ext else None)),
                ("Extraction", str(state.extraction_status or "—")),
            ]
        ),
        unsafe_allow_html=True,
    )

    # 5. Rules + PR validation (two equal cards)
    left, right = st.columns(2, gap="medium")
    with left:
        st.markdown(
            '<div class="sv-section-title">Company Rules Assessment</div>',
            unsafe_allow_html=True,
        )
        rows = rule_rows(state)
        if not rows:
            st.caption("No rule hits recorded for this document.")
        else:
            cards = []
            for row in rows:
                color = {
                    "PASS": "approve",
                    "FAIL": "reject",
                    "NEEDS REVIEW": "needs",
                }.get(row["Result"], "neutral")
                cards.append(
                    f'<div class="sv-equal-card">'
                    f'<span class="sv-badge {color}">{esc(row["Result"])}</span> '
                    f'<strong>{esc(row["Rule"])}</strong>'
                    f'<div class="sv-muted" style="margin-top:8px">'
                    f'{esc(row["Explanation"] or row["Hit ID"])}</div></div>'
                )
            st.markdown("".join(cards), unsafe_allow_html=True)

    with right:
        st.markdown(
            '<div class="sv-section-title">Purchase Request Validation</div>',
            unsafe_allow_html=True,
        )
        pr = state.pr_row or {}
        quoted_qty = ext.quantity.value if ext else None
        quoted_price = ext.unit_price.value if ext else None
        req_qty = pr.get("quantity_requested")
        max_price = pr.get("max_unit_price")
        match_label = "Match" if state.pr_match_ok else "No match / uncertain"
        match_class = "approve" if state.pr_match_ok else "reject"
        qty_txt = (
            f"{state.qty_diff_pct:+.2f}%"
            if state.qty_diff_pct is not None
            else "Not Available"
        )
        price_txt = (
            f"{state.price_over_max_pct:+.2f}%"
            if state.price_over_max_pct is not None
            else "Not Available"
        )
        price_tone = "warn"
        if state.price_over_max_pct is None:
            price_tone = ""
        elif state.price_over_max_pct <= 0:
            price_tone = "ok"
        elif state.price_over_max_pct <= 3:
            price_tone = "warn"
        else:
            price_tone = "bad"
        qty_icon = "✓" if state.qty_diff_pct == 0 else "!"
        price_icon = "✓" if price_tone == "ok" else "!"
        st.markdown(
            f"""
            <div class="sv-equal-card">
              <span class="sv-badge {match_class}">{esc(match_label)}</span>
              <div class="sv-kv-grid">
                <div><span class="lbl">Requested qty</span><strong>{esc(_display(req_qty))}</strong></div>
                <div><span class="lbl">Quoted qty</span><strong>{esc(_display(quoted_qty))}</strong></div>
                <div><span class="lbl">Qty difference</span>
                  <strong>{qty_icon} {esc(qty_txt)}</strong></div>
                <div><span class="lbl">Max unit price</span><strong>{esc(_display(max_price))}</strong></div>
                <div><span class="lbl">Quoted unit price</span><strong>{esc(_display(quoted_price))}</strong></div>
                <div><span class="lbl">Price vs max</span>
                  <strong class="sv-price-{price_tone}">{price_icon} {esc(price_txt)}</strong></div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 6. Extraction Quality — full width
    st.markdown(
        '<div class="sv-section-title">Extraction Quality and Evidence</div>',
        unsafe_allow_html=True,
    )
    filled, uncertain, total = extraction_field_counts(state)
    st.markdown(
        extraction_stat_chips(
            status=str(state.extraction_status or "—"),
            filled=filled,
            total=total,
            uncertain=uncertain,
        ),
        unsafe_allow_html=True,
    )

    tog_l, tog_r = st.columns([3.2, 1.0])
    with tog_r:
        show_all = st.toggle("Show empty fields", value=False, key=f"fields_all_{doc_uid}")
    with tog_l:
        st.caption("All extraction fields · vertical scroll only")

    st.markdown(
        field_table_html(field_rows(state, filled_only=not show_all)),
        unsafe_allow_html=True,
    )
    if state.extraction_issues:
        with st.expander("Verification notes"):
            for issue in state.extraction_issues:
                st.write(f"- {issue}")

    st.markdown('<div class="sv-section-title">Document Preview</div>', unsafe_allow_html=True)
    _pdf_preview(meta.pdf_path)

    with st.expander("Raw extracted text", expanded=False):
        st.text(state.raw_text or "(empty)")


def _display(value) -> str:
    if value is None:
        return "—"
    return str(value)


def _pdf_preview(pdf_path: str | None) -> None:
    if not pdf_path:
        st.caption("PDF path not available.")
        return
    path = Path(pdf_path)
    if not path.exists():
        st.caption("PDF file missing on disk.")
        return
    try:
        st.pdf(str(path), height=520)
    except Exception:  # noqa: BLE001 - st.pdf may be missing or fail on some builds
        st.caption("Inline PDF preview unavailable in this Streamlit build. File is saved at:")
        st.code(str(path), language=None)
        with path.open("rb") as f:
            st.download_button("Download PDF", f, file_name=path.name, mime="application/pdf")
