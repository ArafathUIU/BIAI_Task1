# Supplier Document Checker (Task 1)

Fixed-step LangGraph pipeline that checks supplier quotations and terms against a
purchase request and company rules. Returns **Approve / Reject / Needs a person to
check** with exact supporting quotes.

## Setup

```bash
cp .env.example .env   # add OPENAI_API_KEY, or set LLM_BASE_URL for Ollama
uv sync
```

## Run tests

```bash
uv run python -m pytest
uv run ruff check .
```

If `uv run pytest` is blocked by OS application control, use `uv run python -m pytest`
(same tests; works around a Windows policy shim issue).

## Run the app (Phase 7)

```bash
uv run streamlit run src/supplier_check/ui.py
```

## Run the pipeline (Phase 6)

```bash
uv run python -m supplier_check.graph --input data/ --out runs/
```

See `PLAN.md`, `Decisions.md`, and `agent.md` for architecture and roadmap.
