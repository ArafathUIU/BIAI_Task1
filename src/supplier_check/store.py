"""Audit storage: append one JSON line per document run."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from .config import LLM_MODEL
from .schemas import GraphState

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "extract_quotation.md"


def _prompt_version() -> str:
    try:
        return hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest()[:12]
    except OSError:
        return "unknown"


def _record(state: GraphState) -> dict:
    rule_hits = state.rule_result.rule_hits if state.rule_result else []
    return {
        "doc_id": state.doc_id,
        "file_name": state.file_name,
        "text_hash": state.text_hash,
        "decision": state.decision,
        "reasons": state.reasons,
        "evidence": state.evidence,
        "extraction_status": state.extraction_status,
        "extraction_issues": state.extraction_issues,
        "pr_match_ok": state.pr_match_ok,
        "qty_diff_pct": state.qty_diff_pct,
        "price_diff_pct": state.price_diff_pct,
        "price_over_max_pct": state.price_over_max_pct,
        "rule_hits": rule_hits,
        "human_review_required": state.human_review_required,
        "model": LLM_MODEL,
        "prompt_version": _prompt_version(),
        "timestamp": datetime.now(UTC).isoformat(),
    }


def write_audit(run_dir: Path, state: GraphState) -> Path:
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "results.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(_record(state), ensure_ascii=False) + "\n")
    return path
