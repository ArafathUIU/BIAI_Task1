"""Streamlit entry point - SupplierGuard.

Do not use pandas / ``st.table`` / ``st.dataframe``. On some Windows machines
Application Control blocks pandas native DLLs and those APIs crash the app.

Legacy helper names are re-exported for existing tests.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from supplier_check.control_center.app import main
from supplier_check.control_center.components import (
    decision_badge as decision_badge_html,
)
from supplier_check.control_center.components import (
    field_rows as _field_rows,
)
from supplier_check.control_center.components import (
    render_html_table,
    render_markdown_table,
)
from supplier_check.control_center.workspace import ROOT, count_decisions
from supplier_check.schemas import GraphState


def _resolve_path(path_str: str) -> Path:
    """Resolve relative paths against the project root, not the process cwd."""
    path = Path(path_str).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def _counts(states: list[GraphState]) -> dict[str, int]:
    counts = {"Approve": 0, "Reject": 0, "Needs a person to check": 0}
    for s in states:
        if s.decision in counts:
            counts[s.decision] += 1
    return counts


def _results_rows(states: list[GraphState]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for s in states:
        supplier = ""
        item = ""
        if s.extraction is not None:
            if s.extraction.supplier_name.value is not None:
                supplier = str(s.extraction.supplier_name.value)
            if s.extraction.item_code.value is not None:
                item = str(s.extraction.item_code.value)
        reason = s.reasons[0] if s.reasons else ""
        rows.append(
            {
                "Document": s.doc_id,
                "Supplier": supplier,
                "Item": item,
                "Qty %": "" if s.qty_diff_pct is None else f"{s.qty_diff_pct:+.1f}",
                "Price %": "" if s.price_diff_pct is None else f"{s.price_diff_pct:+.1f}",
                "Decision": s.decision or "",
                "Primary reason": reason,
            }
        )
    return rows


# Keep count_decisions import reachable for future UI tests.
_ = count_decisions

__all__ = [
    "_counts",
    "_field_rows",
    "_resolve_path",
    "_results_rows",
    "decision_badge_html",
    "main",
    "render_html_table",
    "render_markdown_table",
]


if __name__ == "__main__":
    main()
