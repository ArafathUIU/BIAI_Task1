"""LangGraph wiring for the supplier document checker."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from .decide import decide
from .extract import extract_quotation
from .ingest import ingest_pdf
from .pr import apply_pr_comparison, load_purchase_request
from .schemas import GraphState
from .store import write_audit
from .verify import verify_extraction


def _to_state(state) -> GraphState:
    if isinstance(state, GraphState):
        return state
    return GraphState.model_validate(state)


def _dump(state: GraphState) -> dict:
    return state.model_dump()


def build_graph(pr_path: Path):
    pr = load_purchase_request(pr_path)

    def ingest_node(state):
        s = _to_state(state)
        if s.file_path:
            new = ingest_pdf(Path(s.file_path))
            new.file_path = s.file_path
            return _dump(new)
        return _dump(s)

    def extract_node(state):
        s = _to_state(state)
        return _dump(extract_quotation(s))

    def verify_node(state):
        s = _to_state(state)
        return _dump(verify_extraction(s))

    def pr_node(state):
        s = _to_state(state)
        return _dump(apply_pr_comparison(s, pr))

    def decide_node(state):
        s = _to_state(state)
        return _dump(decide(s))

    graph = StateGraph(GraphState)
    graph.add_node("ingest", ingest_node)
    graph.add_node("extract", extract_node)
    graph.add_node("verify", verify_node)
    graph.add_node("pr_compare", pr_node)
    graph.add_node("decide", decide_node)

    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "extract")
    graph.add_edge("extract", "verify")
    graph.add_edge("verify", "pr_compare")
    graph.add_edge("pr_compare", "decide")
    graph.add_edge("decide", END)
    return graph.compile()


def run_batch(input_dir: Path, out_dir: Path) -> Path:
    input_dir = Path(input_dir)
    pr_path = input_dir / "purchase-request.csv"
    graph = build_graph(pr_path)
    run_dir = out_dir / datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    for pdf in sorted(input_dir.glob("supplier-pack-*.pdf")):
        try:
            state = GraphState(doc_id=pdf.stem, file_path=str(pdf))
            final = graph.invoke(state.model_dump())
            final_state = GraphState.model_validate(final)
        except Exception as exc:  # noqa: BLE001 - one bad doc must not abort the batch
            final_state = GraphState(
                doc_id=pdf.stem,
                file_name=pdf.name,
                file_path=str(pdf),
                decision="Needs a person to check",
                reasons=[f"Pipeline error while processing document: {exc}"],
                human_review_required=True,
                extraction_status="needs_human",
                extraction_issues=[str(exc)],
            )
        write_audit(run_dir, final_state)
        print(f"{final_state.doc_id}: {final_state.decision}")

    return run_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the supplier document checker.")
    parser.add_argument("--input", required=True, help="Folder containing the sample files.")
    parser.add_argument("--out", default="runs", help="Output folder for audit JSONL.")
    args = parser.parse_args()
    run_batch(Path(args.input), Path(args.out))


if __name__ == "__main__":
    main()
