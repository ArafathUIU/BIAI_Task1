import json
from pathlib import Path

import pytest

from supplier_check.graph import build_graph, run_batch

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _pack01_payload() -> dict:
    from tests.test_verify import PACK01_FIELDS, _payload

    return _payload(PACK01_FIELDS)


@pytest.fixture
def mock_llm(monkeypatch):
    def _set(payload):
        monkeypatch.setattr(
            "supplier_check.extract.call_llm",
            lambda messages, client=None, model=None: json.dumps(payload),
        )

    return _set


def test_graph_runs_pack_01_end_to_end(mock_llm, tmp_path) -> None:
    mock_llm(_pack01_payload())
    graph = build_graph(DATA_DIR / "purchase-request.csv")
    state = {"doc_id": "supplier-pack-01", "file_path": str(DATA_DIR / "supplier-pack-01.pdf")}
    final = graph.invoke(state)
    assert final["decision"] == "Approve"
    assert final["pr_match_ok"] is True
    assert final["extraction_status"] == "ok"


def test_run_batch_writes_audit_jsonl(mock_llm, tmp_path, monkeypatch) -> None:
    mock_llm(_pack01_payload())
    monkeypatch.setattr(
        "supplier_check.extract.get_client_and_model",
        lambda: (object(), "llama-3.3-70b-versatile"),
    )
    # Only one pack present in a temp folder to keep it fast.
    import shutil

    work = tmp_path / "data"
    work.mkdir()
    shutil.copy(DATA_DIR / "supplier-pack-01.pdf", work / "supplier-pack-01.pdf")
    shutil.copy(DATA_DIR / "purchase-request.csv", work / "purchase-request.csv")
    run_dir = run_batch(work, tmp_path / "runs")
    audit = run_dir / "results.jsonl"
    assert audit.exists()
    lines = audit.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["doc_id"] == "supplier-pack-01"
    assert record["decision"] == "Approve"
    assert record["model"] == "llama-3.3-70b-versatile"


def test_run_batch_continues_after_pipeline_error(mock_llm, tmp_path, monkeypatch) -> None:
    mock_llm(_pack01_payload())
    import shutil

    from supplier_check import graph as graph_mod

    work = tmp_path / "data"
    work.mkdir()
    shutil.copy(DATA_DIR / "supplier-pack-01.pdf", work / "supplier-pack-01.pdf")
    shutil.copy(DATA_DIR / "supplier-pack-02.pdf", work / "supplier-pack-02.pdf")
    shutil.copy(DATA_DIR / "purchase-request.csv", work / "purchase-request.csv")

    real_build = graph_mod.build_graph

    class BoomGraph:
        def invoke(self, state):
            if state.get("doc_id") == "supplier-pack-01":
                raise RuntimeError("boom")
            return real_build(work / "purchase-request.csv").invoke(state)

    monkeypatch.setattr(graph_mod, "build_graph", lambda pr_path: BoomGraph())
    run_dir = run_batch(work, tmp_path / "runs")
    lines = [
        json.loads(line)
        for line in (run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(lines) == 2
    by_id = {row["doc_id"]: row for row in lines}
    assert by_id["supplier-pack-01"]["decision"] == "Needs a person to check"
    assert "Pipeline error" in by_id["supplier-pack-01"]["reasons"][0]
    assert by_id["supplier-pack-02"]["decision"] in {
        "Approve",
        "Reject",
        "Needs a person to check",
    }
