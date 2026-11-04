# Supplier Document Checker (Task 1)

Fixed-step LangGraph pipeline that checks supplier quotations and terms against a
purchase request and company rules. Returns **Approve / Reject / Needs a person to
check** with exact supporting quotes.

## Setup

```bash
cp .env.example .env
uv sync
```

Fill **one** provider in `.env` (never commit `.env`; it is gitignored):

| Provider | Set these |
|---|---|
| OpenAI | `OPENAI_API_KEY` (+ optional `LLM_MODEL`, default `gpt-4o-mini`) |
| Groq | `GROQ_API_KEY` (+ optional `GROQ_MODEL`, default `llama-3.3-70b-versatile`) |
| Ollama / custom | `LLM_BASE_URL` (e.g. `http://localhost:11434/v1`) + `LLM_MODEL` |

Precedence if more than one is set: `LLM_BASE_URL` → `GROQ_API_KEY` → `OPENAI_API_KEY`.

## Run tests

```bash
uv run python -m pytest
uv run ruff check .
```

If `uv run pytest` is blocked by OS application control, use `uv run python -m pytest`
(same tests; works around a Windows policy shim issue).

## Run the app (Phase 7)

From the project root:

```bash
uv run streamlit run src/supplier_check/ui.py
```

The UI is **pandas-free** (`st.table` / `st.dataframe` are not used). On some
Windows machines Application Control blocks pandas DLLs; this app stays runnable
without pandas. Relative paths like `data` resolve from the project root.

## Run the pipeline (Phase 6)

```bash
uv run python -m supplier_check.graph --input data/ --out runs/
```

See `PLAN.md`, `Decisions.md`, and `agent.md` for architecture and roadmap.
