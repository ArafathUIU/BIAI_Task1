"""Purchase-request loading and quote comparison."""

from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path
from typing import Any

from .schemas import GraphState


def load_purchase_request(path: Path) -> dict[str, dict[str, Any]]:
    """Load purchase-request.csv keyed by item code (A-E)."""
    result: dict[str, dict[str, Any]] = {}
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            item = (row.get("Item") or "").strip()
            if not item:
                continue
            result[item] = {
                "pr_number": (row.get("PR number") or "").strip(),
                "item": item,
                "description": (row.get("Description") or "").strip(),
                "unit": (row.get("Unit") or "").strip(),
                "quantity_requested": int(row["Quantity requested"]),
                "max_unit_price": Decimal(row["Maximum unit price (BDT)"]),
            }
    return result


def get_pr_row(item_code: Any, pr: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    if not isinstance(item_code, str):
        return None
    return pr.get(item_code.strip().upper())


def compare_to_pr(extraction: Any, pr_row: dict[str, Any]) -> dict[str, float | None]:
    """Return qty/price comparison percentages (signed)."""
    qty = extraction.quantity.value
    unit_price = extraction.unit_price.value
    requested_qty = pr_row["quantity_requested"]
    max_price = pr_row["max_unit_price"]

    qty_diff_pct: float | None = None
    price_diff_pct: float | None = None
    price_over_max_pct: float | None = None

    if isinstance(qty, (int, float)) and not isinstance(qty, bool) and requested_qty:
        qty_diff_pct = (qty - requested_qty) / requested_qty * 100
    if isinstance(unit_price, (int, float)) and not isinstance(unit_price, bool) and max_price:
        price_diff_pct = (unit_price - float(max_price)) / float(max_price) * 100
        price_over_max_pct = price_diff_pct

    return {
        "qty_diff_pct": qty_diff_pct,
        "price_diff_pct": price_diff_pct,
        "price_over_max_pct": price_over_max_pct,
    }


def apply_pr_comparison(state: GraphState, pr: dict[str, dict[str, Any]]) -> GraphState:
    """LangGraph-friendly helper: attach PR row and comparison to state."""
    if state.extraction is None:
        state.pr_match_ok = False
        return state
    item_code = state.extraction.item_code.value
    row = get_pr_row(item_code, pr)
    if row is None:
        state.pr_row = None
        state.pr_match_ok = False
        return state
    state.pr_row = row
    state.pr_match_ok = True
    cmp_ = compare_to_pr(state.extraction, row)
    state.qty_diff_pct = cmp_["qty_diff_pct"]
    state.price_diff_pct = cmp_["price_diff_pct"]
    state.price_over_max_pct = cmp_["price_over_max_pct"]
    return state
