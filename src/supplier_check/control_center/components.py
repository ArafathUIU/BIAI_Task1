"""Reusable presentation helpers (no business-rule logic)."""

from __future__ import annotations

import html
from typing import Any

from supplier_check.schemas import GraphState

from .workspace import DocumentMeta

DECISION_CLASS = {
    "Approve": "approve",
    "Reject": "reject",
    "Needs a person to check": "needs",
}

STATUS_LABEL = {
    "uploaded": ("Not Processed", "uploaded"),
    "processing": ("Processing", "processing"),
    "processed": ("Processed", "processed"),
    "failed": ("Failed", "failed"),
}

RULE_HIT_LABELS = {
    "reject_price_over_3pct": "Unit price more than 3% above PR maximum",
    "reject_advance_over_20pct": "Advance payment more than 20%",
    "reject_no_late_penalty_clause": "No late-delivery penalty clause",
    "reject_tin_bin_missing": "TIN or BIN missing",
    "reject_delivery_over_45_days": "Delivery later than 45 days",
    "needs_late_penalty_uncertain": "Late-penalty clause uncertain",
    "needs_price_up_to_3pct": "Unit price above max by at most 3%",
    "needs_qty_diff_over_5pct": "Quantity differs by more than 5%",
    "needs_payment_terms": "Payment terms unclear or outside 30-60 days",
    "needs_delivery_unknown": "Delivery days unknown",
    "needs_delivery_31_45_days": "Delivery promised in 31-45 days",
    "needs_vat_not_separate_15": "VAT not shown separately at 15%",
    "needs_numbers_dont_add_up": "Numbers do not add up",
    "needs_validity_under_30_days": "Validity under 30 days",
    "needs_penalty_under_0_5pct": "Late-penalty rate under 0.5%/week",
    "approve_all_rules_pass": "All company rules pass",
}


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def decision_badge(decision: str | None, *, empty: str = "Not Processed") -> str:
    if not decision:
        return f'<span class="sv-badge neutral">○ {esc(empty)}</span>'
    css = DECISION_CLASS.get(decision, "neutral")
    if decision == "Approve":
        label = "✓ Approved"
    elif decision == "Reject":
        label = "✕ Rejected"
    elif decision == "Needs a person to check":
        label = "! Needs Review"
    else:
        label = decision
    return f'<span class="sv-badge {css}">{esc(label)}</span>'


def status_badge(status: str | None) -> str:
    label, css = STATUS_LABEL.get(status or "", (status or "Unknown", "neutral"))
    icons = {
        "uploaded": "○",
        "processing": "…",
        "processed": "●",
        "failed": "✕",
    }
    icon = icons.get(status or "", "○")
    return f'<span class="sv-badge {css}">{esc(icon)} {esc(label)}</span>'

def kpi_card(label: str, value: int | str, *, kind: str = "", hint: str = "") -> str:
    cls = f"sv-kpi {kind}".strip()
    hint_html = f'<div class="hint">{esc(hint)}</div>' if hint else ""
    return (
        f'<div class="{cls}"><div class="label">{esc(label)}</div>'
        f'<div class="value">{esc(value)}</div>{hint_html}</div>'
    )


def kpi_row(total: int, approved: int, rejected: int, needs: int) -> str:
    return (
        '<div class="sv-kpi-grid">'
        f"{kpi_card('Total Processed', total, kind='', hint='Live docs with a decision')}"
        f"{kpi_card('Approved', approved, kind='approve', hint='Ready for procurement')}"
        f"{kpi_card('Rejected', rejected, kind='reject', hint='Failed hard rules')}"
        f"{kpi_card('Needs Review', needs, kind='needs', hint='Human check required')}"
        "</div>"
    )


def distribution_bar(approved: int, rejected: int, needs: int) -> str:
    total = approved + rejected + needs
    if total <= 0:
        return (
            '<div class="sv-card compact"><div class="sv-section-title">Decision Distribution</div>'
            '<p class="sv-muted">No processed documents yet.</p></div>'
        )
    a = 100.0 * approved / total
    r = 100.0 * rejected / total
    n = 100.0 * needs / total
    return f"""
    <div class="sv-card compact">
      <div class="sv-section-title">Decision Distribution</div>
      <div class="sv-bar">
        <span class="a" style="width:{a:.2f}%" title="Approved: {approved} ({a:.0f}%)"></span>
        <span class="r" style="width:{r:.2f}%" title="Rejected: {rejected} ({r:.0f}%)"></span>
        <span class="n" style="width:{n:.2f}%" title="Needs Review: {needs} ({n:.0f}%)"></span>
      </div>
      <div class="sv-legend">
        <span><i style="background:#1B7F4B"></i>Approved {a:.0f}% ({approved})</span>
        <span><i style="background:#B42318"></i>Rejected {r:.0f}% ({rejected})</span>
        <span><i style="background:#F59E0B"></i>Needs Review {n:.0f}% ({needs})</span>
      </div>
    </div>
    """

def workflow_steps_html(*, active: int = 1, done_through: int = 0) -> str:
    """Single compact stepper: upload → extract/verify → review decision."""
    steps = [
        (1, "Upload", "Drop PDF packs"),
        (2, "Extract & verify", "Rules run automatically"),
        (3, "Review decision", "Approve / Reject / Needs Review"),
    ]
    parts: list[str] = ['<div class="sv-steps">']
    for num, title, blurb in steps:
        if num <= done_through:
            state = "done"
        elif num == active:
            state = "active"
        else:
            state = ""
        cls = f"sv-step {state}".strip()
        parts.append(
            f'<div class="{cls}"><strong><span class="n">{num}</span>{esc(title)}</strong>'
            f"{esc(blurb)}</div>"
        )
    parts.append("</div>")
    return "".join(parts)


def relative_time(iso_ts: str | None) -> tuple[str, str]:
    """Return (relative label, exact tooltip). Presentation helper only."""
    from datetime import UTC, datetime

    if not iso_ts:
        return ("-", "")
    raw = str(iso_ts).strip()
    exact = raw[:19].replace("T", " ")
    try:
        # Normalize trailing Z for broader fromisoformat compatibility.
        normalized = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        now = datetime.now(UTC)
        delta = now - parsed.astimezone(UTC)
        seconds = int(delta.total_seconds())
        if seconds < 0:
            return (exact, exact)
        if seconds < 60:
            rel = "just now"
        elif seconds < 3600:
            rel = f"{seconds // 60} min ago"
        elif seconds < 86400:
            rel = f"{seconds // 3600} hr ago"
        elif seconds < 86400 * 7:
            days = seconds // 86400
            rel = "1 day ago" if days == 1 else f"{days} days ago"
        else:
            rel = exact
        return (rel, exact)
    except ValueError:
        return (exact, exact)


def empty_state_html(title: str, message: str, *, icon: str = "📄") -> str:
    return (
        '<div class="sv-empty">'
        f'<div class="sv-empty-icon">{esc(icon)}</div>'
        f"<strong>{esc(title)}</strong>"
        f"<span>{esc(message)}</span></div>"
    )


def attention_callout_html(count: int) -> str:
    if count <= 0:
        return ""
    noun = "document needs" if count == 1 else "documents need"
    return (
        f'<div class="sv-attention"><strong>Needs attention:</strong> '
        f"{count} {noun} human review. Open Needs Review in the sidebar.</div>"
    )


def conic_pie(
    segments: list[tuple[str, int, str]],
    *,
    title: str,
    empty_text: str = "No data available",
) -> str:
    """Render a compact CSS conic-gradient pie from real counts (no chart dependency)."""
    usable = [(label, count, color) for label, count, color in segments if count > 0]
    total = sum(count for _, count, _ in usable)
    if total <= 0:
        return (
            f'<div class="sv-pie-card sv-pie-card-sm"><div class="sv-section-title">{esc(title)}</div>'
            f'<p class="sv-muted">{esc(empty_text)}</p></div>'
        )

    # Single category: big count + pill instead of a full donut.
    if len(usable) == 1:
        label, count, color = usable[0]
        return f"""
        <div class="sv-pie-card sv-pie-card-sm">
          <div class="sv-section-title">{esc(title)}</div>
          <div class="sv-pie-single">
            <div class="sv-pie-single-count" style="color:{color}">{count}</div>
            <span class="sv-badge" style="background:{color}22;color:{color};border-color:{color}55">
              {esc(label)} · 100%
            </span>
          </div>
        </div>
        """

    stops: list[str] = []
    acc = 0.0
    for _label, count, color in usable:
        start = 100.0 * acc / total
        acc += count
        end = 100.0 * acc / total
        stops.append(f"{color} {start:.2f}% {end:.2f}%")
    gradient = ", ".join(stops)

    legend = "".join(
        f'<div class="sv-pie-legend-row">'
        f'<i style="background:{color}"></i>{esc(label)} '
        f"<strong>{count}</strong> ({100.0 * count / total:.0f}%)</div>"
        for label, count, color in usable
    )
    return f"""
    <div class="sv-pie-card sv-pie-card-sm">
      <div class="sv-section-title">{esc(title)}</div>
      <div class="sv-pie-layout">
        <div class="sv-pie sv-pie-sm" style="background: conic-gradient({gradient});"></div>
        <div class="sv-pie-legend">{legend}</div>
      </div>
    </div>
    """


def _compact_cell(text: str, *, limit: int = 72) -> str:
    """Single-line cell: collapse whitespace, ellipsis + tooltip for overflow."""
    flat = " ".join(str(text).split())
    if not flat:
        return '<span class="sv-cell-empty">—</span>'
    shown = flat if len(flat) <= limit else flat[: limit - 1] + "…"
    return f'<span class="sv-cell-clip" title="{esc(flat)}">{esc(shown)}</span>'


def verification_status_pill(status: str | None) -> str:
    raw = (status or "").strip().upper()
    if raw == "FOUND":
        return '<span class="sv-badge approve">FOUND</span>'
    if raw == "NOT_FOUND":
        return '<span class="sv-badge neutral">NOT_FOUND</span>'
    if raw == "UNCERTAIN":
        return '<span class="sv-badge needs">UNCERTAIN</span>'
    if not raw:
        return '<span class="sv-badge neutral">—</span>'
    return f'<span class="sv-badge neutral">{esc(raw)}</span>'


def confidence_cell(conf_text: str) -> str:
    if not conf_text or conf_text == "Not Available":
        return '<span class="sv-muted">—</span>'
    try:
        val = float(conf_text)
        pct = max(0.0, min(100.0, val * 100.0 if val <= 1.0 else val))
        return (
            f'<div class="sv-conf" title="{esc(conf_text)}">'
            f'<div class="sv-conf-bar"><span style="width:{pct:.0f}%"></span></div>'
            f'<span>{pct:.0f}%</span></div>'
        )
    except ValueError:
        return f'<span class="sv-muted">{esc(conf_text)}</span>'


def field_table_html(rows: list[dict[str, str]]) -> str:
    """Full-width fixed-layout extraction table (no horizontal scroll)."""
    if not rows:
        return '<p class="sv-muted">No extraction fields to show.</p>'
    body_parts: list[str] = []
    for row in rows:
        field = esc(row.get("Field", ""))
        value = _compact_cell(row.get("Extracted Value", ""), limit=80)
        status = verification_status_pill(row.get("Verification Status"))
        conf = confidence_cell(row.get("Confidence", ""))
        evidence = _compact_cell(row.get("Evidence", ""), limit=48)
        body_parts.append(
            "<tr>"
            f'<td class="col-field"><code>{field}</code></td>'
            f'<td class="col-value">{value}</td>'
            f'<td class="col-status">{status}</td>'
            f'<td class="col-conf">{conf}</td>'
            f'<td class="col-evidence">{evidence}</td>'
            "</tr>"
        )
    return f"""
    <div class="sv-field-table-wrap">
      <table class="sv-field-table">
        <thead>
          <tr>
            <th class="col-field">Field</th>
            <th class="col-value">Extracted Value</th>
            <th class="col-status">Status</th>
            <th class="col-conf">Confidence</th>
            <th class="col-evidence">Evidence</th>
          </tr>
        </thead>
        <tbody>{"".join(body_parts)}</tbody>
      </table>
    </div>
    """


def summary_metric_cards(items: list[tuple[str, str]]) -> str:
    """Document summary as wrapping custom cards (no st.metric truncation)."""
    cards = "".join(
        f'<div class="sv-sum-card"><div class="label">{esc(label)}</div>'
        f'<div class="value">{esc(value if value not in (None, "") else "—")}</div></div>'
        for label, value in items
    )
    return f'<div class="sv-sum-grid">{cards}</div>'


def extraction_stat_chips(
    *,
    status: str,
    filled: int,
    total: int,
    uncertain: int,
    confidence: str = "Not Available",
) -> str:
    return f"""
    <div class="sv-stat-chips">
      <div class="sv-stat-chip"><span class="lbl">Extraction</span><strong>{esc(status)}</strong></div>
      <div class="sv-stat-chip"><span class="lbl">Fields found</span><strong>{filled}/{total}</strong></div>
      <div class="sv-stat-chip"><span class="lbl">Uncertain</span><strong>{uncertain}</strong></div>
      <div class="sv-stat-chip"><span class="lbl">Confidence</span><strong>{esc(confidence)}</strong></div>
    </div>
    """


def rule_outcome_counts(state: GraphState) -> tuple[int, int, int]:
    """Count PASS / FAIL / NEEDS REVIEW from backend rule hits."""
    rows = rule_rows(state)
    passed = sum(1 for r in rows if r["Result"] == "PASS")
    failed = sum(1 for r in rows if r["Result"] == "FAIL")
    needs = sum(1 for r in rows if r["Result"] == "NEEDS REVIEW")
    return passed, failed, needs


def field_status_counts(state: GraphState) -> tuple[int, int, int, int]:
    """Count FOUND / NOT_FOUND / UNCERTAIN / unset from extraction."""
    if state.extraction is None:
        return 0, 0, 0, 0
    found = not_found = uncertain = unset = 0
    for field in state.extraction.model_dump().values():
        status = field.get("status")
        if status == "FOUND":
            found += 1
        elif status == "NOT_FOUND":
            not_found += 1
        elif status == "UNCERTAIN":
            uncertain += 1
        else:
            unset += 1
    return found, not_found, uncertain, unset


def decision_reason_panel(state: GraphState) -> str:
    """Prominent Why This Decision panel using backend reasons only."""
    decision = state.decision
    badge = decision_badge(decision)
    if decision == "Reject":
        heading = "Why Rejected?"
        lead = "Confirmed rule violations from the decision engine:"
    elif decision == "Needs a person to check":
        heading = "Why Needs Human Review?"
        lead = "Unresolved uncertainty or soft checks from the decision engine:"
    elif decision == "Approve":
        heading = "Why Approved?"
        lead = "Checks that passed according to the decision engine:"
    else:
        heading = "Decision Explanation"
        lead = "Reasons returned by the backend:"

    reasons = state.reasons or ["No reasons returned by backend."]
    reason_html = "".join(f"<li>{esc(reason)}</li>" for reason in reasons)
    evidence_html = ""
    if state.evidence:
        quotes = "".join(f"<li><code>{esc(ev)}</code></li>" for ev in state.evidence)
        evidence_html = (
            "<div class='sv-reason-evidence'><strong>Supporting quotes</strong>"
            f"<ul>{quotes}</ul></div>"
        )
    return f"""
    <div class="sv-reason-panel">
      <div class="sv-reason-head">
        <div>
          <div class="sv-section-title" style="margin:0">{esc(heading)}</div>
          <p class="sv-muted" style="margin:0.2rem 0 0 0">{esc(lead)}</p>
        </div>
        {badge}
      </div>
      <ul class="sv-reason-list">{reason_html}</ul>
      {evidence_html}
    </div>
    """


def render_html_table(rows: list[dict[str, str]], *, decision_col: str | None = None) -> str:
    if not rows:
        return '<p class="sv-muted">No rows.</p>'
    cols = list(rows[0].keys())
    head = "".join(f"<th>{esc(c)}</th>" for c in cols)
    body_parts: list[str] = []
    for row in rows:
        cells: list[str] = []
        for c in cols:
            raw = str(row.get(c, ""))
            if decision_col and c == decision_col:
                cells.append(f"<td>{decision_badge(raw or None)}</td>")
            elif c in {"Decision", "Status", "File Status", "Result"}:
                if c == "File Status" or c == "Status":
                    # Already may contain HTML badge from caller
                    cells.append(f"<td>{raw}</td>")
                elif c == "Result":
                    cells.append(f"<td>{raw}</td>")
                else:
                    cells.append(f"<td>{decision_badge(raw or None)}</td>")
            else:
                cells.append(f"<td>{esc(raw)}</td>")
        body_parts.append(f"<tr>{''.join(cells)}</tr>")
    return (
        '<div class="sv-table-wrap"><table class="sv-table">'
        f"<thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(body_parts)}</tbody></table></div>"
    )


def render_markdown_table(rows: list[dict[str, str]]) -> str:
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


def field_rows(state: GraphState, *, filled_only: bool = True) -> list[dict[str, str]]:
    if state.extraction is None:
        return []
    rows: list[dict[str, str]] = []
    for name, field in state.extraction.model_dump().items():
        value = field.get("value")
        status = field.get("status")
        if filled_only and value is None and status not in {"NOT_FOUND", "UNCERTAIN"}:
            continue
        conf = field.get("confidence")
        evidence = field.get("evidence")
        rows.append(
            {
                "Field": name,
                "Extracted Value": "" if value is None else str(value),
                "Verification Status": "" if status is None else str(status),
                "Confidence": "Not Available" if conf is None else f"{float(conf):.2f}",
                "Evidence": "" if evidence is None else str(evidence),
            }
        )
    return rows


def supplier_name(state: GraphState | None) -> str:
    if state is None or state.extraction is None:
        return ""
    value = state.extraction.supplier_name.value
    return "" if value is None else str(value)


def extraction_field_counts(state: GraphState) -> tuple[int, int, int]:
    """Return (filled, uncertain, total)."""
    if state.extraction is None:
        return 0, 0, 0
    filled = 0
    uncertain = 0
    total = 0
    for field in state.extraction.model_dump().values():
        total += 1
        if field.get("status") == "UNCERTAIN":
            uncertain += 1
        if field.get("value") is not None or field.get("status") == "NOT_FOUND":
            filled += 1
    return filled, uncertain, total


def rule_rows(state: GraphState) -> list[dict[str, str]]:
    """Present backend rule hits with actual reasons - no invented thresholds."""
    if state.rule_result is None:
        return []
    hits = state.rule_result.rule_hits or []
    reasons = state.reasons or state.rule_result.reasons or []
    rows: list[dict[str, str]] = []
    for i, hit in enumerate(hits):
        label = RULE_HIT_LABELS.get(hit, hit)
        if hit.startswith("reject_"):
            result = "FAIL"
        elif hit.startswith("needs_"):
            result = "NEEDS REVIEW"
        elif hit.startswith("approve_"):
            result = "PASS"
        else:
            result = "NEEDS REVIEW"
        reason = reasons[i] if i < len(reasons) else (reasons[0] if reasons else "")
        rows.append(
            {
                "Rule": label,
                "Hit ID": hit,
                "Result": result,
                "Explanation": reason,
            }
        )
    return rows


def recent_rows(docs: list[DocumentMeta], limit: int = 8) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for doc in docs[:limit]:
        rows.append(
            {
                "Filename": doc.file_name,
                "Decision": doc.decision or "",
                "Status": status_badge(doc.processing_status),
                "Processed": (doc.processed_at or doc.created_at or "")[:19].replace("T", " "),
            }
        )
    return rows


def display_decision_label(decision: str | None) -> str:
    if decision == "Approve":
        return "Approved"
    if decision == "Reject":
        return "Rejected"
    if decision == "Needs a person to check":
        return "Needs Human Review"
    return "Not Available"
